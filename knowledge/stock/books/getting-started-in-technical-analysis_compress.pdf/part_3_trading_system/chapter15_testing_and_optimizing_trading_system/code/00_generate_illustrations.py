"""
Chapter 15 - Illustration Generator
Generates all visualizations referenced in the chapter 15 Obsidian notes.

Each figure conceptually mirrors what Schwager describes in the chapter.
Illustrations are reconstructed from synthetic data (not reproduced from the book).
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

np.random.seed(42)
OUT = os.path.join(os.path.dirname(__file__), "..", "images")
os.makedirs(OUT, exist_ok=True)


def synthetic_price_series(n=500, drift=0.0002, vol=0.015, start=100.0):
    """Geometric Brownian motion-style price series."""
    rets = np.random.normal(drift, vol, n)
    return start * np.exp(np.cumsum(rets))


# ---------------------------------------------------------------
# Fig 1 — The Well-Chosen Example (cherry-pick illusion)
# ---------------------------------------------------------------
def fig_well_chosen_example():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # LEFT: cherry-picked window where every signal happens to win
    np.random.seed(7)
    p1 = synthetic_price_series(120, drift=0.004, vol=0.012)
    axes[0].plot(p1, color="#1f77b4", lw=1.4)
    buys  = [10, 55, 95]
    sells = [30, 75, 115]
    axes[0].scatter(buys,  [p1[i] for i in buys],  marker="^", s=110, c="green", label="Buy", zorder=5)
    axes[0].scatter(sells, [p1[i] for i in sells], marker="v", s=110, c="red",   label="Sell", zorder=5)
    axes[0].set_title("Seminar slide: every Buy < Sell\n(\"the well-chosen example\")",
                      fontsize=11)
    axes[0].set_xlabel("Day"); axes[0].set_ylabel("Price")
    axes[0].legend(loc="lower right"); axes[0].grid(alpha=0.3)

    # RIGHT: same system on a different window — losses
    np.random.seed(99)
    p2 = synthetic_price_series(120, drift=-0.001, vol=0.018)
    axes[1].plot(p2, color="#1f77b4", lw=1.4)
    buys2  = [15, 50, 90]
    sells2 = [35, 70, 110]
    axes[1].scatter(buys2,  [p2[i] for i in buys2],  marker="^", s=110, c="green", zorder=5)
    axes[1].scatter(sells2, [p2[i] for i in sells2], marker="v", s=110, c="red",   zorder=5)
    axes[1].set_title("Same system, different period:\nbuys above sells (you lose)",
                      fontsize=11)
    axes[1].set_xlabel("Day"); axes[1].grid(alpha=0.3)

    fig.suptitle("Concept 1 — The Well-Chosen Example",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/01_well_chosen_example.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 2 — Parameter / Parameter Set (breakout w/ different N)
# ---------------------------------------------------------------
def fig_parameter_set():
    np.random.seed(3)
    p = synthetic_price_series(200, drift=0.001, vol=0.02)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, N in zip(axes, [7, 40]):
        ax.plot(p, lw=1.3, color="#444")
        # crude breakout signals: close > rolling-N high
        for i in range(N, len(p)):
            if p[i] > max(p[i-N:i]):
                ax.scatter(i, p[i], marker="^", s=55, c="green", zorder=5)
            elif p[i] < min(p[i-N:i]):
                ax.scatter(i, p[i], marker="v", s=55, c="red", zorder=5)
        ax.set_title(f"Breakout system, parameter set: N = {N}", fontsize=11)
        ax.set_xlabel("Day"); ax.grid(alpha=0.3)
    axes[0].set_ylabel("Price")
    fig.suptitle("Concept 2 — Parameter & Parameter Set\n(same system rules, different signal timing)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/02_parameter_set.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 3 — Time Stability across sub-periods
# ---------------------------------------------------------------
def fig_time_stability():
    years = np.arange(1, 16)
    np.random.seed(11)
    # System A: 3 huge years carry the rest
    a = np.random.normal(2, 4, 15); a[[3, 8, 11]] = [55, 48, 60]
    # System B: steady wins
    b = np.random.normal(11, 4, 15); b[2] = -3

    fig, ax = plt.subplots(figsize=(11, 4.5))
    w = 0.4
    ax.bar(years - w/2, a, w, label="System A (lumpy: 3 hero years)",
           color="#d62728", alpha=0.85)
    ax.bar(years + w/2, b, w, label="System B (time-stable)",
           color="#2ca02c", alpha=0.85)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xlabel("Year"); ax.set_ylabel("Annual return (%)")
    ax.set_title("Concept 3 — Time Stability\n(same total return, very different reliability)",
                 fontsize=13, fontweight="bold")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(f"{OUT}/03_time_stability.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 4 — Slippage + Limit Days
# ---------------------------------------------------------------
def fig_slippage():
    days = np.arange(20)
    # build a price path with a 'limit-up' gap
    p = np.array([100, 101, 100.5, 102, 103, 105, 107,
                  112, 117, 122, 121, 122, 124, 123, 125,
                  127, 128, 126, 128, 130], dtype=float)

    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(days, p, "o-", color="#1f77b4", lw=1.6)

    # signal generated at day 6 close — but next day gaps up (limit move)
    sig_day = 6;   sig_px  = p[sig_day]
    fill_day = 9;  fill_px = p[fill_day]

    ax.scatter(sig_day,  sig_px,  marker="^", s=150, c="green",  zorder=5,
               label=f"Signal price (theoretical) = {sig_px:.2f}")
    ax.scatter(fill_day, fill_px, marker="X", s=150, c="orange", zorder=5,
               label=f"Actual fill price = {fill_px:.2f}")

    ax.annotate("3-day limit-locked gap\n(no execution possible)",
                xy=(7.5, 115), xytext=(2, 122),
                arrowprops=dict(arrowstyle="->", color="black"),
                fontsize=10)
    ax.fill_betweenx([100, 132], 7, 9, color="red", alpha=0.12)

    ax.set_xlabel("Day"); ax.set_ylabel("Price")
    ax.set_title("Concept 4 — Slippage & Limit Days\n(paper P&L vs. real-world fill)",
                 fontsize=13, fontweight="bold")
    ax.legend(loc="lower right"); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/04_slippage.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 5 — Parameter Stability heatmap
# ---------------------------------------------------------------
def fig_parameter_stability():
    short = np.arange(2, 21)
    long_ = np.arange(20, 81, 4)
    SH, LO = np.meshgrid(short, long_)

    # synthetic profit landscape: broad plateau + one isolated lucky spike
    profit = (
        100 * np.exp(-((SH - 10)**2 + (LO - 50)**2) / 600)
        + 130 * np.exp(-((SH - 5)**2 + (LO - 25)**2) / 6)   # lucky spike
        + np.random.normal(0, 8, SH.shape)
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(profit, aspect="auto", origin="lower", cmap="RdYlGn",
                   extent=[short.min(), short.max(), long_.min(), long_.max()])
    plt.colorbar(im, ax=ax, label="Simulated profit ($)")

    # circle the lucky fluke and the broad plateau
    ax.scatter([5], [25], s=400, facecolors="none", edgecolors="black", linewidths=2)
    ax.text(5.5, 27, "Lucky fluke\n(unstable)", fontsize=9)
    ax.scatter([10], [50], s=900, facecolors="none", edgecolors="blue", linewidths=2)
    ax.text(11, 53, "Broad plateau\n(stable region — choose here)",
            fontsize=9, color="blue")

    ax.set_xlabel("Short MA length"); ax.set_ylabel("Long MA length")
    ax.set_title("Concept 5 — Parameter Stability\n(prefer broad plateaus over isolated peaks)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/05_parameter_stability.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 6 — Testing vs Fitting (curve fitting)
# ---------------------------------------------------------------
def fig_testing_vs_fitting():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    np.random.seed(5)

    # In-sample (where we 'fit')
    n = 200
    in_sample = synthetic_price_series(n, drift=0.001, vol=0.02)
    # Equity curve from a heavily over-fit system
    overfit_eq = np.cumsum(np.abs(np.random.normal(80, 25, n)))
    realistic_eq = np.cumsum(np.random.normal(20, 60, n))

    axes[0].plot(overfit_eq, color="green", lw=2,
                 label="Curve-fit system\n(in-sample)")
    axes[0].plot(realistic_eq, color="gray", lw=1.5, alpha=0.7,
                 label="Honest system\n(in-sample)")
    axes[0].set_title("In-sample period (1985-1996)\n— anything looks great here",
                      fontsize=11)
    axes[0].set_ylabel("Equity ($)"); axes[0].set_xlabel("Day")
    axes[0].legend(); axes[0].grid(alpha=0.3)

    # Out-of-sample (the truth)
    overfit_oos  = np.cumsum(np.random.normal(-30, 90, n))
    realistic_oos = np.cumsum(np.random.normal(15, 65, n))
    axes[1].plot(overfit_oos, color="green", lw=2,
                 label="Curve-fit system\n(out-of-sample)")
    axes[1].plot(realistic_oos, color="gray", lw=1.5, alpha=0.7,
                 label="Honest system\n(out-of-sample)")
    axes[1].axhline(0, color="black", lw=0.5)
    axes[1].set_title("Out-of-sample period (1997-1998)\n— curve-fit collapses",
                      fontsize=11)
    axes[1].set_xlabel("Day"); axes[1].legend(); axes[1].grid(alpha=0.3)

    fig.suptitle("Concept 6 — Testing vs Fitting", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/06_testing_vs_fitting.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 7 — Blind (walk-forward) Simulation
# ---------------------------------------------------------------
def fig_blind_simulation():
    fig, ax = plt.subplots(figsize=(11, 3.5))

    folds = [
        ("1985-1992", "1993-1994"),
        ("1987-1994", "1995-1996"),
        ("1989-1996", "1997-1998"),
    ]
    y_positions = [0.7, 0.4, 0.1]

    for (opt, test), y in zip(folds, y_positions):
        ax.barh(y, 8, left=int(opt.split("-")[0]) - 1985, height=0.18,
                color="#1f77b4", alpha=0.85)
        ax.barh(y, 2, left=int(test.split("-")[0]) - 1985, height=0.18,
                color="#d62728", alpha=0.85)
        ax.text(int(opt.split("-")[0]) - 1985 + 0.2, y,
                f"OPTIMIZE on {opt}", va="center", color="white", fontsize=9, fontweight="bold")
        ax.text(int(test.split("-")[0]) - 1985 + 0.1, y,
                f"TEST on {test}", va="center", color="white", fontsize=9, fontweight="bold")

    ax.set_xlim(0, 14); ax.set_ylim(0, 1)
    ax.set_yticks([]); ax.set_xticks([])
    ax.set_title("Concept 7 — Blind Simulation (walk-forward)\n"
                 "Pick parameters from past data only, then test on the future you 'haven't seen'",
                 fontsize=13, fontweight="bold")

    # legend
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#1f77b4", label="In-sample (optimize)"),
                       Patch(color="#d62728", label="Out-of-sample (test)")],
              loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{OUT}/07_blind_simulation.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 8 — Optimized vs Average parameter-set performance
# ---------------------------------------------------------------
def fig_avg_paramset():
    np.random.seed(13)
    sets = np.arange(1, 51)
    in_sample  = np.sort(np.random.normal(20, 30, 50))[::-1]   # ranked
    out_sample = np.random.normal(8, 25, 50)                   # uncorrelated

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(sets - 0.2, in_sample,  0.4, label="In-sample return (%)", color="#1f77b4")
    ax.bar(sets + 0.2, out_sample, 0.4, label="Out-of-sample return (%)", color="#ff7f0e")
    ax.axhline(np.mean(out_sample), color="green", ls="--", lw=2,
               label=f"Avg of all sets (OOS) = {np.mean(out_sample):.1f}%")
    ax.axhline(out_sample[0], color="red", ls="--", lw=2,
               label=f"Best in-sample set, OOS realized = {out_sample[0]:.1f}%")
    ax.set_xlabel("Parameter set (ranked by in-sample return)")
    ax.set_ylabel("Return (%)")
    ax.set_title("Concept 8 — Average Parameter-Set Performance\n"
                 "Best in-sample ≠ best out-of-sample. The mean is more honest.",
                 fontsize=13, fontweight="bold")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(f"{OUT}/08_avg_parameter_set.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 9 — Schwager's Corollary illustration
# ---------------------------------------------------------------
def fig_schwagers_corollary():
    fig, ax = plt.subplots(figsize=(10, 4.5))

    days = np.arange(0, 365 * 3)
    honest    = 100_000 * (1 + 0.18) ** (days / 365)        # realistic 18%
    optimistic = 100_000 * (1 + 1.00) ** (days / 365)       # 100% claim
    fraud     = 100_000 * (1 + 4.00) ** (days / 365)        # 400% brochure

    ax.plot(days, honest,     label="Honest simulation: 18% / yr",   color="green",  lw=2)
    ax.plot(days, optimistic, label="Glossy ad: 100% / yr",          color="orange", lw=2)
    ax.plot(days, fraud,      label="\"$299 system\": 400% / yr",     color="red",    lw=2)

    ax.set_yscale("log")
    ax.set_xlabel("Days"); ax.set_ylabel("Account value ($, log scale)")
    ax.set_title("Concept 9 — Schwager's Corollary: bad simulations drive out good\n"
                 "(realistic numbers look puny next to fantasy claims)",
                 fontsize=13, fontweight="bold")
    ax.legend(); ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(f"{OUT}/09_schwagers_corollary.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------
# Fig 10 — Multimarket testing (return/risk per market)
# ---------------------------------------------------------------
def fig_multimarket():
    markets = ["Coffee", "Sugar", "Crude Oil", "Gold", "Corn",
               "Wheat", "S&P 500", "Cocoa", "Soybeans", "Cotton"]
    np.random.seed(42)
    ret = np.random.normal(15, 10, len(markets))
    risk = np.random.uniform(8, 25, len(markets))

    fig, ax = plt.subplots(figsize=(10, 5))
    sc = ax.scatter(risk, ret, s=180, c=ret/risk, cmap="RdYlGn", edgecolors="black")
    for r, x, m in zip(ret, risk, markets):
        ax.annotate(m, (x, r), xytext=(5, 5), textcoords="offset points", fontsize=9)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xlabel("Max drawdown (%)"); ax.set_ylabel("Annual return (%)")
    ax.set_title("Concept 10 — Multimarket Testing\n"
                 "A good system should show return/risk merit across most markets",
                 fontsize=13, fontweight="bold")
    plt.colorbar(sc, ax=ax, label="Return / Risk")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/10_multimarket.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    print("Generating Chapter 15 illustrations...")
    fig_well_chosen_example()
    fig_parameter_set()
    fig_time_stability()
    fig_slippage()
    fig_parameter_stability()
    fig_testing_vs_fitting()
    fig_blind_simulation()
    fig_avg_paramset()
    fig_schwagers_corollary()
    fig_multimarket()
    print(f"All figures written to: {OUT}")
    for f in sorted(os.listdir(OUT)):
        print(f"  - {f}")
