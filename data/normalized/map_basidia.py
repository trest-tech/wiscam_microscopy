"""
fill_basidia_fixed_range.py

Reads basidia data strictly from A:E and rows 32..57 (inclusive) for every sheet.
Merges summaries into basidia.xlsx and writes basidia_filled.xlsx.

Assumed layout under A:E, rows 32..57 (per sheet):
  A = index/row label (ignored)
  B = Length
  C = Width
  D = Sterigma count
  E = Sterigma Length
"""

import pandas as pd
import numpy as np
import math
import re
from pathlib import Path

# ========= Paths =========
TRAINING_PATH = Path("amanita_microscopy.xlsx")  # input workbook with raw sheets
MASTER_PATH   = Path("basidia.xlsx")        # master table to update
OUTPUT_PATH   = Path("basidia_filled.xlsx") # output file

# ========= Fixed range (Excel rows 32..57 inclusive; columns A..E) =========
ROW_START = 32   # 1-based Excel row number
ROW_END   = 57   # inclusive
COL_SLICE = slice(0, 5)   # A..E -> iloc[:, 0:5)

# Convert to pandas iloc indices
ILOC_ROW_START = ROW_START - 1           # 31
ILOC_ROW_STOP  = ROW_END                 # iloc stop is exclusive; 57 -> includes index 56
ILOC_COL_SLICE = slice(0, 5)             # A..E

# ========= Rounding rule (.0 / .5 / next integer) =========
def custom_round(x: float):
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

# ========= Specimen ID helper =========
def get_specimen_id(df: pd.DataFrame, sheet_name: str) -> str:
    """
    Try to find an id like '## 30184' anywhere in the top 15 rows,
    else fallback to digits in A1, else the sheet name.
    """
    for r in range(0, min(15, len(df))):
        for val in df.iloc[r].tolist():
            if isinstance(val, str) and "##" in val:
                m = re.search(r"##\\s*(\\S+)", val)
                if m:
                    return m.group(1)
    v = df.iloc[0, 0] if df.shape[0] > 0 and df.shape[1] > 0 else None
    if isinstance(v, (int, float)) and not pd.isna(v):
        return str(int(v))
    m = re.search(r"(\\d+[\\w_]*)", str(v)) if v is not None else None
    return m.group(1) if m else sheet_name

# ========= Safe parsers =========
_num_rx = re.compile(r"(\\d+)")

def parse_int_or_nan(x) -> float:
    """Extract integer from '4', '4?', '2(?)', return NaN if not found."""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float)) and not pd.isna(x):
        return int(x)
    s = str(x)
    m = _num_rx.search(s)
    return int(m.group(1)) if m else np.nan

def parse_float_or_nan(x) -> float:
    """Parse floats robustly; 'NA', '', '?' -> NaN."""
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).strip())
        except Exception:
            return np.nan

def pct_stats_min_avg_max(series: pd.Series) -> dict:
    """
    Return min/avg/max with custom rounding on min/max; avg unrounded.
    """
    x = pd.to_numeric(pd.Series(series), errors="coerce").dropna().to_numpy()
    if x.size == 0:
        return dict(min=np.nan, mean=np.nan, max=np.nan, count=0)
    return dict(
        min  = custom_round(np.min(x)),
        mean = float(np.mean(x)),     # keep unrounded for avg
        max  = custom_round(np.max(x)),
        count= int(x.size),
    )

