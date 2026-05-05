"""
Visualize EMD and STL decompositions:
    Figure 15a — EMD decomposition (price + IMFs + residual)
    Figure 15b — EMD vs EEMD: mode-mixing comparison
    Figure 15c — STL decomposition (trend + seasonal + remainder)
    Figure 15d — Cross-method comparison: trend extraction (DWT vs EMD vs STL)
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from emd_stl_decomposer import emd_decompose, stl_decompose, emd_denoise
from wavelet_decomposer import multi_resolution_decompose

OUT = "/home/claude/obsidian_chapter12/images"

# ------------------------------------------------------------------
# Same synthetic series as before so visualisations are comparable
# ------------------------------------------------------------------
np.random.seed(42)
n = 252
dates = pd.date_range("2023-01-02", periods=n, freq="B")
t = np.arange(n)
signal = (
    100
    + 0.04 * t
    + 4.0 * np.sin(2 * np.pi * t / 80)
    + 1.5 * np.sin(2 * np.pi * t / 21)
    + 0.5 * np.sin(2 * np.pi * t / 5)
    + np.random.normal(0, 0.6, n)
)
signal[120] += 6.0
signal[200] -= 5.0
close = pd.Series(signal, index=dates, name="close")

# ==================================================================
# Figure 15a — EMD decomposition
# ==================================================================
emd_result = emd_decompose(close)
n_imfs = emd_result.n_imfs()
periods = emd_result.dominant_period_per_imf()
energies = emd_result.energy_per_imf()

fig, axes = plt.subplots(n_imfs + 2, 1, figsize=(11, 1.5 * (n_imfs + 2)),
                          sharex=True)

axes[0].plot(close.index, close.values, color="black", linewidth=0.9)
axes[0].set_ylabel("Price")
axes[0].set_title("Original close")
axes[0].grid(True, linestyle=":", alpha=0.4)

for i, imf in enumerate(emd_result.imfs):
    ax = axes[i + 1]
    ax.plot(imf.index, imf.values, color="#1f77b4", linewidth=0.8)
    ax.axhline(0, color="gray", linewidth=0.4)
    ax.set_ylabel(f"IMF{i+1}")
    period = periods[f"IMF{i+1}"]
    period_str = "monotonic" if period == float("inf") else f"≈{period:.0f} bars"
    energy_pct = energies[f"IMF{i+1}"] * 100
    ax.set_title(f"IMF{i+1} (period {period_str}, {energy_pct:.1f}% energy)",
                 fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.4)

axes[-1].plot(emd_result.residual.index, emd_result.residual.values,
              color="#d62728", linewidth=1.2)
axes[-1].set_ylabel("Residual")
axes[-1].set_title(f"Residual (the data-driven trend, "
                   f"{energies['residual']*100:.1f}% energy)",
                   fontsize=9)
axes[-1].grid(True, linestyle=":", alpha=0.4)
axes[-1].set_xlabel("Date")

plt.suptitle("Empirical Mode Decomposition — adaptive, no fixed basis\n"
             f"Sum of {n_imfs} IMFs + residual reconstructs the original "
             f"to ~10⁻¹⁴",
             fontsize=11)
plt.tight_layout()
plt.savefig(f"{OUT}/15a_emd_decomposition.png", dpi=140)
plt.close()
print(f"Wrote 15a_emd_decomposition.png ({n_imfs} IMFs found)")


# ==================================================================
# Figure 15b — EMD vs EEMD comparison
# ==================================================================
eemd_result = emd_decompose(close, method="EEMD",
                            eemd_trials=50, noise_std=0.2, seed=7)

n_imfs_emd  = emd_result.n_imfs()
n_imfs_eemd = eemd_result.n_imfs()
n_rows = max(n_imfs_emd, n_imfs_eemd) + 1

fig, axes = plt.subplots(n_rows, 2, figsize=(13, 1.4 * n_rows), sharex=True)
axes[0, 0].plot(close.index, close.values, color="black", linewidth=0.9)
axes[0, 0].set_title(f"EMD ({n_imfs_emd} IMFs)", fontsize=10)
axes[0, 1].plot(close.index, close.values, color="black", linewidth=0.9)
axes[0, 1].set_title(f"EEMD ({n_imfs_eemd} IMFs, "
                     f"50 trials, noise=0.2σ)", fontsize=10)
for ax in (axes[0, 0], axes[0, 1]):
    ax.set_ylabel("Price")
    ax.grid(True, linestyle=":", alpha=0.4)

# EMD column
for i, imf in enumerate(emd_result.imfs):
    ax = axes[i + 1, 0]
    ax.plot(imf.index, imf.values, color="#1f77b4", linewidth=0.7)
    ax.axhline(0, color="gray", linewidth=0.4)
    ax.set_ylabel(f"IMF{i+1}")
    ax.grid(True, linestyle=":", alpha=0.4)

# EEMD column
for i, imf in enumerate(eemd_result.imfs):
    ax = axes[i + 1, 1]
    ax.plot(imf.index, imf.values, color="#2ca02c", linewidth=0.7)
    ax.axhline(0, color="gray", linewidth=0.4)
    ax.set_ylabel(f"IMF{i+1}")
    ax.grid(True, linestyle=":", alpha=0.4)

# Hide unused rows
for i in range(n_imfs_emd + 1, n_rows):
    axes[i, 0].axis("off")
for i in range(n_imfs_eemd + 1, n_rows):
    axes[i, 1].axis("off")

axes[-1, 0].set_xlabel("Date")
axes[-1, 1].set_xlabel("Date")
plt.suptitle("EMD vs EEMD — ensemble averaging tends to produce "
             "cleaner mode separation\n"
             "(IMF count and content can differ between the two)",
             fontsize=11)
plt.tight_layout()
plt.savefig(f"{OUT}/15b_emd_vs_eemd.png", dpi=140)
plt.close()
print("Wrote 15b_emd_vs_eemd.png")


# ==================================================================
# Figure 15c — STL decomposition
# ==================================================================
stl_monthly = stl_decompose(close, period=21, seasonal=7, robust=True)
stl_weekly  = stl_decompose(close, period=5,  seasonal=7, robust=True)

fig, axes = plt.subplots(4, 2, figsize=(13, 8), sharex=True)
fig.suptitle("STL Decomposition — trend + seasonal + remainder\n"
             "Left: period=21 (monthly cycle).  "
             "Right: period=5 (weekly / day-of-week effects)",
             fontsize=11)

for col, (label, d) in enumerate([("monthly (P=21)", stl_monthly),
                                    ("weekly (P=5)",  stl_weekly)]):
    axes[0, col].plot(close.index, close.values, color="black", linewidth=0.9)
    axes[0, col].set_title(f"Original close — {label}", fontsize=10)
    axes[0, col].set_ylabel("Price")
    axes[0, col].grid(True, linestyle=":", alpha=0.4)

    axes[1, col].plot(d.trend.index, d.trend.values,
                       color="#d62728", linewidth=1.3)
    axes[1, col].set_title(f"Trend (strength={d.strength_of_trend():.2f})",
                            fontsize=9)
    axes[1, col].grid(True, linestyle=":", alpha=0.4)

    axes[2, col].plot(d.seasonal.index, d.seasonal.values,
                       color="#1f77b4", linewidth=0.8)
    axes[2, col].axhline(0, color="gray", linewidth=0.4)
    axes[2, col].set_title(
        f"Seasonal (strength={d.strength_of_seasonality():.2f})",
        fontsize=9)
    axes[2, col].grid(True, linestyle=":", alpha=0.4)

    axes[3, col].plot(d.remainder.index, d.remainder.values,
                       color="#7f7f7f", linewidth=0.7)
    axes[3, col].axhline(0, color="gray", linewidth=0.4)
    axes[3, col].set_title("Remainder", fontsize=9)
    axes[3, col].grid(True, linestyle=":", alpha=0.4)
    axes[3, col].set_xlabel("Date")

plt.tight_layout()
plt.savefig(f"{OUT}/15c_stl_decomposition.png", dpi=140)
plt.close()
print("Wrote 15c_stl_decomposition.png")


# ==================================================================
# Figure 15d — Trend extraction: DWT vs EMD vs STL
# ==================================================================
mra = multi_resolution_decompose(close, wavelet="db4", levels=5)
sma_50 = close.rolling(50, center=True).mean()

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(close.index, close.values, color="lightgray", linewidth=0.8,
        label="Original close", zorder=1)
ax.plot(sma_50.index, sma_50.values, color="#7f7f7f", linewidth=1.4,
        linestyle="--", label="50-bar SMA (centered)", zorder=2)
ax.plot(mra.trend.index, mra.trend.values, color="#1f77b4", linewidth=1.6,
        label="Wavelet trend (db4, A_5)", zorder=3)
ax.plot(emd_result.residual.index, emd_result.residual.values,
        color="#d62728", linewidth=1.6,
        label="EMD residual", zorder=4)
ax.plot(stl_monthly.trend.index, stl_monthly.trend.values,
        color="#2ca02c", linewidth=1.6,
        label="STL trend (P=21)", zorder=5)

# Mark shocks
for shock_idx in (120, 200):
    ax.axvline(close.index[shock_idx], color="orange",
               linewidth=0.6, linestyle=":", alpha=0.6)

ax.set_xlabel("Date")
ax.set_ylabel("Price")
ax.set_title("Trend Extraction Compared — Same Series, Four Methods\n"
             "Each method makes different assumptions about what 'trend' means",
             fontsize=11)
ax.legend(loc="upper left", fontsize=9)
ax.grid(True, linestyle=":", alpha=0.4)
plt.tight_layout()
plt.savefig(f"{OUT}/15d_trend_comparison.png", dpi=140)
plt.close()
print("Wrote 15d_trend_comparison.png")
