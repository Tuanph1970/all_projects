# Hướng dẫn sử dụng nhanh / Quick Start Guide

**Phiên bản / Version 0.9** · Cập nhật / Updated 2026-11-03

> **Tiếng Việt trước, English below.** Mỗi mục có cả hai ngôn ngữ.
> Each section appears in Vietnamese first, then English.
>
> Tài liệu này là **bản hướng dẫn nhanh cho toàn bộ ứng dụng**. Hai tài liệu
> chuyên sâu đã có vẫn giữ nguyên giá trị:
> This is the **whole-application quick guide**. Two existing deep-dive guides
> remain valid:
> - `USER_GUIDE_portfolio_journal_ai_insights.md` — Danh mục, Nhật ký, AI
> - `USER_GUIDE_chart_decomp_and_decision_tools.md` — Phân rã biểu đồ, Decision Helper

---

## 0. Mở ứng dụng / Opening the app

**VI.** Truy cập `http://localhost:3004/stock-app/` (hoặc địa chỉ nội bộ mà
người quản trị cung cấp). Đăng nhập bằng email và mật khẩu của bạn. Đổi ngôn
ngữ Việt/Anh bằng nút ở thanh trên cùng — mọi màn hình đều có cả hai.

**EN.** Open `http://localhost:3004/stock-app/` (or the LAN address your
administrator gave you) and sign in with your email and password. The
language switch is in the top bar; every screen exists in both languages.

---

## 1. Bắt đầu từ đâu / Where to start

**VI.** Thứ tự dưới đây là con đường ngắn nhất để ứng dụng trở nên hữu ích cho
bạn. Ba bước đầu mất khoảng năm phút và quyết định chất lượng của mọi thứ sau đó.

1. **Danh mục → Danh sách theo dõi** — thêm các mã bạn quan tâm. *Việc này quan
   trọng hơn vẻ ngoài của nó:* danh sách theo dõi là nguồn cho ô chọn mã ở
   trang Phân tích đồ thị, và cũng là danh sách mà hệ thống đi lấy tin tức
   doanh nghiệp. Mã không có trong đây thì không có tin.
2. **Danh mục → Cổ phiếu nắm giữ** — nhập những mã bạn **đã mua**. Đây là hai
   khái niệm khác nhau: *nắm giữ* là đã mua, *theo dõi* là chỉ quan sát.
3. **Danh mục → Cảnh báo giá** — đặt ít nhất một cảnh báo để nhận thông báo.

**EN.** The order below is the shortest path to the app being useful. The first
three steps take about five minutes and determine the quality of everything else.

1. **Portfolio → Watchlist** — add the symbols you follow. *This matters more
   than it looks:* the watchlist feeds the symbol picker on Chart analyst, and
   it is also the list the system fetches company news for. A symbol that is
   not here gets no news.
2. **Portfolio → Holdings** — enter what you have **actually bought**. These
   are two different ideas: *holdings* are bought, *watchlist* is watched only.
3. **Portfolio → Price alerts** — set at least one alert so notifications start.

---

## 2. Mười hai nhóm menu / The twelve menu groups

> **Tên tiếng Việt dưới đây là đúng nhãn hiển thị trong ứng dụng.**
> The Vietnamese names below are the exact labels shown in the app.

### 2.1 Bảng giá / Price board

**VI.** Bảng giá trực tiếp. Trong giờ giao dịch, một dòng cũ hơn 60 giây sẽ
được lấy lại khi bạn mở trang.

**EN.** The live price board. During trading hours a row older than 60 seconds
is refetched when you open the page.

### 2.2 Cổ phiếu / Stocks

**VI.** **Lọc cổ phiếu** (theo điều kiện bạn đặt), **Theo ngành** (sức mạnh
từng ngành), **Danh sách CP** (tra cứu toàn sàn).

**EN.** **Screener** (your own conditions), **By industry** (sector strength),
**Stock list** (browse the whole board).

### 2.3 Biến động thị trường / Market movers

**VI.** **Tăng mạnh nhất**, **Giảm mạnh nhất**, **Giao dịch nhiều nhất** —
dòng tiền đang đi đâu hôm nay.

**EN.** **Top gainers**, **Top losers**, **Most active** — where today's money
is going.

### 2.4 Dự đoán / Predictions

**VI.** **Mô hình** và **Giải pháp** để huấn luyện dự báo giá cho một mã,
**Chỉ báo** để chọn biến đầu vào, **Backtest** để kiểm định trên quá khứ.

**Hai điều nên biết trước khi tin một con số:** (1) chỉ báo kỹ thuật **không
bao giờ** được dùng làm biến tương lai — hệ thống chặn việc đó, vì ngày mai
chưa có RSI của ngày mai; (2) chế độ cắt lỗ mặc định của Backtest là
**BASING_POINT** (quy tắc Edwards & Magee), được chọn sau khi đo trên 61 mã
chưa từng dùng để tinh chỉnh.