# ========= Core summarizer using fixed A:E, 32..57 =========
def summarize_training_book_basidia_fixed(training_path: Path):
    xls = pd.ExcelFile(training_path, engine="openpyxl")
    recs = []
    logs = []

    for sheet in xls.sheet_names:
        # Load with no headers to preserve raw grid coordinates
        df = xls.parse(sheet, header=None, dtype=object)

        # Slice A:E, rows 32..57
        # If a sheet is shorter/narrower, pandas will handle it with NaNs—so no traceback.
        block = df.iloc[ILOC_ROW_START:ILOC_ROW_STOP, ILOC_COL_SLICE].copy()

        # Identify specimen
        sid = get_specimen_id(df, sheet)

        if block.empty:
            logs.append((sid, sheet, "fixed_range_empty", 0, 0, 0))
            continue

        # Columns: [A=index/label, B=L, C=W, D=sterigma count, E=sterigma length]
        L = pd.to_numeric(block.iloc[:, 1], errors="coerce").mask(lambda s: s <= 0)
        W = pd.to_numeric(block.iloc[:, 2], errors="coerce").mask(lambda s: s <= 0)
        S_count_raw = block.iloc[:, 3]
        S_len_raw   = block.iloc[:, 4]

        # Keep rows with at least L or W present
        keep_mask = (~L.isna()) | (~W.isna())
        L2 = L[keep_mask]
        W2 = W[keep_mask]

        basidia_count = int(keep_mask.sum())
        if basidia_count == 0:
            logs.append((sid, sheet, "no_numeric_in_fixed_range", 0, 0, 0))
            continue

        # Sterigma fields
        S_counts = S_count_raw[keep_mask].map(parse_int_or_nan)
        S_lens   = pd.to_numeric(S_len_raw[keep_mask].map(parse_float_or_nan), errors="coerce").mask(lambda s: s <= 0)

        # Stats
        Ls = pct_stats_min_avg_max(L2)
        Ws = pct_stats_min_avg_max(W2)
        Ss = pct_stats_min_avg_max(S_lens)

        # Sterigma count categories
        s_counts_valid = S_counts.dropna().astype(int)
        c4 = int((s_counts_valid == 4).sum())
        c3 = int((s_counts_valid == 3).sum())
        c2 = int((s_counts_valid == 2).sum())
        c1 = int((s_counts_valid == 1).sum())

        recs.append({
            "specimen_id": str(sid),
            "basidia_count": basidia_count,
            "min_length": Ls["min"], "avg_length": Ls["mean"], "max_length": Ls["max"],
            "min_width":  Ws["min"], "avg_width": Ws["mean"],  "max_width": Ws["max"],
            "4s/basidia": c4, "3s/basidia": c3, "2s/basidia": c2, "s/basidia": c1,
            "min_s_length": Ss["min"], "avg_s_length": Ss["mean"], "max_s_length": Ss["max"],
        })

        logs.append((sid, sheet, "ok_fixed_range", basidia_count, int(Ss["count"]), int(L2.notna().sum()), int(W2.notna().sum())))

    summary_df = pd.DataFrame.from_records(recs)
    log_df = pd.DataFrame(
        logs,
        columns=["specimen_id","sheet","status","basidia_count","sterigma_len_count","len_nonnull","width_nonnull"]
    )
    return summary_df, log_df

# ========= Merge into basidia master =========
def main():
    summary, logdf = summarize_training_book_basidia_fixed(TRAINING_PATH)

    # Load master and ensure specimen_id is string
    master = pd.read_excel(MASTER_PATH, sheet_name=0, engine="openpyxl")
    master["specimen_id"] = master["specimen_id"].astype(str)

    updated = master.copy()
    if not summary.empty:
        summary["specimen_id"] = summary["specimen_id"].astype(str)

        update_cols = [
            "basidia_count",
            "min_length","avg_length","max_length",
            "min_width","avg_width","max_width",
            "4s/basidia","3s/basidia","2s/basidia","s/basidia",
            "min_s_length","avg_s_length","max_s_length",
        ]

        # Ensure columns exist in master
        for col in update_cols:
            if col not in updated.columns:
                updated[col] = np.nan

        # Update existing rows
        s_map = summary.set_index("specimen_id").to_dict(orient="index")
        for idx, row in updated.iterrows():
            sid = row["specimen_id"]
            if sid in s_map:
                for col in update_cols:
                    updated.at[idx, col] = s_map[sid].get(col, np.nan)

        # Append any parsed specimens not already present
        missing = summary[~summary["specimen_id"].isin(updated["specimen_id"])]
        if not missing.empty:
            to_append = missing.reindex(columns=updated.columns, fill_value=np.nan)
            updated = pd.concat([updated, to_append], ignore_index=True)

    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as w:
        updated.to_excel(w, index=False, sheet_name="basidia")
        logdf.to_excel(w, index=False, sheet_name="parse_log")

    print("Done ->", OUTPUT_PATH)

if __name__ == "__main__":
    main()