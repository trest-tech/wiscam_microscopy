import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np

# Load data
df = pd.read_csv("basidiospore_filled.csv")

# Keep only sections that have at least one row with measurements
valid_sections = df.groupby("sectionid").filter(
    lambda g: g["avg_length"].notna().any() and g["avg_width"].notna().any()
)["sectionid"].unique()

n_sections = len(valid_sections)

# Determine grid layout
n_cols = int(np.ceil(np.sqrt(n_sections)))
n_rows = int(np.ceil(n_sections / n_cols))

fig, axes = plt.subplots(
    n_rows, n_cols,
    figsize=(4*n_cols, 4*n_rows),
    sharex=True, sharey=True
)
axes = axes.flatten()

# Global axis limits - use same scale for both axes
x_min = df["min_width"].min()
x_max = df["max_width"].max()
y_min = df["min_length"].min()
y_max = df["max_length"].max()

# Calculate overall min and max across both dimensions
overall_min = min(x_min, y_min)
overall_max = max(x_max, y_max)

for ax, section in zip(axes, valid_sections):
    sub = df[df["sectionid"] == section]
    species_in_section = sub["species"].unique()
    
    # Assign colors to species
    colors = plt.cm.tab10(np.linspace(0, 1, len(species_in_section)))
    
    for i, species in enumerate(species_in_section):
        species_data = sub[sub["species"] == species]
        
        # Build 10–90 percentile crosshairs
        vertical_segments = [
            [(species_data.loc[j, "avg_width"], species_data.loc[j, "10_length"]),
             (species_data.loc[j, "avg_width"], species_data.loc[j, "90_length"])]
            for j in species_data.index
        ]
        
        horizontal_segments = [
            [(species_data.loc[j, "10_width"], species_data.loc[j, "avg_length"]),
             (species_data.loc[j, "90_width"], species_data.loc[j, "avg_length"])]
            for j in species_data.index
        ]
        
        ax.add_collection(LineCollection(vertical_segments, colors=colors[i], linewidths=1, alpha=0.5))
        ax.add_collection(LineCollection(horizontal_segments, colors=colors[i], linewidths=1, alpha=0.5))
        
        # Center points
        ax.scatter(species_data["avg_width"], species_data["avg_length"], color=colors[i], s=15, alpha=0.8, label=species)
    
    ax.set_title(section)
    ax.set_xlim(overall_min, overall_max)
    ax.set_ylim(overall_min, overall_max)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize="small", loc="center left", bbox_to_anchor=(1, 0.5))
# Hide unused axes
for ax in axes[n_sections:]:
    ax.axis("off")

fig.suptitle("Spore Morphology by Section (10–90 Percentile Crosshairs)", fontsize=16)
fig.text(0.5, 0.04, "Width", ha="center")
fig.text(0.04, 0.5, "Length", va="center", rotation="vertical")

plt.tight_layout(rect=[0.05, 0.05, 1, 0.95])
plt.show()