**EN.** **Models** and **Solutions** train a price forecast for a symbol,
**Indicators** chooses the inputs, **Backtest** re-runs it over history.

**Two things to know before trusting a number:** (1) technical indicators are
**never** offered as future covariates — the system blocks it, because
tomorrow's RSI does not exist today; (2) the Backtest trailing-stop default is
**BASING_POINT** (the Edwards & Magee rule), adopted after measuring 61 symbols
never used for tuning.

### 2.5 Mô phỏng giao dịch với AI / AI trading simulation

**VI.** Môi trường mô phỏng giao dịch.

**EN.** The trading-simulation environment.

### 2.6 Trợ lý AI / AI assistant

**VI.** **Trò chuyện AI** để hỏi tự do về dữ liệu trong ứng dụng; **Hỏi đáp
kiến thức** trả lời dựa trên tài liệu đã nạp.

**EN.** **AI chat** for free-form questions about your data; **Knowledge QA**
answers from an ingested document base.

### 2.7 Phân tích / Analysis — *có tính năng mới trong 0.9 / contains the 0.9 addition*

**VI.** Bảy trang. **Phân tích đồ thị** là trang mới của 0.9:

- **Phân tích đồ thị (MỚI)** — chọn một mã **đang theo dõi**, chọn khoảng ngày
  nếu muốn, bấm **Phân tích**. Ứng dụng viết ra bằng lời những gì đồ thị đang
  nói: xu hướng và trạng thái các đường MA, hỗ trợ/kháng cự kèm lịch sử phá vỡ
  và đổi vai, RSI/MACD/Bollinger/khối lượng, mẫu nến đảo chiều, phân kỳ RSI,
  kênh giá, mẫu hình nhiều tuần, và một kế hoạch cụ thể (điểm vào, cắt lỗ,
  chốt lời, khối lượng).

  **Ba điều làm nên sự khác biệt của trang này:**
  - Khi chọn **ngày kết thúc**, phân tích chỉ dùng dữ liệu **đến ngày đó** — nó
    không thể "nhìn thấy tương lai". Rất hữu ích để tự kiểm tra lại một quyết
    định cũ của mình.
  - Mẫu hình giá chỉ được coi là **tín hiệu** khi vượt phân vị 95 so với đồ thị
    ngẫu nhiên. Nếu không, trang nói thẳng là "không mạnh hơn mức tình cờ" —
    đo trên bốn mã đang theo dõi, ba mã nhận đúng câu đó.
  - Nếu dữ liệu giá có sự kiện doanh nghiệp chưa điều chỉnh, trang **từ chối
    đưa kế hoạch** thay vì đưa một kế hoạch dựa trên số liệu sai.

- **Phân tích kỹ thuật** — đồ thị nến đầy đủ kèm chỉ báo.
- **Phân tích cơ bản** — báo cáo tài chính, chỉ số, định giá.
- **Phân tích AI** — tổng hợp điểm số, rủi ro, mẫu hình.
- **Phân rã biểu đồ**, **Dự báo & Backtest**, **Phản ứng sự kiện** — công cụ
  nâng cao; xem tài liệu chuyên sâu.

**EN.** Seven pages. **Chart analyst** is the 0.9 addition:

- **Chart analyst (NEW)** — pick a **watched** symbol, optionally set a date
  range, press **Analysis**. The app says in words what the chart is saying:
  trend and MA stack, support/resistance with break and role-reversal history,
  RSI/MACD/Bollinger/volume, reversal candles, RSI divergence, the price
  channel, multi-week formations, and a concrete plan (entry, stop, target,
  position size).

  **Three things make this page different:**
  - Set an **end date** and the analysis uses only bars up to that date — it
    cannot see the future. Useful for checking your own past decisions.
  - A chart formation counts as a **signal** only if it beats the 95th
    percentile of what the same detector finds in random-walk charts.
    Otherwise the page says plainly it is "no stronger than chance" — measured
    across four watched symbols, three got exactly that answer.
  - If the price history holds an unadjusted corporate action, the page
    **refuses to offer a plan** rather than building one on bad numbers.

- **Technical analysis** — the full candlestick chart with indicators.
- **Fundamental analysis** — statements, ratios, valuation.
- **AI analysis** — a combined score, risk read and pattern summary.
- **Chart Decomposition**, **Forecast & Backtest**, **Event Reaction** —
  advanced tools; see the deep-dive guide.

### 2.8 Danh mục / Portfolio

