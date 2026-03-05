import pandas as pd
import numpy as np
import math
import re
from pathlib import Path

# ========= Paths =========
TRAINING_PATH = Path("amanita_microscopy.xlsx")
MASTER_PATH   = Path("basidiospore.xlsx")
OUTPUT_PATH   = Path("basidiospore_filled.xlsx")

# ========= Custom rounding (.0 / .5 / next integer) =========
# Rule:
#   decimal ≤ .249  -> round down to .0
#   decimal ≤ .749  -> round down to .5
#   otherwise       -> round up to next integer (.0)
def custom_round(x):
    if pd.isna(x):
        return np.nan
    x = float(x)
    base = math.floor(x)
    dec  = x - base
    if dec <= 0.249:
        return float(base)
    elif dec <= 0.749:
        return float(base) + 0.5
    else:
        return float(base) + 1.0

# ========= Stats helper (UNROUNDED mean so we can keep avg_q raw) =========
def pct_stats_custom(series):
    x = pd.to_numeric(pd.Series(series), errors="coerce").dropna().to_numpy()
    if x.size == 0:
        return dict(min=np.nan, p10=np.nan, p90=np.nan, max=np.nan, mean=np.nan, count=0)
    return dict(
        min  = custom_round(np.min(x)),
        p10  = custom_round(np.quantile(x, 0.10, method="linear")),
        p90  = custom_round(np.quantile(x, 0.90, method="linear")),
        max  = custom_round(np.max(x)),
        mean = float(np.mean(x)),  # IMPORTANT: leave unrounded for avg_q
        count= int(x.size),
    )

# ========= Locate the Basidiospore header row =========
def find_basidiospore_anchor(df):
    """Find the row index of the 'Basidiospore' label in column A."""
    for r in range(len(df)):
        v = df.iloc[r, 0]
        if isinstance(v, str) and v.strip().lower().startswith("basidiospore"):
            return r
    return None

def get_specimen_id(df, sheet_name):
    """Extract '## 30184' style id; fallback to first cell digits or sheet name."""
    for r in range(0, min(15, len(df))):
        for val in df.iloc[r].tolist():
            if isinstance(val, str) and "##" in val:
                m = re.search(r"##\s*(\S+)", val)
                if m:
                    return m.group(1)
    v = df.iloc[0, 0]
    if isinstance(v, (int, float)) and not pd.isna(v):
        return str(int(v))
    m = re.search(r"(\d+[\w_]*)", str(v))
    return m.group(1) if m else sheet_name

# ========= Row scanning: robust data detection =========
def scan_spore_rows(df, anchor_row, max_rows=25, max_scan=60, stop_after_blanks=3):
    """
    Starting from the row after 'Basidiospore', scan downward and collect rows
    where B or C (Length/Width) looks numeric. Stop when:
      - we have collected up to max_rows rows, OR
      - we encounter `stop_after_blanks` consecutive rows where both B and C are empty,
        OR
      - we scanned `max_scan` rows (safety).
    Returns a DataFrame with exactly the detected spore rows (A:D).
    """
    rows = []
    blanks = 0
    start_r = anchor_row + 1
    end_r = min(start_r + max_scan, len(df))

    for r in range(start_r, end_r):
        # columns: A(index), B(Length), C(Width), D(Q)
        row = df.iloc[r, 0:4]
        # numeric test on B/C
        b = pd.to_numeric(row.iloc[1], errors="coerce")
        c = pd.to_numeric(row.iloc[2], errors="coerce")

        if pd.isna(b) and pd.isna(c):
            blanks += 1
            if blanks >= stop_after_blanks:
                break
            # don't append this row
        else:
            blanks = 0
            rows.append(row.tolist())
            if len(rows) >= max_rows:
                break

    if not rows:
        return pd.DataFrame(columns=[0,1,2,3])
    return pd.DataFrame(rows, columns=[0,1,2,3])

