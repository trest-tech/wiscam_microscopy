import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# Load your CSV
df = pd.read_csv("basidiospore_filled.csv")

fig, ax = plt.subplots(figsize=(8, 6))

# Build min–max crosshair segments
vertical_segments = [
    [(df.loc[i, "avg_width"], df.loc[i, "min_length"]),
     (df.loc[i, "avg_width"], df.loc[i, "max_length"])]
    for i in df.index
]

horizontal_segments = [
    [(df.loc[i, "min_width"], df.loc[i, "avg_length"]),
     (df.loc[i, "max_width"], df.loc[i, "avg_length"])]
    for i in df.index
]

# Optional: 10–90 percentile inner crosshair
vertical_inner = [
    [(df.loc[i, "avg_width"], df.loc[i, "10_length"]),
     (df.loc[i, "avg_width"], df.loc[i, "90_length"])]
    for i in df.index
]

horizontal_inner = [
    [(df.loc[i, "10_width"], df.loc[i, "avg_length"]),
     (df.loc[i, "90_width"], df.loc[i, "avg_length"])]
    for i in df.index
]

# Add outer (min–max) crosshairs
ax.add_collection(LineCollection(vertical_segments, colors="black", linewidths=1))
ax.add_collection(LineCollection(horizontal_segments, colors="black", linewidths=1))

# Add inner (10–90) crosshairs
ax.add_collection(LineCollection(vertical_inner, colors="blue", linewidths=2))
ax.add_collection(LineCollection(horizontal_inner, colors="blue", linewidths=2))

# Add center points
ax.scatter(df["avg_width"], df["avg_length"], color="red", s=20, alpha=0.7)

ax.set_xlabel("Width")
ax.set_ylabel("Length")
ax.set_title("Spore Measurements with Min–Max and 10–90 Crosshairs")

plt.tight_layout()
plt.show()