**VI.**
- **Cổ phiếu nắm giữ** — số lượng, giá vốn, lãi/lỗ.
- **Hiệu suất** — giá trị tài khoản theo thời gian.
- **Cảnh báo giá** — ba loại: **trên** một mức giá, **dưới** một mức giá, và
  **khối lượng bất thường (MỚI trong 0.9)**.

  *Cảnh báo khối lượng* đo khối lượng hôm nay so với **trung vị** khối lượng
  của chính mã đó — không phải một con số cổ phiếu tuyệt đối, vì "khối lượng
  lớn" với POW khác với VIC. Mặc định là **3,0 lần**: đo trên 42.674 quan sát
  của 32 mã, mức này xuất hiện ở 4,55% số phiên, còn 1,5 lần thì tới 23,95% —
  đủ nhiều để bạn bắt đầu bỏ qua thông báo.

  Cảnh báo khối lượng **lặp lại mỗi ngày giao dịch một lần**, khác với cảnh báo
  giá chỉ báo một lần. Lý do: "vượt 25.000" là một ngưỡng bị vượt một lần, còn
  khối lượng bất thường thì tái diễn.

  Thông báo nói rõ: khối lượng bất thường thể hiện **sự chú ý, không phải chiều
  hướng** — nó không cho biết tin phía sau là tốt hay xấu.
- **Danh sách theo dõi** — nguồn cho tin tức doanh nghiệp và cho ô chọn mã ở
  trang Phân tích đồ thị.

**EN.**
- **Holdings** — quantity, cost basis, profit and loss.
- **Performance** — your account value over time.
- **Price alerts** — three kinds: **above** a price, **below** a price, and
  **unusual volume (NEW in 0.9)**.

  *Volume alerts* measure today's volume against that symbol's own **median** —
  not an absolute share count, because "high volume" for POW is not high volume
  for VIC. The default is **3.0×**: measured over 42,674 readings on 32 symbols,
  that fires on 4.55% of sessions, where 1.5× fires on 23.95% — often enough
  that you would start ignoring it.

  Volume alerts **re-fire once per trading day**, unlike price alerts which fire
  once. The reason: "above 25,000" is a threshold crossed once, but unusual
  volume recurs.

  The notification says so explicitly: unusual volume means **attention, not
  direction** — it does not tell you whether the news behind it is good or bad.
- **Watchlist** — the source for company news and for the Chart analyst picker.

### 2.9 Tin tức / News

**VI.** **Tin TCB** — dán email nghiên cứu hằng ngày của TCBS vào đây; hệ thống
bóc tách VN-Index, thanh khoản, khối ngoại, các đường MA và các khuyến nghị
mua/bán, rồi lưu lại để đối chiếu hiệu quả về sau.

**EN.** **TCB News** — paste the TCBS daily research email; the system extracts
the VN-Index, liquidity, foreign flow, moving averages and buy/sell calls, then
stores them so their record can be scored later.

### 2.10 Nhật ký giao dịch / Trade journal

**VI.** Bảy trang: **Tổng quan**, **Bảng thống kê**, **Tài khoản**, **Sổ giao
dịch**, **Nhật ký**, **Kế hoạch hàng ngày**, **Tổng kết tuần**. Đây là nơi ghi
lại *vì sao* bạn vào lệnh, không chỉ *đã vào lệnh gì* — phần ít hấp dẫn nhất
nhưng có giá trị lâu dài nhất của ứng dụng.

**EN.** Seven pages: **Overview**, **Dashboard**, **Accounts**, **Trade log**,
**Diary**, **Daily planning**, **Weekly review**. This is where you record *why*
you entered a trade, not just *what* — the least exciting part of the app and
the one with the longest-lasting value.

### 2.11 Công cụ hỗ trợ quyết định / Decision Helper

**VI.** Mười hai trang cho một quy trình ra quyết định có kỷ luật: **Tổng
quan**, **Màn hình quyết định**, **Bảng quyết định Watchlist**, **Phòng thử
nghiệm Backtest**, **Kỷ luật giao dịch**, **Chạy định kỳ**, **Quét thị
trường**, **Bản đồ nhiệt Watchlist**, **Phân tích hiệu suất**, **Vị thế đang
mở**, **Kết quả giao dịch**, **Bảng rủi ro**.
Chi tiết: `USER_GUIDE_chart_decomp_and_decision_tools.md`.

**EN.** Twelve screens for a disciplined decision process: **General View**,
**Decision Console**, **Watchlist Board**, **Backtest Studio**, **Discipline**,
**Scheduled Runs**, **Scanner**, **Heat Map**, **Analytics**, **Open
Positions**, **Trade Outcomes**, **Risk Dashboard**.
Details: `USER_GUIDE_chart_decomp_and_decision_tools.md`.

### 2.12 Góp ý & ý tưởng / Ideas & feedback — *MỚI trong 0.9 / NEW in 0.9*