# ========= Summarize training workbook =========
def summarize_training_book(training_path: Path):
    """
    For each worksheet:
      - Find 'Basidiospore' anchor.
      - Scan down for rows where B/C are numeric (up to 25 spores).
      - Treat blanks/non-numeric/<=0 as missing (NaN).
      - Q = sheet Q if valid (>0), else L/W if both valid (>0).
      - Keep only rows with at least L or W present.
      - Compute:
         * Length/Width: min, 10th, 90th, max (custom-rounded)
         * Q: min/max (custom-rounded) and avg_q (UNROUNDED mean over valid Q)
      - spore_count = number of rows retained.
    """
    xls = pd.ExcelFile(training_path, engine="openpyxl")
    recs = []
    logs = []

    for sheet in xls.sheet_names:
        df = xls.parse(sheet, header=None, dtype=object)
        sid = get_specimen_id(df, sheet)
        anchor = find_basidiospore_anchor(df)

        if anchor is None:
            logs.append((sid, sheet, "no_basidiospore_anchor", 0, 0, 0))
            continue

        block = scan_spore_rows(df, anchor_row=anchor, max_rows=25, max_scan=60, stop_after_blanks=3)

        if block.empty:
            logs.append((sid, sheet, "no_spore_rows_found", 0, 0, 0))
            continue

        # Columns: [A=index, B=L, C=W, D=Q]
        L = pd.to_numeric(block.iloc[:, 1], errors="coerce")
        W = pd.to_numeric(block.iloc[:, 2], errors="coerce")
        Q = pd.to_numeric(block.iloc[:, 3], errors="coerce")

        # Treat impossible values as missing
        L = L.mask(L <= 0)
        W = W.mask(W <= 0)
        Q = Q.mask(Q <= 0)

        # Build Q candidate: prefer sheet Q, else L/W where both valid
        Qc = Q.copy()
        can_compute = (~L.isna()) & (~W.isna()) & (W != 0)
        Qc = Qc.where(~Qc.isna(), (L / W).where(can_compute))

        # Retain rows where at least L or W exists
        keep = (~L.isna()) | (~W.isna())
        L2 = L[keep]
        W2 = W[keep]
        Q2 = Qc[keep]

        # Final valid Q set for averaging: numeric and > 0 only
        Q_valid = pd.to_numeric(Q2, errors="coerce").dropna()
        Q_valid = Q_valid[Q_valid > 0]

        spore_count = int(keep.sum())
        q_count     = int(Q_valid.shape[0])

        if spore_count == 0:
            logs.append((sid, sheet, "no_numeric_spores", 0, 0, 0))
            continue

        # Stats
        Ls = pct_stats_custom(L2)
        Ws = pct_stats_custom(W2)

        # min/max with custom rounding; avg_q UNROUNDED mean over valid Q only
        if q_count > 0:
            min_q_val = custom_round(float(Q_valid.min()))
            max_q_val = custom_round(float(Q_valid.max()))
            avg_q_val = float(Q_valid.mean())  # UNROUNDED
        else:
            min_q_val = np.nan
            max_q_val = np.nan
            avg_q_val = np.nan

        recs.append({
            "specimen_id": str(sid),
            "spore_count": spore_count,

            "min_length": Ls["min"], "10_length": Ls["p10"], "90_length": Ls["p90"], "max_length": Ls["max"],
            "min_width":  Ws["min"], "10_width": Ws["p10"], "90_width": Ws["p90"], "max_width": Ws["max"],

            "min_q": min_q_val,
            "avg_q": avg_q_val,  # <- UNROUNDED MEAN of valid Q only
            "max_q": max_q_val,
        })

        logs.append((sid, sheet, "ok", spore_count, q_count, int(L2.notna().sum())))

    summary_df = pd.DataFrame.from_records(recs)
    log_df = pd.DataFrame(logs, columns=["specimen_id", "sheet", "status", "spore_count", "q_count", "lw_rows"])
    return summary_df, log_df

# ========= Merge into master =========
def main():
    summary, logdf = summarize_training_book(TRAINING_PATH)

    master = pd.read_excel(MASTER_PATH, sheet_name=0, engine="openpyxl")
    master["specimen_id"] = master["specimen_id"].astype(str)

    updated = master.copy()
    if not summary.empty:
        summary["specimen_id"] = summary["specimen_id"].astype(str)

        update_cols = [
            "spore_count",
            "min_length","10_length","90_length","max_length",
            "min_width","10_width","90_width","max_width",
            "min_q","avg_q","max_q",
        ]

        # Update existing rows
        s_map = summary.set_index("specimen_id").to_dict(orient="index")
        for idx, row in updated.iterrows():
            sid = row["specimen_id"]
            if sid in s_map:
                for col in update_cols:
                    if col in updated.columns:
                        updated.at[idx, col] = s_map[sid].get(col, np.nan)

        # Append any parsed specimens not already present
        missing = summary[~summary["specimen_id"].isin(updated["specimen_id"])]
        if not missing.empty:
            for col in update_cols:
                if col not in updated.columns:
                    updated[col] = np.nan
            to_append = missing.reindex(columns=updated.columns, fill_value=np.nan)
            updated = pd.concat([updated, to_append], ignore_index=True)

    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as w:
        updated.to_excel(w, index=False, sheet_name="Sheet1")
        logdf.to_excel(w, index=False, sheet_name="parse_log")

    print("Done ->", OUTPUT_PATH)

if __name__ == "__main__":
    main()