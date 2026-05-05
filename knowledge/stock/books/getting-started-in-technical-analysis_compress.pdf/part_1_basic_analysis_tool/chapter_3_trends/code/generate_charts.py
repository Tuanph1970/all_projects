"""Generate illustrative charts for each Chapter 3 concept."""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

plt.rcParams.update({
    "figure.figsize": (10, 5.5),
    "figure.dpi": 110,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

OUT = "/home/claude/ch3/images"

def make_dates(n, start="2024-01-02"):
    base = datetime.fromisoformat(start)
    return [base + timedelta(days=i) for i in range(n)]

# ---------- 1. UPTREND: higher highs / higher lows ----------
np.random.seed(7)
n = 80
trend = np.linspace(100, 130, n)
noise = np.cumsum(np.random.normal(0, 0.6, n))
price = trend + noise
# inject clear RH/RL pattern
price[10] += 2; price[15] -= 2
price[28] += 3; price[33] -= 1.5
price[48] += 4; price[55] -= 1
price[68] += 3.5
dates = make_dates(n)

fig, ax = plt.subplots()
ax.plot(dates, price, color="#1f77b4", lw=1.6)
RH = [10, 28, 48, 68]
RL = [15, 33, 55]
for i in RH:
    ax.scatter(dates[i], price[i] + 0.4, color="#2ca02c", marker="v", s=70, zorder=5)
    ax.text(dates[i], price[i] + 1.2, "RH", color="#2ca02c", ha="center", fontsize=9, fontweight="bold")
for i in RL:
    ax.scatter(dates[i], price[i] - 0.4, color="#d62728", marker="^", s=70, zorder=5)
    ax.text(dates[i], price[i] - 1.6, "RL", color="#d62728", ha="center", fontsize=9, fontweight="bold")
ax.set_title("Uptrend — Higher Highs (RH) and Higher Lows (RL)")
ax.set_ylabel("Price")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/01_uptrend_highs_lows.png", bbox_inches="tight")
plt.close()

# ---------- 2. DOWNTREND ----------
np.random.seed(11)
n = 80
trend = np.linspace(130, 100, n)
noise = np.cumsum(np.random.normal(0, 0.6, n))
price = trend + noise
price[10] -= 2; price[15] += 2
price[28] -= 3; price[33] += 1.5
price[48] -= 4; price[55] += 1
price[68] -= 3.5
dates = make_dates(n)

fig, ax = plt.subplots()
ax.plot(dates, price, color="#d62728", lw=1.6)
RL = [10, 28, 48, 68]
RH = [15, 33, 55]
for i in RL:
    ax.scatter(dates[i], price[i] - 0.4, color="#d62728", marker="^", s=70, zorder=5)
    ax.text(dates[i], price[i] - 1.6, "RL", color="#d62728", ha="center", fontsize=9, fontweight="bold")
for i in RH:
    ax.scatter(dates[i], price[i] + 0.4, color="#2ca02c", marker="v", s=70, zorder=5)
    ax.text(dates[i], price[i] + 1.2, "RH", color="#2ca02c", ha="center", fontsize=9, fontweight="bold")
ax.set_title("Downtrend — Lower Lows (RL) and Lower Highs (RH)")
ax.set_ylabel("Price")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/02_downtrend_highs_lows.png", bbox_inches="tight")
plt.close()

# ---------- 3. UPTREND LINE (connecting higher lows) ----------
np.random.seed(3)
n = 100
trend = np.linspace(50, 80, n)
noise = np.cumsum(np.random.normal(0, 0.4, n))
price = trend + noise
# anchor lows
lows_idx = [12, 38, 70]
for i, idx in enumerate(lows_idx):
    price[idx] = trend[idx] - 1.5
dates = make_dates(n)
# trend line through first two anchor lows extrapolated
x0, x1 = lows_idx[0], lows_idx[-1]
y0, y1 = price[lows_idx[0]], price[lows_idx[1]]
slope = (price[lows_idx[1]] - price[lows_idx[0]]) / (lows_idx[1] - lows_idx[0])
xs = np.array([lows_idx[0] - 3, n - 1])
ys = price[lows_idx[0]] + slope * (xs - lows_idx[0])

fig, ax = plt.subplots()
ax.plot(dates, price, color="#1f77b4", lw=1.5)
ax.plot([dates[int(xs[0])], dates[int(xs[1])]], ys, color="#ff7f0e", lw=2, label="Uptrend line")
for idx in lows_idx:
    ax.scatter(dates[idx], price[idx], color="#d62728", s=55, zorder=5)
ax.set_title("Uptrend Line — drawn through successive higher lows")
ax.set_ylabel("Price")
ax.legend(loc="upper left", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/03_uptrend_line.png", bbox_inches="tight")
plt.close()

# ---------- 4. DOWNTREND LINE ----------
np.random.seed(5)
n = 100
trend = np.linspace(80, 50, n)
noise = np.cumsum(np.random.normal(0, 0.4, n))
price = trend + noise
highs_idx = [12, 38, 70]
for idx in highs_idx:
    price[idx] = trend[idx] + 1.5
dates = make_dates(n)
slope = (price[highs_idx[1]] - price[highs_idx[0]]) / (highs_idx[1] - highs_idx[0])
xs = np.array([highs_idx[0] - 3, n - 1])
ys = price[highs_idx[0]] + slope * (xs - highs_idx[0])

fig, ax = plt.subplots()
ax.plot(dates, price, color="#d62728", lw=1.5)
ax.plot([dates[int(xs[0])], dates[int(xs[1])]], ys, color="#ff7f0e", lw=2, label="Downtrend line")
for idx in highs_idx:
    ax.scatter(dates[idx], price[idx], color="#2ca02c", s=55, zorder=5)
ax.set_title("Downtrend Line — drawn through successive lower highs")
ax.set_ylabel("Price")
ax.legend(loc="upper right", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/04_downtrend_line.png", bbox_inches="tight")
plt.close()

# ---------- 5. TREND CHANNEL ----------
np.random.seed(2)
n = 120
slope = 0.25
base = 50 + slope * np.arange(n)
osc = 3 * np.sin(np.linspace(0, 5 * np.pi, n))
noise = np.random.normal(0, 0.4, n)
price = base + osc + noise
dates = make_dates(n)
lower = base - 3
upper = base + 3

fig, ax = plt.subplots()
ax.plot(dates, price, color="#1f77b4", lw=1.5)
ax.plot(dates, lower, color="#ff7f0e", lw=2, label="Uptrend line (support)")
ax.plot(dates, upper, color="#9467bd", lw=2, ls="--", label="Parallel return line (resistance)")
ax.fill_between(dates, lower, upper, color="#ff7f0e", alpha=0.07)
ax.set_title("Trend Channel — parallel lines enclosing the trend")
ax.set_ylabel("Price")
ax.legend(loc="upper left", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/05_trend_channel.png", bbox_inches="tight")
plt.close()

# ---------- 6. TREND-LINE RULES (entry on touch, sell on close-below penetration) ----------
np.random.seed(8)
n = 100
slope = 0.18
base = 60 + slope * np.arange(n)
osc = 2.5 * np.sin(np.linspace(0, 4 * np.pi, n))
noise = np.random.normal(0, 0.3, n)
price = base + osc + noise
# add a clear trend-line break near end
price[80:] -= np.linspace(0, 6, n - 80)
dates = make_dates(n)
line = base - 2.5

fig, ax = plt.subplots()
ax.plot(dates, price, color="#1f77b4", lw=1.5)
ax.plot(dates, line, color="#ff7f0e", lw=2, label="Uptrend line")
# mark "buy zones" where price touches line
touches = []
for i in range(5, n - 5):
    if abs(price[i] - line[i]) < 0.4 and price[i + 3] > price[i]:
        touches.append(i)
seen = set()
unique = []
for t in touches:
    if all(abs(t - u) > 8 for u in unique):
        unique.append(t)
for t in unique[:3]:
    ax.scatter(dates[t], price[t], color="#2ca02c", marker="^", s=120, zorder=6,
               edgecolor="black", linewidth=0.6, label="Buy (rule 1)" if t == unique[0] else "")
# break point
break_i = next((i for i in range(80, n) if price[i] < line[i] - 0.3), None)
if break_i:
    ax.scatter(dates[break_i], price[break_i], color="#d62728", marker="v", s=140, zorder=6,
               edgecolor="black", linewidth=0.6, label="Sell — penetration (rule 2)")
ax.set_title("Trend Line Rules — buy near the line, sell on penetration")
ax.set_ylabel("Price")
ax.legend(loc="upper left", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/06_trend_line_rules.png", bbox_inches="tight")
plt.close()

# ---------- 7. TD LINES (DeMark) — connect two most recent qualifying lows ----------
np.random.seed(4)
n = 90
slope = 0.2
base = 40 + slope * np.arange(n)
osc = 2 * np.sin(np.linspace(0, 5 * np.pi, n))
noise = np.random.normal(0, 0.3, n)
price = base + osc + noise
dates = make_dates(n)

def td_pivot_lows(p, N):
    out = []
    for i in range(N, len(p) - N):
        if p[i] < min(p[i - N:i]) and p[i] < min(p[i + 1:i + N + 1]):
            out.append(i)
    return out

pivots = td_pivot_lows(price, N=4)
# Take last two pivots that satisfy "most recent low and most recent preceding LOWER low"
td_pair = None
if len(pivots) >= 2:
    for i in range(len(pivots) - 1, 0, -1):
        a, b = pivots[i - 1], pivots[i]
        if price[a] < price[b]:  # earlier pivot is lower → valid TD uptrend line
            td_pair = (a, b)
            break
fig, ax = plt.subplots()
ax.plot(dates, price, color="#1f77b4", lw=1.5)
for p in pivots:
    ax.scatter(dates[p], price[p], color="#9e9e9e", s=30, zorder=4)
if td_pair:
    a, b = td_pair
    m = (price[b] - price[a]) / (b - a)
    xs = np.array([a, n - 1])
    ys = price[a] + m * (xs - a)
    ax.plot([dates[int(xs[0])], dates[int(xs[1])]], ys, color="#ff7f0e", lw=2.2,
            label=f"TD uptrend line (N=4)")
    ax.scatter([dates[a], dates[b]], [price[a], price[b]], color="#d62728", s=80, zorder=6,
               edgecolor="black", linewidth=0.6)
ax.set_title("TD Line (DeMark) — objective trend line through 2 qualifying pivots")
ax.set_ylabel("Price")
ax.legend(loc="upper left", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/07_td_line.png", bbox_inches="tight")
plt.close()

# ---------- 8. INTERNAL vs CONVENTIONAL trend line ----------
np.random.seed(9)
n = 100
slope = 0.18
base = 45 + slope * np.arange(n)
osc = 2 * np.sin(np.linspace(0, 4 * np.pi, n))
noise = np.random.normal(0, 0.4, n)
price = base + osc + noise
# create one extreme spike low
price[20] -= 4.5
dates = make_dates(n)
# conventional line: through the extreme low and another lateron
conv_a, conv_b = 20, 70
m_conv = (price[conv_b] - price[conv_a]) / (conv_b - conv_a)
xs_c = np.array([conv_a - 5, n - 1])
ys_c = price[conv_a] + m_conv * (xs_c - conv_a)
# internal line: linear regression through "majority" of relative lows excluding the extreme
from numpy.polynomial import polynomial as P
mask = np.ones(n, dtype=bool); mask[15:25] = False
# choose lows: points below smoothed mean
smoothed = np.convolve(price, np.ones(7)/7, mode="same")
low_idx = np.where((price < smoothed - 0.6) & mask)[0]
coef = np.polyfit(low_idx, price[low_idx], 1)
xs_i = np.array([0, n - 1])
ys_i = coef[0] * xs_i + coef[1]

fig, ax = plt.subplots()
ax.plot(dates, price, color="#1f77b4", lw=1.5)
ax.plot([dates[int(xs_c[0])], dates[int(xs_c[1])]], ys_c, color="#9467bd", lw=2, ls="--",
        label="Conventional (extreme low)")
ax.plot([dates[int(xs_i[0])], dates[int(xs_i[1])]], ys_i, color="#ff7f0e", lw=2.2,
        label="Internal (best fit through majority)")
ax.scatter(dates[20], price[20], color="#9467bd", s=80, zorder=6, edgecolor="black",
           linewidth=0.6, label="Extreme low")
ax.set_title("Internal vs. Conventional Trend Line")
ax.set_ylabel("Price")
ax.legend(loc="upper left", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/08_internal_trend_line.png", bbox_inches="tight")
plt.close()

# ---------- 9. MOVING AVERAGE — trending market ----------
np.random.seed(6)
n = 200
trend = np.concatenate([
    np.linspace(50, 70, 100),
    np.linspace(70, 55, 100),
])
noise = np.cumsum(np.random.normal(0, 0.4, n))
price = trend + noise
ma40 = np.convolve(price, np.ones(40)/40, mode="valid")
ma40_x = np.arange(39, n)
dates = make_dates(n)

fig, ax = plt.subplots()
ax.plot(dates, price, color="#9e9e9e", lw=1.0, label="Daily close")
ax.plot([dates[i] for i in ma40_x], ma40, color="#ff7f0e", lw=2.2, label="40-day SMA")
# buy/sell signals: 10-tick reversal in MA
signals = []
direction = 0
ext = ma40[0]
for i in range(1, len(ma40)):
    if direction <= 0 and ma40[i] - ext >= 1.0:  # using "1.0" as threshold
        signals.append(("buy", ma40_x[i]))
        direction = 1; ext = ma40[i]
    elif direction >= 0 and ext - ma40[i] >= 1.0:
        signals.append(("sell", ma40_x[i]))
        direction = -1; ext = ma40[i]
    else:
        if direction >= 0:
            ext = max(ext, ma40[i])
        if direction <= 0:
            ext = min(ext, ma40[i])
seen_b = seen_s = False
for kind, idx in signals[:6]:
    if kind == "buy":
        ax.scatter(dates[idx], price[idx], color="#2ca02c", marker="^", s=120, zorder=6,
                   edgecolor="black", linewidth=0.6, label=None if seen_b else "Buy")
        seen_b = True
    else:
        ax.scatter(dates[idx], price[idx], color="#d62728", marker="v", s=120, zorder=6,
                   edgecolor="black", linewidth=0.6, label=None if seen_s else "Sell")
        seen_s = True
ax.set_title("Simple Moving Average (40-day) — trending market")
ax.set_ylabel("Price")
ax.legend(loc="upper left", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/09_moving_average_trending.png", bbox_inches="tight")
plt.close()

# ---------- 10. MOVING AVERAGE — sideways/whipsaw ----------
np.random.seed(13)
n = 200
price = 60 + 3 * np.sin(np.linspace(0, 8 * np.pi, n)) + np.cumsum(np.random.normal(0, 0.3, n))
ma40 = np.convolve(price, np.ones(40)/40, mode="valid")
ma40_x = np.arange(39, n)
dates = make_dates(n)

signals = []
direction = 0
ext = ma40[0]
for i in range(1, len(ma40)):
    if direction <= 0 and ma40[i] - ext >= 0.6:
        signals.append(("buy", ma40_x[i])); direction = 1; ext = ma40[i]
    elif direction >= 0 and ext - ma40[i] >= 0.6:
        signals.append(("sell", ma40_x[i])); direction = -1; ext = ma40[i]
    else:
        if direction >= 0: ext = max(ext, ma40[i])
        if direction <= 0: ext = min(ext, ma40[i])

fig, ax = plt.subplots()
ax.plot(dates, price, color="#9e9e9e", lw=1.0, label="Daily close")
ax.plot([dates[i] for i in ma40_x], ma40, color="#ff7f0e", lw=2.2, label="40-day SMA")
seen_b = seen_s = False
for kind, idx in signals:
    if kind == "buy":
        ax.scatter(dates[idx], price[idx], color="#2ca02c", marker="^", s=90, zorder=6,
                   edgecolor="black", linewidth=0.6, label=None if seen_b else "Buy (whipsaw)")
        seen_b = True
    else:
        ax.scatter(dates[idx], price[idx], color="#d62728", marker="v", s=90, zorder=6,
                   edgecolor="black", linewidth=0.6, label=None if seen_s else "Sell (whipsaw)")
        seen_s = True
ax.set_title("Simple Moving Average (40-day) — choppy/sideways market (whipsaws)")
ax.set_ylabel("Price")
ax.legend(loc="upper left", frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
plt.tight_layout()
plt.savefig(f"{OUT}/10_moving_average_sideways.png", bbox_inches="tight")
plt.close()

print("All charts generated.")