**VI.** Nói cho chúng tôi biết nên làm gì tiếp theo, hoặc điều gì đang gây khó
cho bạn. Chọn loại góp ý (ý tưởng / có chỗ sai / gây khó hiểu / dùng tốt /
khác), viết nội dung, gửi. **Trang bạn đang xem được gửi kèm tự động**, nên bạn
không cần giải thích mình đang ở đâu. Bạn xem lại được các góp ý đã gửi và
trạng thái xử lý.

Loại góp ý có giá trị nhất — và ít gặp nhất — là **"gây khó hiểu"**: tính năng
vẫn chạy, nhưng bạn không biết phải dùng thế nào.

**EN.** Tell us what to build next, or what is getting in your way. Pick a
category (idea / something is wrong / this confused me / this works well /
other), write it, send. **The page you are on is attached automatically**, so
you never have to explain where you were. You can see what you have sent and
how it is being handled.

The most valuable category — and the rarest — is **"this confused me"**: the
feature works, but you could not tell how.

---

## 3. Những điều ứng dụng sẽ KHÔNG làm / What the app will NOT do

**VI.** Đây là thiết kế có chủ ý, không phải thiếu sót:

- **Không hứa một con số khi dữ liệu không đỡ được nó.** Nếu không đủ điểm đảo
  chiều để vẽ kênh giá, trang nói là không đủ, thay vì kẻ một đường qua một
  điểm.
- **Không gọi mẫu hình là tín hiệu nếu nó không mạnh hơn ngẫu nhiên.** Một mẫu
  Vai–Đầu–Vai ở phân vị 6 so với đồ thị tung đồng xu sẽ được nêu ra kèm đúng
  câu đó.
- **Không đưa kế hoạch khi tỷ lệ Lãi/Rủi ro dưới 1:1**, hoặc khi dữ liệu có sự
  kiện doanh nghiệp chưa điều chỉnh.
- **Không đề nghị dồn quá 20% tài khoản vào một mã**, dù quy tắc rủi ro thuần
  toán học có cho phép nhiều hơn khi điểm cắt lỗ rất gần.
- **Không dùng mô hình ngôn ngữ để viết phần phân tích đồ thị.** Toàn bộ câu
  chữ sinh ra từ các con số đã đo được. Một mô hình ngôn ngữ sẽ viết hay hơn,
  và đó chính là rủi ro.

**EN.** These are deliberate, not gaps:

- **No number is promised when the data cannot support it.** Too few swing
  points to draw a channel, and the page says so rather than drawing a line
  through one pivot.
- **A formation is not called a signal unless it beats chance.** A
  head-and-shoulders at the 6th percentile of what coin-flip charts produce is
  reported with exactly that caveat attached.
- **No plan when reward-to-risk is under 1:1**, or when the window holds an
  unadjusted corporate action.
- **No suggestion to put more than 20% of the account in one position**, even
  when pure risk arithmetic would allow more because the stop is tight.
- **No language model writes the chart analysis.** Every sentence comes from
  measured numbers. A language model would write it better, and that is
  precisely the risk.

---

## 4. Khắc phục sự cố / Troubleshooting

| Hiện tượng / Symptom | Nguyên nhân & cách xử lý / Cause and fix |
|---|---|
| Ô chọn mã ở Phân tích đồ thị trống / Chart analyst picker is empty | Bạn chưa theo dõi mã nào. Thêm ở Danh mục → Danh sách theo dõi. / You are not watching any symbol yet; add one on Portfolio → Watchlist. |
| Không nhận được thông báo / No notifications arriving | Cần cho phép thông báo trên trình duyệt, và cần có ít nhất một cảnh báo đang bật. / The browser must have granted notification permission and at least one alert must be active. |
| Mã của tôi không có tin tức / My symbol has no news | Tin tức chỉ lấy cho các mã trong danh sách theo dõi và danh mục. / News is fetched only for watched and held symbols. |
| Cường độ tin bằng 0 dù có nhiều bài / News intensity reads 0 although many articles exist | Nguồn tin không cung cấp ngày công bố cho các bài nạp hàng loạt, nên chúng bị loại khỏi chuỗi thời gian và được báo riêng. / The feed supplies no publication date for bulk-loaded items, so they are excluded from the time series and reported separately. |
| Màn hình không đổi sau khi cập nhật / Screen unchanged after an update | Tải lại trang bằng Ctrl+Shift+R. / Hard-reload with Ctrl+Shift+R. |

---

## 5. Gửi góp ý / Sending feedback

**VI.** Dùng **Góp ý & ý tưởng** trong menu. Góp ý cụ thể có giá trị hơn góp ý
lịch sự: một ví dụ, hoặc các bước bạn đã làm, hữu ích hơn một bản tóm tắt
chung chung.

**EN.** Use **Ideas & feedback** in the menu. Concrete beats polite: an example,
or the steps you took, is worth more than a careful summary.
