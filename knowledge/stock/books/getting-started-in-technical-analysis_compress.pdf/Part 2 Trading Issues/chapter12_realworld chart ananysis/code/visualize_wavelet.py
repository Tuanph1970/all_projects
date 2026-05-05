"""
Visualize the wavelet_decomposer outputs:
    Figure 14a — multi-resolution decomposition (trend + detail bands)
    Figure 14b — CWT scalogram with cone of influence
    Figure 14c — wavelet denoising vs original
    Figure 14d — multi-scale spike detection
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

sys.path.insert(0, os.path.dirname(__file__))
from wavelet_decomposer import (
    multi_resolution_decompose, scalogram, wavelet_denoise,
    multi_scale_spikes, coincident_spikes,
)

OUT = "/home/claude/obsidian_chapter12/images"

# ------------------------------------------------------------------
# Build a clean synthetic series that exercises every band
# ------------------------------------------------------------------
np.random.seed(42)
n = 256
dates = pd.date_range("2023-01-02", periods=n, freq="B")
t = np.arange(n)

signal = (
    100
    + 0.06 * t                                   # slow upward trend
    + 5.0 * np.sin(2 * np.pi * t / 80)           # 80-bar primary cycle
    + 2.0 * np.sin(2 * np.pi * t / 20)           # 20-bar secondary cycle
    + np.random.normal(0, 0.7, n)                # daily noise
)
# Two sharp single-bar shocks (like news events)
signal[120] += 6.0
signal[200] -= 5.0

close = pd.Series(signal, index=dates, name="close")

# ==================================================================
# Figure 14a — multi-resolution decomposition
# ==================================================================
mra = multi_resolution_decompose(close, wavelet="db4", levels=5)

fig, axes = plt.subplots(7, 1, figsize=(11, 9), sharex=True)
axes[0].plot(close.index, close.values, color="black", linewidth=0.9)
axes[0].set_ylabel("Price")
axes[0].set_title("Original close")
axes[0].grid(True, linestyle=":", alpha=0.4)

for i, d in enumerate(mra.details, start=1):
    axes[i].plot(d.index, d.values, color="#1f77b4", linewidth=0.8)
    axes[i].axhline(0, color="gray", linewidth=0.4)
    band_label = {1: "≈2-day", 2: "≈4-day", 3: "≈8-day",
                  4: "≈16-day", 5: "≈32-day"}[i]
    axes[i].set_ylabel(f"D{i}")
    axes[i].set_title(f"Detail band D{i} ({band_label} wiggles, "
                      f"{mra.energy_per_band()[f'D{i}']*100:.1f}% energy)",
                      fontsize=9)
    axes[i].grid(True, linestyle=":", alpha=0.4)

axes[-1].plot(mra.trend.index, mra.trend.values,
              color="#d62728", linewidth=1.2)
axes[-1].set_ylabel("Trend")
axes[-1].set_title(f"Trend / approximation A_5 "
                   f"({mra.energy_per_band()['trend']*100:.1f}% energy) — "
                   f"the genuine low-frequency component",
                   fontsize=9)
axes[-1].grid(True, linestyle=":", alpha=0.4)
axes[-1].set_xlabel("Date")

plt.suptitle("Multi-Resolution Decomposition — db4 wavelet, 5 levels\n"
             "Sum of all bands reconstructs the original to machine precision",
             fontsize=11)
plt.tight_layout()
plt.savefig(f"{OUT}/14a_mra_decomposition.png", dpi=140)
plt.close()

# ==================================================================
# Figure 14b — CWT scalogram with cone of influence
# ==================================================================
sg = scalogram(close, wavelet="morl", n_scales=64, min_scale=2.0)
power = sg.power()
coi = sg.cone_of_influence()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True,
                                gridspec_kw={"height_ratios": [1, 2.5]})

ax1.plot(close.index, close.values, color="black", linewidth=0.9)
ax1.set_ylabel("Price")
ax1.set_title("Close + CWT scalogram (Morlet wavelet)")
ax1.grid(True, linestyle=":", alpha=0.4)

# Use date numbers for the imshow extent so x-axis is consistent
import matplotlib.dates as mdates
date_nums = mdates.date2num(close.index.to_pydatetime())
extent = [date_nums[0], date_nums[-1], sg.scales[-1], sg.scales[0]]

im = ax2.imshow(power, aspect="auto", extent=extent, cmap="viridis",
                norm=LogNorm(vmin=power.max() * 1e-3, vmax=power.max()))
ax2.set_yscale("log")
ax2.set_ylabel("Scale (≈ wiggle width in bars)")
ax2.set_xlabel("Date")
ax2.xaxis_date()

# Cone of influence in date coords
ax2.plot(date_nums, np.maximum(coi, sg.scales[0]),
         color="white", linewidth=1.3, linestyle="--")
ax2.fill_between(date_nums, np.maximum(coi, sg.scales[0]), sg.scales[-1],
                 color="black", alpha=0.35, hatch="//", linewidth=0)

# Annotate the shock locations
for shock_idx, label in [(120, "shock ↑"), (200, "shock ↓")]:
    ax1.axvline(close.index[shock_idx], color="red",
                linewidth=0.8, linestyle=":")
    ax2.axvline(date_nums[shock_idx], color="red",
                linewidth=0.8, linestyle=":")
    ax1.text(close.index[shock_idx], close.max() * 0.99, label,
             color="red", fontsize=8, ha="right", va="top")

cbar = plt.colorbar(im, ax=ax2, fraction=0.04)
cbar.set_label("|W(a,b)|² (log)")

ax2.text(0.02, 0.05,
         "Shaded region = outside cone of influence\n"
         "(edge effects, results unreliable)",
         transform=ax2.transAxes, color="white", fontsize=8,
         bbox=dict(facecolor="black", alpha=0.5, edgecolor="none"))

plt.tight_layout()
plt.savefig(f"{OUT}/14b_scalogram.png", dpi=140)
plt.close()

# ==================================================================
# Figure 14c — wavelet denoising vs moving average
# ==================================================================
denoised = wavelet_denoise(close, levels=4, threshold_levels=2)
sma20 = close.rolling(20, center=True).mean()

fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(close.index, close.values, color="lightgray", linewidth=0.8,
        label="Original close")
ax.plot(sma20.index, sma20.values, color="#1f77b4", linewidth=1.4,
        label="20-bar SMA (lagged, smears shocks)")
ax.plot(denoised.index, denoised.values, color="#d62728", linewidth=1.4,
        label="Wavelet-denoised (no lag, preserves shocks)")

# Highlight the shock regions
for shock_idx, _ in [(120, "↑"), (200, "↓")]:
    ax.axvspan(close.index[shock_idx - 2], close.index[shock_idx + 2],
               color="yellow", alpha=0.25)

ax.set_xlabel("Date")
ax.set_ylabel("Price")
ax.set_title("Wavelet Denoising vs Moving Average\n"
             "Yellow bands mark shock events — note SMA smears them across "
             "many bars; wavelet preserves them as localized features",
             fontsize=10)
ax.grid(True, linestyle=":", alpha=0.4)
ax.legend(loc="upper left", fontsize=9)
plt.tight_layout()
plt.savefig(f"{OUT}/14c_denoising.png", dpi=140)
plt.close()

# ==================================================================
# Figure 14d — multi-scale spike detection (Mexican Hat matched filter)
# ==================================================================
spikes = multi_scale_spikes(close, scales=(4, 8, 16, 32), threshold_sigmas=2.0)
coinc = coincident_spikes(spikes, min_scales=2)

fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(close.index, close.values, color="black", linewidth=0.9, zorder=3)

# Mark spikes from each scale at offset y-positions
y_min = close.min()
y_max = close.max()
y_range = y_max - y_min
scale_colors = ["#ff7f0e", "#2ca02c", "#1f77b4", "#9467bd"]
scale_names = ["scale=4 (≈4-bar)", "scale=8 (≈8-bar)",
               "scale=16 (≈16-bar)", "scale=32 (≈32-bar)"]
for i, col in enumerate(spikes.columns):
    s = spikes[col]
    peaks = s[s > 0]
    troughs = s[s < 0]
    y_offset = y_min - (i + 1) * y_range * 0.04
    ax.scatter(peaks.index, [y_offset] * len(peaks), marker="^",
               color=scale_colors[i], s=35, label=scale_names[i],
               edgecolor="black", linewidth=0.3)
    ax.scatter(troughs.index, [y_offset] * len(troughs), marker="v",
               color=scale_colors[i], s=35,
               edgecolor="black", linewidth=0.3)

# Coincident detections in red
coinc_pos = coinc[coinc > 0]
coinc_neg = coinc[coinc < 0]
for ts in coinc_pos.index:
    ax.axvline(ts, color="red", linewidth=0.6, alpha=0.4)
for ts in coinc_neg.index:
    ax.axvline(ts, color="blue", linewidth=0.6, alpha=0.4)

ax.set_title("Multi-Scale Spike Detection (Mexican Hat wavelet as matched filter)\n"
             "Triangles mark per-scale detections; red lines = peaks confirmed at "
             "≥2 scales; blue lines = troughs confirmed at ≥2 scales",
             fontsize=10)
ax.set_xlabel("Date")
ax.set_ylabel("Price")
ax.grid(True, linestyle=":", alpha=0.4)
ax.legend(loc="upper left", fontsize=8, ncol=2)
plt.tight_layout()
plt.savefig(f"{OUT}/14d_multiscale_spikes.png", dpi=140)
plt.close()

print("Generated:")
for f in ["14a_mra_decomposition.png", "14b_scalogram.png",
          "14c_denoising.png", "14d_multiscale_spikes.png"]:
    print(f"  {OUT}/{f}")
