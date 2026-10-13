# Hướng dẫn sử dụng / User Guide
## Phân rã biểu đồ & Công cụ hỗ trợ quyết định
## Chart Decomposition & Decision Tools

> Tài liệu song ngữ (Tiếng Việt / English). Mỗi chức năng được trình bày theo 2 phần:
> **Lợi ích (Mục tiêu)** — bạn đạt được gì, và **Cách thực hiện** — các bước thao tác.
>
> Bilingual document (Vietnamese / English). Each function is described in 2 parts:
> **Benefit (Goal)** — what you gain, and **How to achieve it** — the steps to take.

---

## Mục lục / Table of Contents

**Phần 1 — Phân rã biểu đồ / Chart Decomposition**
- [1.1 Phân rã tín hiệu / Signal Decomposition](#11--phân-rã-tín-hiệu--signal-decomposition)
- [1.2 Phân tích thời gian–tần số / Time-Frequency Analysis](#12--phân-tích-thời-giantần-số--time-frequency-analysis)
- [1.3 Hurst & Đồng pha / Hurst & Coherence](#13--hurst--đồng-pha--hurst--coherence)
- [1.4 Dự báo biến động / Volatility Forecast](#14--dự-báo-biến-động--volatility-forecast)
- [1.5 Nhận diện mẫu hình / Pattern Detection](#15--nhận-diện-mẫu-hình--pattern-detection)

**Phần 2 — Công cụ hỗ trợ quyết định / Decision Tools**
- [2.1 Tổng quan / General View](#21--tổng-quan--general-view)
- [2.2 Màn hình quyết định / Decision Console](#22--màn-hình-quyết-định--decision-console)
  - [2.2.1 — Xác nhận bằng khối lượng / Volume validation](#221--xác-nhận-bằng-khối-lượng--volume-validation-edwards--magee)
- [2.3 Bảng quyết định Watchlist / Watchlist Board](#23--bảng-quyết-định-watchlist--watchlist-board)
- [2.4 Phòng thử nghiệm Backtest / Backtest Studio](#24--phòng-thử-nghiệm-backtest--backtest-studio)
- [2.5 Kỷ luật giao dịch / Discipline Dashboard](#25--kỷ-luật-giao-dịch--discipline-dashboard)
- [2.6 Chạy định kỳ / Scheduled Runs](#26--chạy-định-kỳ--scheduled-runs)
- [2.7 Quét thị trường / Scanner](#27--quét-thị-trường--scanner)
- [2.8 Bản đồ nhiệt Watchlist / Heat Map](#28--bản-đồ-nhiệt-watchlist--heat-map)
- [2.9 Phân tích hiệu suất / Analytics](#29--phân-tích-hiệu-suất--analytics)
- [2.10 Vị thế đang mở / Open Positions](#210--vị-thế-đang-mở--open-positions)
- [2.11 Kết quả giao dịch / Trade Outcomes](#211--kết-quả-giao-dịch--trade-outcomes)
- [2.12 Bảng rủi ro / Risk Dashboard](#212--bảng-rủi-ro--risk-dashboard)

---

# PHẦN 1 — PHÂN RÃ BIỂU ĐỒ (Menu: Phân tích ▸ Phân rã biểu đồ)
# PART 1 — CHART DECOMPOSITION (Menu: Analysis ▸ Chart Decomposition)

**Trang:** *Phân rã & Phân tích đa tỷ lệ* — **Page:** *Decomposition & Multi-Scale Analysis*

### Cách bắt đầu (dùng chung cho mọi tab) / Getting started (common to all tabs)

**VI:**
1. Nhập **mã cổ phiếu** (ví dụ VCB, HPG, TCB) hoặc dùng dữ liệu mẫu (demo).
2. Chọn **khoảng thời gian** (1 năm, 2 năm, 3 năm, 5 năm).
3. Chọn **tab phân tích** bên dưới và bấm nút chạy tương ứng.

**EN:**
1. Enter a **ticker** (e.g. VCB, HPG, TCB) or use demo data.
2. Choose a **period** (1Y, 2Y, 3Y, 5Y).
3. Pick an **analysis tab** below and click its run button.

Trang có 5 tab / The page has 5 tabs: **Phân rã tín hiệu**, **Phân tích thời gian–tần số**, **Hurst & Đồng pha**, **Dự báo biến động**, **Nhận diện mẫu hình**.

---

## 1.1 — Phân rã tín hiệu / Signal Decomposition

**🎯 Lợi ích / Benefit**

- **VI:** Tách giá cổ phiếu (vốn nhiễu loạn) thành **xu hướng nền** (chuyển động chậm) và các **thành phần dao động** ở từng tần số. Nhờ đó bạn nhìn thấy "khung xương" thật sự của giá, loại bỏ nhiễu, để phán đoán xu hướng và chu kỳ rõ ràng hơn.
- **EN:** Break a noisy price into an **underlying trend** (slow component) plus **oscillation components** at each frequency. You see the true "skeleton" of the price with noise removed, making the trend and cycles far easier to read.

**🛠️ Cách thực hiện / How to achieve it**

**VI:**
1. Chọn **phương pháp phân rã**:
   - **MODWT (Wavelet)** — mặc định, ổn định nhất, khuyến nghị dùng thường ngày.
   - **EMD** — thích nghi theo dữ liệu, hợp với chuỗi không dừng.
   - **EEMD** — EMD có trung bình hóa nhiễu, sạch hơn nhưng chậm hơn.
   - **VMD** — tách các tần số dao động rất gọn.
2. Tuỳ chọn nâng cao: với MODWT chọn họ wavelet (mặc định `sym8`) và số cấp J (mặc định 6); với VMD chọn số mode K (4–6) và hệ số α (mặc định 1500).
3. Bấm **"Run Decomposition"**.
4. Đọc biểu đồ: đường gốc, đường xu hướng (approximation/residue), các dải dao động (details/IMF/modes). Bấm vào chú giải để bật/tắt từng đường, cuộn để phóng to, kéo để dịch chuyển thời gian.
5. Kiểm tra **sai số tái tạo (reconstruction error)** — gần 0 nghĩa là phân rã tốt.

**EN:**
1. Choose a **decomposition method**:
   - **MODWT (Wavelet)** — default, most stable, recommended for daily use.
   - **EMD** — data-adaptive, good for non-stationary series.
   - **EEMD** — noise-averaged EMD, cleaner but slower.
   - **VMD** — separates oscillation frequencies very cleanly.
2. Advanced options: for MODWT pick the wavelet family (default `sym8`) and levels J (default 6); for VMD set number of modes K (4–6) and α (default 1500).
3. Click **"Run Decomposition"**.
4. Read the chart: the original line, the trend line (approximation/residue), and the oscillation bands (details/IMFs/modes). Click the legend to toggle a series, scroll to zoom, drag to pan in time.
5. Check the **reconstruction error** — near 0 means a good decomposition.

---

## 1.2 — Phân tích thời gian–tần số / Time-Frequency Analysis

**🎯 Lợi ích / Benefit**

- **VI:** Cho biết **khi nào** từng loại dao động (nhanh/chậm) mạnh nhất. Bản đồ nhiệt giúp bạn nhận ra giai đoạn thị trường "giật cục" (nhiễu) so với giai đoạn đang có xu hướng, và tần số nào đang chi phối tại từng thời điểm.
- **EN:** Reveals **when** each type of oscillation (fast/slow) is strongest. The heatmap shows you choppy (noisy) phases versus trending phases, and which frequency dominates at any given date.

**🛠️ Cách thực hiện / How to achieve it**

**VI:**
1. Chọn phương pháp: **CWT Scalogram** (wavelet liên tục, khuyến nghị) hoặc **Hilbert-Huang Spectrum** (từ EMD).
2. Với CWT chọn số scale (32 / 64 / 128 — nhiều hơn thì mịn hơn nhưng chậm hơn).
3. Bấm **"Run Compute"**.
4. Đọc bản đồ nhiệt: màu càng sáng (vàng) = tần số đó càng mạnh. Trục dọc là chu kỳ (trên = chu kỳ ngắn/nhiễu, dưới = chu kỳ dài/xu hướng).
5. **Lưu ý vùng xám ở mép (Cone of Influence)** — dữ liệu ở đó không đáng tin do hiệu ứng biên; hãy bỏ qua.

**EN:**
1. Choose a method: **CWT Scalogram** (continuous wavelet, recommended) or **Hilbert-Huang Spectrum** (from EMD).
2. For CWT pick the number of scales (32 / 64 / 128 — more is finer but slower).
3. Click **"Run Compute"**.
4. Read the heatmap: brighter (yellow) = that frequency is stronger. The vertical axis is period (top = short cycles/noise, bottom = long cycles/trend).
5. **Note the grey edges (Cone of Influence)** — data there is unreliable due to boundary effects; ignore it.

---

## 1.3 — Hurst & Đồng pha / Hurst & Coherence

**🎯 Lợi ích / Benefit**

- **VI:** Hai công cụ trong một tab. **Hurst** cho biết cổ phiếu đang **theo xu hướng** (có quán tính) hay **hồi quy về trung bình** — giúp chọn chiến lược phù hợp. **Đồng pha (Coherence)** đo mức độ **hai cổ phiếu cùng biến động** ở từng tần số — hữu ích cho cặp hedge/tương quan.
- **EN:** Two tools in one tab. **Hurst** tells you whether a stock is **trending** (has momentum) or **mean-reverting** — helping you pick the right strategy. **Coherence** measures how **two stocks move together** at each frequency — useful for hedge pairs and correlation.

**🛠️ Cách thực hiện / How to achieve it**

**VI — Hurst:**
1. Bấm **"Estimate Hurst"**.
2. Đọc giá trị H: **H > 0.5** = theo xu hướng (động lượng); **H ≈ 0.5** = bước ngẫu nhiên (không dự đoán được); **H < 0.5** = hồi quy về trung bình (hợp chiến lược đảo chiều). Màu đỏ = xu hướng mạnh, xanh lá = ngẫu nhiên, xanh dương = hồi quy.
3. Xem biểu đồ phương sai theo scale: đường thẳng = hành vi nhất quán; chỗ gãy = động lực thay đổi theo thang.

**VI — Đồng pha:**
1. Nhập **mã cổ phiếu thứ hai** (ví dụ TCB) và bấm **"Load"**.
2. Bấm **"Compute Coherence"**.
3. Đọc bản đồ nhiệt đồng pha: màu sáng = hai mã cùng dao động ở tần số/thời điểm đó; màu mờ = chúng độc lập.

**EN — Hurst:**
1. Click **"Estimate Hurst"**.
2. Read the value H: **H > 0.5** = trending (momentum); **H ≈ 0.5** = random walk (not predictable); **H < 0.5** = mean-reverting (reversal strategies may work). Red = strong trend, green = random, blue = mean-reverting.
3. View the variance-by-scale chart: a straight line = consistent behaviour; kinks = scale-dependent dynamics.

**EN — Coherence:**
1. Enter a **second ticker** (e.g. TCB) and click **"Load"**.
2. Click **"Compute Coherence"**.
3. Read the coherence heatmap: bright = the two stocks move together at that frequency/time; dim = they move independently.

> ⚠️ Hurst luôn được ước lượng trên **suất sinh lời (returns)**, không phải trên giá. / Hurst is always estimated on **returns**, never on raw price.

---

## 1.4 — Dự báo biến động / Volatility Forecast

**🎯 Lợi ích / Benefit**

- **VI:** Dự báo **mức biến động (volatility) 1 ngày tới**, giúp bạn ước lượng rủi ro và canh kích thước lệnh. So sánh mô hình chuẩn **HAR** với mô hình nâng cao **VMD-HAR** để biết phương pháp nào chính xác hơn.
- **EN:** Forecasts **next-day volatility**, helping you gauge risk and size positions. Compares the baseline **HAR** model with the enhanced **VMD-HAR** model to see which is more accurate.

**🛠️ Cách thực hiện / How to achieve it**

**VI:**
1. Chọn mô hình: **HAR** (cần ≥ 300 điểm dữ liệu) hoặc **VMD-HAR** (cần ≥ 5 năm dữ liệu ngày, ~1.253 điểm).
2. Bấm **"Run Forecast"**.
3. Đọc bảng chỉ số: **RMSE / MAE** (sai số — càng thấp càng tốt), **R²** (mức giải thích — > 0.3 là tốt), **QLIKE** (càng thấp càng tốt).
4. Xem biểu đồ: đường liền = biến động thực tế, đường nét đứt = dự báo, chỉ hiển thị giai đoạn **ngoài mẫu (out-of-sample)** để phản ánh hiệu năng thực tế.
5. VMD-HAR chỉ "tốt hơn" khi vượt HAR cả về RMSE/QLIKE và có ý nghĩa thống kê (kiểm định Diebold-Mariano |DM| > 1.96).

**EN:**
1. Choose a model: **HAR** (needs ≥ 300 data points) or **VMD-HAR** (needs ≥ 5 years of daily data, ~1,253 points).
2. Click **"Run Forecast"**.
3. Read the metrics: **RMSE / MAE** (error — lower is better), **R²** (explained variance — > 0.3 is good), **QLIKE** (lower is better).
4. View the chart: solid line = actual volatility, dashed line = forecast, shown only for the **out-of-sample** period to reflect realistic performance.
5. VMD-HAR only "wins" if it beats HAR on RMSE/QLIKE **and** is statistically significant (Diebold-Mariano test |DM| > 1.96).

---

## 1.5 — Nhận diện mẫu hình / Pattern Detection

**🎯 Lợi ích / Benefit**

- **VI:** Tự động phát hiện các **mẫu hình kỹ thuật** (Vai–Đầu–Vai, Hai đỉnh/đáy, Tam giác…) và vẽ trực tiếp lên biểu đồ. Có kiểm tra **ý nghĩa thống kê (null-FPR)** để biết mẫu hình là thật hay ngẫu nhiên. Chế độ **đa tỷ lệ (nested)** còn cho thấy các mẫu hình lồng nhau giữa nhiều mức độ làm mịn.
- **EN:** Automatically detects **chart patterns** (Head & Shoulders, Double Top/Bottom, Triangles…) and draws them on the chart. Includes a **statistical-significance check (null-FPR)** so you know whether a pattern is real or just noise. The **multi-scale (nested)** mode also reveals patterns nested within patterns across denoising levels.

**🛠️ Cách thực hiện / How to achieve it**

**VI — Chế độ một tỷ lệ (mặc định):**
1. Tắt ô **"Multi-scale (nested)"**.
2. Đặt **k_drop** (0–4): mức khử nhiễu (cao hơn = mượt hơn). Đặt **threshold** (0.01–0.5): độ nhạy đỉnh/đáy (thấp hơn = nhiều điểm xoay hơn).
3. (Tuỳ chọn) tick **"Null FPR"** để tính ý nghĩa thống kê (chậm hơn).
4. Bấm **"Run Detection"**.
5. Đọc 3 khung: *Giá gốc vs đã khử nhiễu*, *Khung xương swing* (chấm đỏ = đỉnh, xanh = đáy), *Mẫu hình phát hiện* (khung màu trên biểu đồ). Bảng báo cáo cho biết tên mẫu, vùng thời gian, **điểm tin cậy (0–100%)**, đã xác nhận (✓) hay còn ở mép ("Edge?"), và % ý nghĩa thống kê.

**VI — Chế độ đa tỷ lệ (nested):**
1. Bật ô **"Multi-scale (nested)"** và chọn các tỷ lệ (k_drop = 1,2,3,4).
2. Đặt threshold rồi bấm **"Run Detection"**.
3. Đọc: *Khử nhiễu theo tỷ lệ*, *Mẫu hình lồng nhau* (cùng màu = quan hệ cha–con; viền nét đứt = chưa xác nhận), và bảng báo cáo có cột **Tỷ lệ**, **Lồng trong**, **Quan hệ** (đồng thuận/xung đột), **Độ sâu lồng**, và **tỷ lệ lồng giả (spurious-nesting FPR)**.

**EN — Single-scale mode (default):**
1. Turn off the **"Multi-scale (nested)"** checkbox.
2. Set **k_drop** (0–4): denoising strength (higher = smoother). Set **threshold** (0.01–0.5): swing sensitivity (lower = more pivots).
3. (Optional) tick **"Null FPR"** to compute statistical significance (slower).
4. Click **"Run Detection"**.
5. Read the 3 panels: *Raw vs Denoised*, *Swing Skeleton* (red dots = highs, green = lows), *Detected Patterns* (coloured boxes on the chart). The report table shows pattern name, time range, **confidence score (0–100%)**, confirmed (✓) or edge ("Edge?"), and the significance %.

**EN — Multi-scale (nested) mode:**
1. Turn on the **"Multi-scale (nested)"** checkbox and select the scales (k_drop = 1,2,3,4).
2. Set the threshold and click **"Run Detection"**.
3. Read: *Denoised by Scale*, *Nested Detections* (same colour = parent-child; dashed border = unconfirmed), and the report with columns **Scale**, **Nested in**, **Relation** (agreement/conflict), **Nesting depth**, and **spurious-nesting FPR**.

---

### 📖 Thuật ngữ nhanh / Quick glossary

| Thuật ngữ / Term | Ý nghĩa / Meaning |
|---|---|
| **Cone of Influence (COI)** | Vùng xám ở mép biểu đồ thời gian–tần số; dữ liệu ở đó không đáng tin — bỏ qua. / Grey edges where data is unreliable — ignore. |
| **Reconstruction error** | Sai số khi ghép lại các thành phần để khôi phục giá gốc; gần 0 là tốt. / Error when re-summing components; near 0 is good. |
| **Hurst (H)** | > 0.5 xu hướng, ≈ 0.5 ngẫu nhiên, < 0.5 hồi quy. / > 0.5 trend, ≈ 0.5 random, < 0.5 mean-reverting. |
| **Out-of-sample (OOS)** | Đoạn dữ liệu mô hình chưa từng thấy khi huấn luyện — phản ánh hiệu năng thật. / Data the model never trained on — reflects true performance. |

---

# PHẦN 2 — CÔNG CỤ HỖ TRỢ QUYẾT ĐỊNH (Menu: Công cụ hỗ trợ quyết định)
# PART 2 — DECISION TOOLS (Menu: Decision Tools)

Menu này gồm 12 mục con, đi theo một quy trình giao dịch khép kín: **hiểu hệ thống → phân tích → quét cơ hội → kiểm thử → kỷ luật → theo dõi vị thế → đánh giá kết quả → quản trị rủi ro**.

This menu has 12 sub-items forming an end-to-end trading workflow: **understand the system → analyze → scan for opportunities → backtest → discipline → track positions → review outcomes → manage risk**.

---

## 2.1 — Tổng quan / General View

**🎯 Lợi ích / Benefit**
- **VI:** Hiểu **toàn bộ quy trình ra quyết định** của hệ thống trước khi dùng các công cụ khác. Tránh dùng sai thứ tự, tiết kiệm thời gian.
- **EN:** Understand the **entire decision pipeline** before using the other tools, so you use them in the right order and save time.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Chỉ xem (không nhập liệu). Đọc sơ đồ 4 giai đoạn: *Kiểm tra trạng thái thị trường → Kiểm tra tín hiệu → Kiểm tra kỷ luật → Tính kích thước lệnh & khuyến nghị*. Tham khảo quy trình 5 bước hằng ngày và các thẻ mô tả từng công cụ con.
- **EN:** View-only (no input). Read the 4-stage flowchart: *Regime check → Signal check → Discipline check → Position sizing & recommendation*. Follow the recommended 5-step daily workflow and the reference cards for each sub-tool.

---

## 2.2 — Màn hình quyết định / Decision Console

**🎯 Lợi ích / Benefit**
- **VI:** Công cụ cốt lõi: phân tích **một cổ phiếu** và nhận **khuyến nghị giao dịch cụ thể** — giá vào, cắt lỗ, chốt lời, số lượng cổ phiếu — kèm lý do (tín hiệu, trạng thái thị trường, độ tin cậy).
- **EN:** The core tool: analyze **a single stock** and get a **concrete recommendation** — entry, stop-loss, target, and share count — with the reasoning (signal, regime, confidence).

**🛠️ Cách thực hiện / How to achieve it**
- **VI:**
  1. Nhập **mã cổ phiếu** và **ngày phân tích** (mặc định hôm nay).
  2. (Tuỳ chọn) mở bảng tuỳ chỉnh rủi ro: vốn tài khoản, % rủi ro tối đa/lệnh, số vị thế tối đa, tương quan tối đa.
  3. Chạy phân tích và đọc kết quả: **Trạng thái thị trường** (Tăng/Giảm/Đi ngang), **tín hiệu kích hoạt**, **độ tin cậy (0–100%)**, **hành động khuyến nghị** (MUA / BÁN / BÁN KHỐNG / MUA LẠI / GIỮ / CHỜ / ĐẢO CHIỀU), cùng **giá vào / cắt lỗ / mục tiêu** và **số lượng cổ phiếu**.
  4. Có thể lưu khuyến nghị thành kế hoạch giao dịch trong nhật ký.
- **EN:**
  1. Enter a **ticker** and a **bar date** (defaults to today).
  2. (Optional) open the risk panel: account equity, max risk % per trade, max concurrent positions, max correlation.
  3. Run the analysis and read: **Market regime** (Up/Down/Range), the **triggering signal**, **confidence (0–100%)**, the **recommended action** (BUY / SELL / SELL SHORT / COVER / HOLD / WAIT / REVERSE), with **entry / stop / target** prices and **share count**.
  4. You can save the recommendation as a trade plan in the journal.

---

## 2.2.1 — Xác nhận bằng khối lượng / Volume validation (Edwards & Magee)

**🎯 Lợi ích / Benefit**
- **VI:** Một mẫu hình đẹp trên biểu đồ chưa chắc đáng tin. Edwards & Magee coi **khối lượng là điều kiện hiệu lực** của mẫu hình, không phải thứ trang trí. Mục này cho bạn biết khối lượng **xác nhận hay phản bác** từng mẫu hình, và vì sao — để bạn không vào lệnh theo một hình vẽ mà thị trường không hề hưởng ứng.
- **EN:** A clean-looking pattern is not automatically a trustworthy one. Edwards & Magee treat **volume as the condition of a pattern's validity**, not as decoration. This tells you whether volume **confirms or contradicts** each pattern, and why — so you do not act on a shape the market never backed.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:**
  1. Mở **Màn hình quyết định** (mục 2.2) và xem bảng **Mẫu biểu đồ**. Mỗi thẻ mẫu hình nay có một **nhãn khối lượng**.
  2. Đọc nhãn: **Khối lượng xác nhận** (khối lượng ủng hộ mẫu hình) · **trung tính** (không nói gì) · **phản bác** (khối lượng đi ngược điều kiện) · **đáng ngờ** (⚠ khối lượng *đảo ngược ý nghĩa* mẫu hình — xem bên dưới).
  3. Xem cặp số **Hình mẫu 70% → 59%**: số đầu là độ tin cậy chỉ dựa trên *hình dạng*, số sau là độ tin cậy **sau khi** tính khối lượng. Nếu chỉ hiện một số, khối lượng không làm thay đổi gì.
  4. Mỗi dòng bên dưới là **một điều kiện của sách**, kèm con số thực tế (ví dụ *vai phải nhẹ hơn vai trái · 0,53×*) và chương sách (E&M Ch 6). Dòng không đọc được sẽ **ẩn đi**, không hiển thị như một điều kiện thất bại.
  5. Bảng **Mẫu biểu đồ** trên trang **AI Insights** (Phân tích ▸ AI Insights) hiển thị cùng nhãn ở dạng gọn. Lưu ý: bảng *Nhận diện mẫu hình* ở trên nó là công cụ **khác** (xu hướng theo đường trung bình), không có khối lượng.
- **EN:**
  1. Open the **Decision Console** (§2.2) and look at the **Chart Patterns** panel. Every pattern card now carries a **volume verdict**.
  2. Read the verdict: **Volume confirms** (volume supports the pattern) · **neutral** (it says nothing) · **contradicts** (volume fails the condition) · **suspect** (⚠ volume *inverts the pattern's meaning* — see below).
  3. Read the pair **Shape 70% → 59%**: the first number is confidence from *geometry alone*, the second is confidence **after** volume. If only one number shows, volume changed nothing.
  4. Each row beneath is **one condition from the book**, with the figure behind it (e.g. *right shoulder lighter than left · 0.53×*) and the chapter (E&M Ch 6). A row that cannot be read is **hidden**, not shown as a failed condition.
  5. The **Chart Patterns** card on the **AI Insights** page (Analysis ▸ AI Insights) shows the same verdict compactly. Note the *Pattern Recognition* table above it is a **different** tool (moving-average trend), with no volume.

**⚠️ Bốn điều cần biết / Four things worth knowing**
- **VI:**
  - **Độ tin cậy đã thay đổi.** Con số trên thẻ mẫu hình giờ là *hình dạng × khối lượng*, nên nó **khác với trước đây** — thường thấp hơn. Đây là thay đổi có chủ ý. Độ tin cậy trên **thẻ hành động** (MUA/CHỜ…) **không** bị ảnh hưởng: nó đến từ tầng xác nhận tín hiệu, không liên quan mẫu hình.
  - **"Đáng ngờ" khác "phản bác".** Phản bác = thiếu bằng chứng. Đáng ngờ = bằng chứng *ngược lại*: khối lượng lớn khi phá vỡ **xuống** của tam giác thường là cú rũ bỏ 2–3 ngày (Ch 8); khối lượng lớn **trong** lá cờ biến nó thành vùng đảo chiều (Ch 11). Ở đây **khối lượng càng lớn càng xấu**.
  - **Quy tắc bất đối xứng.** Phá vỡ **lên** *bắt buộc* có khối lượng tăng; phá vỡ **xuống** thì không — *"cần có lực mua để đẩy giá lên, nhưng giá có thể tự rơi vì trọng lượng của nó"* (Ch 7).
  - **Mã thanh khoản thấp:** nếu thấy *"Khối lượng quá mỏng để đánh giá"*, hệ thống **không** phạt mẫu hình — thiếu dữ liệu không phải bằng chứng xấu.
- **EN:**
  - **Confidence has changed.** The number on a pattern card is now *shape × volume*, so it **differs from before** — usually lower. That is intended. The confidence on the **action card** (BUY/WAIT…) is **unaffected**: it comes from the signal confirmation layer and never touched patterns.
  - **"Suspect" is not "contradicts".** Contradicts = evidence missing. Suspect = evidence *the other way*: heavy volume on a **downside** triangle break is usually a 2–3 day shakeout (Ch 8), and heavy volume **inside** a flag turns it into a reversal area (Ch 11). Here **more volume is worse**.
  - **The rule is asymmetric.** An **upside** break *requires* volume expansion; a **downside** break does not — *"it takes buying to put stocks up, but they can fall of their own weight"* (Ch 7).
  - **Thin tickers:** if you see *"Volume too thin to judge"*, the pattern is **not** penalised — missing data is not adverse evidence.

**📊 Cao trào khối lượng / Volume climax**
- **VI:** Khi xuất hiện, một dải cảnh báo hiện trên bảng: khối lượng cực lớn mà **giá gần như không đi đâu** (Ch 10 "cao trào bán", Ch 28). Đây là **thông tin tham khảo** — hệ thống không tự đổi khuyến nghị. Rất hiếm: trong 18 mã thử nghiệm chỉ 2 mã có.
- **EN:** When present, a banner appears on the panel: enormous volume with **price going nowhere** (Ch 10's selling climax, Ch 28). It is **evidence only** — nothing in the recommendation changes because of it. It is genuinely rare: 2 of 18 symbols tested.

**🔧 Thông số / Parameters**
- **VI:** Cửa sổ so sánh khối lượng mặc định là **100 phiên** (hiển thị trong phản hồi API là `baseline_window`); "cao trào" dùng cửa sổ dài **120 phiên**. Các giá trị này được **đo và chọn bằng dữ liệu**, không phải lấy từ sách — xem `docs/em1_s2_parameter_sweep.md`.
- **EN:** The volume comparison window defaults to **100 bars** (reported as `baseline_window` in the API response); the climax check uses a longer **120-bar** window. These values were **measured and chosen from data**, not taken from the book — see `docs/em1_s2_parameter_sweep.md`.

---

## 2.3 — Bảng quyết định Watchlist / Watchlist Board

**🎯 Lợi ích / Benefit**
- **VI:** Xem khuyến nghị cho **tất cả cổ phiếu trong watchlist** cùng lúc dưới dạng bảng, để **so sánh** độ tin cậy và tỷ lệ lời/lỗ giữa nhiều mã, nhanh chóng tìm mã có tín hiệu đáng giao dịch hôm nay.
- **EN:** See recommendations for **all watchlist stocks at once** in a table, to **compare** confidence and risk/reward across tickers and quickly spot which ones are actionable today.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Watchlist tự lấy từ danh mục nắm giữ + danh sách bạn lưu (có thể thêm/bớt mã). Chọn ngày phân tích. Đọc bảng: Mã, Trạng thái, Hành động (badge màu), Độ tin cậy %, Giá vào/Cắt lỗ/Mục tiêu, Số lượng. Bấm vào một dòng để mở Màn hình quyết định cho mã đó.
- **EN:** The watchlist auto-loads from your holdings + saved list (you can add/remove tickers). Pick a bar date. Read the table: Ticker, Regime, Action (colour badge), Confidence %, Entry/Stop/Target, Shares. Click a row to drill into the Decision Console for that ticker.

---

## 2.4 — Phòng thử nghiệm Backtest / Backtest Studio

**🎯 Lợi ích / Benefit**
- **VI:** **Kiểm chứng** chiến lược trên dữ liệu quá khứ trước khi giao dịch thật: biết chiến lược có thực sự hiệu quả không, ước lượng Sharpe/sụt giảm tối đa, và thử tinh chỉnh tham số để cải thiện kết quả.
- **EN:** **Validate** the strategy on historical data before trading live: learn whether it actually works, estimate Sharpe/max drawdown, and try tuning parameters to improve results.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:**
  1. Cấu hình: mã cổ phiếu, khoảng thời gian (ngày đầu/cuối), vốn ban đầu (VND), % rủi ro/lệnh (thường 1–2%).
  2. Tham số kỹ thuật: MA nhanh (mặc định 10), MA chậm (50), breakout N (20), độ trễ K.
  3. Chi phí: trượt giá (bps), phí giao dịch. Bật **walk-forward** để kiểm thử bền vững (tránh nhìn trước).
  4. Chạy và đọc kết quả: số lệnh, tỷ lệ thắng, lãi/lỗ ròng, sụt giảm tối đa, Sharpe, profit factor, R trung bình; **đường cong vốn** và **sổ lệnh chi tiết**.
- **EN:**
  1. Configure: ticker, date range (start/end), initial capital (VND), risk % per trade (typically 1–2%).
  2. Technical params: fast MA (default 10), slow MA (50), breakout N (20), K delay.
  3. Costs: slippage (bps), commission. Enable **walk-forward** for robustness (avoids look-ahead bias).
  4. Run and read: trade count, win rate, net P&L, max drawdown, Sharpe, profit factor, average R; the **equity curve** and a **detailed trade ledger**.

---

## 2.5 — Kỷ luật giao dịch / Discipline Dashboard

**🎯 Lợi ích / Benefit**
- **VI:** **Ngăn giao dịch theo cảm xúc / trả thù** sau chuỗi thua. Hệ thống giám sát các quy tắc kỷ luật (theo phương pháp Jack Schwager) và sẽ **chặn tín hiệu vào lệnh** nếu vi phạm ngưỡng rủi ro.
- **EN:** **Prevents emotional / revenge trading** after losses. The system monitors discipline rules (Jack Schwager's methodology) and will **block entry signals** if risk thresholds are breached.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Chỉ theo dõi (tự động). Xem: chuỗi lệnh thua liên tiếp, mức sụt giảm hiện tại so với đỉnh vốn, số quy tắc bị vi phạm và chi tiết từng vi phạm (ví dụ: "Thua 3 lệnh liên tiếp, ngưỡng là 2 — giảm 50% kích thước lệnh"). Có bảng tham chiếu 10 quy tắc Schwager. Hãy kiểm tra bảng này **trước khi vào lệnh mới**.
- **EN:** Auto-monitoring only. View: consecutive loss streak, current drawdown vs peak equity, count of violated rules and details of each (e.g. "Loss streak is 3, threshold 2 — cut position size by 50%"). Includes a 10-point Schwager rule reference. Check it **before opening any new trade**.

---

## 2.6 — Chạy định kỳ / Scheduled Runs

**🎯 Lợi ích / Benefit**
- **VI:** Để hệ thống **tự quét watchlist theo lịch** (mặc định 15:30 giờ VN mỗi ngày) và xem lại **lịch sử các lần chạy** cùng cảnh báo đã kích hoạt. Không bỏ lỡ tín hiệu khi bạn bận.
- **EN:** Let the system **scan your watchlist on a schedule** (default 15:30 ICT daily) and review the **history of past runs** and the alerts they fired. Never miss a signal while you're busy.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Quản lý watchlist (thêm/bớt mã, ghi chú). Bấm **"Run now"** để quét ngay nếu thị trường biến động bất ngờ. Lọc để chỉ xem các lần chạy **có cảnh báo**. Bảng nhật ký hiển thị: chuông cảnh báo, mã, ngày, hành động, trạng thái, độ tin cậy %, độ trễ (ms), thời điểm chạy.
- **EN:** Manage the watchlist (add/remove tickers, notes). Click **"Run now"** to scan immediately on an unexpected move. Filter to show only runs **with alerts**. The log shows: alert bell, ticker, bar date, action, regime, confidence %, latency (ms), run timestamp.

---

## 2.7 — Quét thị trường / Scanner

**🎯 Lợi ích / Benefit**
- **VI:** Chạy bộ máy quyết định trên **toàn bộ watchlist trong một lần quét** để tìm **tất cả cơ hội giao dịch** hôm nay, và biết ngay có bao nhiêu tín hiệu MUA / BÁN KHỐNG đáng hành động.
- **EN:** Run the decision engine across **the entire watchlist in one scan** to find **every opportunity** today and instantly see how many actionable BUY / SELL SHORT signals exist.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Chọn ngày phân tích, bấm quét. Đọc thanh tóm tắt ("Đã quét 50 mã · 8 MUA · 3 BÁN KHỐNG · 1 đáng hành động") và bảng chi tiết: Mã, Hành động, Trạng thái, Độ tin cậy, Giá vào/Cắt lỗ/Mục tiêu, Tín hiệu. Lọc/sắp xếp theo loại hành động. Bấm "Plan" trên một dòng để mở Màn hình quyết định.
- **EN:** Pick a bar date and scan. Read the summary bar ("Scanned 50 tickers · 8 BUY · 3 SELL SHORT · 1 actionable") and the detailed table: Ticker, Action, Regime, Confidence, Entry/Stop/Target, Signal. Filter/sort by action type. Click "Plan" on a row to open the Decision Console.

---

## 2.8 — Bản đồ nhiệt Watchlist / Heat Map

**🎯 Lợi ích / Benefit**
- **VI:** Cái nhìn **trực quan bằng màu sắc** về động lượng toàn watchlist — nhận ra ngay mã đang tăng (xanh), giảm (đỏ) hay tích lũy (vàng). Dễ "đọc" hơn bảng số khi tìm cơ hội nhanh.
- **EN:** A **visual, colour-coded** view of momentum across the watchlist — instantly spot trending (green), declining (red), or consolidating (yellow) stocks. Easier to "read" than a table for quick scanning.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Mỗi mã là một thẻ màu hiển thị trạng thái, hành động (badge), thanh độ tin cậy (đỏ < 50%, vàng 50–70%, xanh > 70%) và giá vào/cắt lỗ/mục tiêu nếu đáng hành động. Lọc (Tất cả / Đáng hành động / chỉ MUA / chỉ BÁN KHỐNG / GIỮ / CHỜ) và sắp xếp (độ tin cậy, mã, hành động, trạng thái).
- **EN:** Each ticker is a colour tile showing regime, action badge, a confidence bar (red < 50%, yellow 50–70%, green > 70%) and entry/stop/target if actionable. Filter (All / Actionable / BUY only / SELL SHORT only / HOLD / WAIT) and sort (confidence, ticker, action, regime).

---

## 2.9 — Phân tích hiệu suất / Analytics

**🎯 Lợi ích / Benefit**
- **VI:** Bảng tổng quan hiệu suất của **toàn hệ thống quyết định**: biết **tín hiệu nào đáng tin nhất** (tỷ lệ xác nhận cao), hệ thống có giao dịch quá tập trung vào một mã không, và phân bố tín hiệu/độ tin cậy theo thời gian.
- **EN:** A performance overview of the **whole decision system**: learn **which signals are most reliable** (high confirmation rate), whether it over-trades certain stocks, and how signals/confidence are distributed over time.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Chọn khoảng thời gian (30/60/90/180/365 ngày). Đọc thẻ tóm tắt (tổng quyết định, số đáng hành động, tín hiệu/trạng thái phổ biến nhất), biểu đồ tín hiệu đáng hành động theo ngày, phân bố hành động, phân bố độ tin cậy, phân bố trạng thái, bảng tín hiệu (số lần, đã xác nhận, tỷ lệ xác nhận %, độ tin cậy TB) và bảng mã giao dịch nhiều nhất.
- **EN:** Choose a time range (30/60/90/180/365 days). Read the summary cards (total decisions, actionable count, top signal/regime), the daily actionable chart, action distribution, confidence distribution, regime breakdown, the signal table (fires, confirmed, confirmation rate %, avg confidence) and the top-tickers table.

---

## 2.10 — Vị thế đang mở / Open Positions

**🎯 Lợi ích / Benefit**
- **VI:** Thấy **toàn bộ rủi ro đang mở** trong nháy mắt và **dời cắt lỗ (trail stop)** ngay tại chỗ để khóa lợi nhuận khi lệnh thắng phát triển.
- **EN:** See **all open risk** at a glance and **trail your stops** inline to lock in profit as winning trades develop.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Mỗi dòng hiển thị: Mã, Hướng (LONG/SHORT), ngày vào & số ngày giữ, giá vào & cắt lỗ hiện tại, **% rủi ro**, giá mục tiêu, tín hiệu vào. Bấm **"Update Stop"** để nhập giá cắt lỗ mới và lưu (hệ thống kiểm tra: cắt lỗ LONG phải < giá vào, SHORT phải > giá vào).
- **EN:** Each row shows: Ticker, Direction (LONG/SHORT), entry date & days held, entry price & current stop, **risk %**, target price, entry signal. Click **"Update Stop"** to enter a new stop and save (the system validates: long stops < entry, short stops > entry).

---

## 2.11 — Kết quả giao dịch / Trade Outcomes

**🎯 Lợi ích / Benefit**
- **VI:** Đánh giá **lợi thế giao dịch thực sự**: loại tín hiệu nào hay thắng, lời/lỗ theo bội số R, kỳ vọng mỗi lệnh, và **bản phân tích hậu kỳ bằng AI** giải thích vì sao một lệnh thắng/thua để rút kinh nghiệm.
- **EN:** Audit your **real trading edge**: which signals actually win, P&L in R-multiples, expectancy per trade, and an **AI post-mortem** explaining why a trade won or lost so you can learn.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Tự động ghi nhận lệnh đã đóng. Xem thống kê (thắng/thua/hòa, tỷ lệ thắng %, R trung bình, kỳ vọng VND) theo 30/60/90 ngày; sổ kết quả (thanh R trực quan) và phân tích theo loại tín hiệu / trạng thái thị trường / ngày trong tuần / thời gian giữ. Bấm **"Generate AI Review"** trên một lệnh để nhận giải thích của AI (kết quả được lưu cache).
- **EN:** Closed trades are recorded automatically. View stats (win/loss/even, win rate %, average R, expectancy in VND) over 30/60/90 days; the outcome log (visual R bars) and attribution by signal type / regime / weekday / hold duration. Click **"Generate AI Review"** on a trade to get the AI's explanation (results are cached).

---

## 2.12 — Bảng rủi ro / Risk Dashboard

**🎯 Lợi ích / Benefit**
- **VI:** Giám sát **rủi ro toàn danh mục**: tổng mức rủi ro trước khi mở thêm vị thế, **mức tương quan giữa các mã** (tránh tập trung rủi ro), và **kịch bản xấu nhất** nếu mọi cắt lỗ bị chạm. Hệ thống sẽ **chặn lệnh mới** nếu vượt giới hạn rủi ro.
- **EN:** Monitor **portfolio-level risk**: total risk before adding a position, **correlation between holdings** (avoid concentrated risk), and the **worst-case scenario** if all stops hit at once. The system **blocks new trades** if risk exceeds limits.

**🛠️ Cách thực hiện / How to achieve it**
- **VI:** Tự động tổng hợp. Xem thẻ tóm tắt (số vị thế mở, % rủi ro tổng, phơi nhiễm ròng, vốn, số LONG/SHORT, VND rủi ro nếu mọi cắt lỗ bị chạm), thiên hướng long/short, kịch bản xấu nhất (% sụt giảm), bảng chi tiết vị thế, và **ma trận tương quan** (ô đỏ = tương quan dương cao → rủi ro tập trung; ô tím = tương quan âm → phòng hộ tốt; viền đỏ = vượt giới hạn). Cảnh báo ở 70% và chặn ở 100% giới hạn rủi ro tích lũy.
- **EN:** Auto-aggregated. View summary cards (open positions, total risk %, net exposure, equity, long/short count, VND at risk if all stops hit), long/short bias, worst-case drawdown %, a position detail table, and the **correlation matrix** (red = high positive correlation → concentrated risk; purple = negative → good hedge; red outline = breaches the max-correlation limit). Warns at 70% and blocks at 100% of the cumulative-risk limit.

---

### 🔄 Quy trình khuyến nghị hằng ngày / Recommended daily workflow

1. **Kỷ luật giao dịch** — kiểm tra có bị chặn không. / **Discipline** — check you're not blocked.
2. **Bản đồ nhiệt / Quét thị trường** — tìm cơ hội. / **Heat Map / Scanner** — find opportunities.
3. **Màn hình quyết định** — phân tích sâu mã quan tâm. / **Decision Console** — deep-dive a candidate.
4. **Bảng rủi ro** — kiểm tra rủi ro danh mục trước khi vào lệnh. / **Risk Dashboard** — check portfolio risk before entering.
5. **Vị thế đang mở** — dời cắt lỗ; **Kết quả giao dịch** — đánh giá định kỳ. / **Open Positions** — trail stops; **Trade Outcomes** — review periodically.

---

*Tài liệu này mô tả các chức năng theo giao diện hiện tại. Các con số ví dụ chỉ mang tính minh họa. / This document describes the current UI. Example numbers are illustrative only.*
