# Claude Code prompt — Stock dashboard redesign

Copy everything below the `--- PROMPT START ---` line into Claude Code, and attach `dashboard-proposal.png` to the same message.

---
**PROMPT START**
---

I want to redesign the Dashboard page (`Bảng điều khiển` route) of my StockAI React app. The new design is in the attached image (`dashboard-proposal.png`). Please rebuild the UI to match it, while preserving all existing functionality, routing, data fetching, Vietnamese labels, and the full sidebar menu structure (including submenus and the collapse-to-icons behavior).

## Discover first, then change

1. Read `package.json` to confirm the React version, the styling approach (CSS modules / plain CSS / Tailwind), and whether `recharts` and `lucide-react` are already installed (they appear to be — confirm).
2. Locate the Dashboard page component (likely under `src/pages` or `src/components` — search for "Bảng điều khiển" or "Khuyến nghị AI" to find it).
3. Locate the Sidebar component (search for "StockAI" or "sidebar-nav").
4. Locate the Header component (search for "header-right" or "logout-button").
5. Locate the global stylesheet (likely `src/index.css` or `src/App.css`).
6. **Do not change** any route definitions, navigation `onClick` handlers, API calls, Redux/Context state, or the data shape of recommendations/portfolio. UI only.

## Design system to apply

Add these to your global CSS as variables, and use them everywhere instead of the current Tailwind-y inline classes:

```css
:root {
  --paper:#F5F2EA;    /* page background — warm cream */
  --panel:#FFFFFF;    /* raised surfaces */
  --sidebar:#EEEBE2;  /* sidebar background */
  --line:#DDD9CF;     /* hairline borders */
  --rule:#EEEBE2;     /* softer in-card dividers */
  --ink:#1A1810;      /* primary text */
  --ink2:#6B6859;     /* secondary text */
  --ink3:#8F8C7F;     /* tertiary / labels */
  --pos:#2C5F4A;      /* positive (gains, BUY) */
  --neg:#9B2C2C;      /* negative (losses, SELL) */
  --amber:#88683E;    /* HOLD, accents */
}
```

**Fonts** — load from Google Fonts in `public/index.html`:
- **Geist** — body font, weights 400 and 500
- **Geist Mono** — for ALL numbers, labels, and timestamps (this is the most important rule)
- **Instrument Serif** — for page headings (H1) and card titles only, with `font-style: italic` on emphasis spans

```html
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
```

## Design principles (non-negotiable)

1. **Mono numbers, mono labels.** Every price, percentage, count, and ALL CAPS label uses Geist Mono. This is what makes the UI feel like a real trading product.
2. **No gradients anywhere.** Remove the purple-blue gradient table header. Remove the blue-to-purple icon gradient on "Danh mục đầu tư". Hairline borders only.
3. **No decorative icons on stat cards.** The colored circle icons next to "Tổng giá trị", "Lãi/Lỗ" etc. must go. The number is the value, not its decoration.
4. **Monochrome sidebar icons.** Replace the rainbow `style="color: rgb(...)"` inline colors with `var(--ink3)` for inactive and `var(--ink)` for active. The active item is shown by white background + dark text + hairline border, not by a colored icon.
5. **Header layout.** Left side: live-update timestamp (with pulsing green dot) above the H1 page title. Right side: search box (with ⌘K hint) + notification icon button + "Đăng xuất" button. No floating centered elements.
6. **User profile moves to the sidebar bottom.** Remove the user avatar/email from the header. Show it in the sidebar footer above the "Thu gọn menu" collapse button.
7. **Empty states get hierarchy.** Icon in a hairline-bordered circle → serif italic title → muted sub-text (≤2 lines) → secondary action button.
8. **Footer** stays at the bottom of the main content, but restyle as a dark slab (`--ink` background, `--paper` author name, `--ink3` link).

## Sidebar specifics

- Width: **248px** when expanded, **64px** when collapsed (icons only).
- Preserve all 12 menu items in the exact order shown in the current app:
  Bảng điều khiển, Bảng giá, Cổ phiếu, Biến động thị trường, Dự đoán, Mô phỏng giao dịch với AI, Trợ lý AI, Phân tích, Danh mục, Nhật ký giao dịch, Decision Helper, Công cụ.
- Preserve which items have submenus (the chevron-right items in current code).
- Submenus indent under parent with a thin left border (`1px solid var(--line)`), font-size 12px, no icons.
- The brand "StockAI" uses Instrument Serif with "AI" in italic.

## Stat cards specifics

Four cards in a `grid-template-columns: repeat(4, 1fr); gap: 10px`:
- `Tổng giá trị` → `$0` → meta: "Chưa có khoản đầu tư"
- `Lãi / Lỗ` → `+$0` → meta: "Hôm nay"
- `Cổ phiếu nắm giữ` → `0` → meta: "0 mã đang nắm"
- `Thay đổi trong ngày` → `+2.34%` (color `var(--pos)`) → meta: "VN-Index +0.42%"

Card style: `background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px;`. Label = uppercase Geist Mono 10px, value = Geist Mono 22px weight 500, meta = Geist Mono 11px in `var(--ink3)`.

## Portfolio card

- Header: small uppercase mono label "Danh mục đầu tư", below it a serif title showing the count ("0 mã đang nắm giữ"). Right side: black "+ Thêm cổ phiếu" button.
- Table header row uses uppercase mono labels, hairline border bottom — NO gradient.
- Right-align numeric columns: Số lượng, Giá TB, Giá hiện tại, Thay đổi, Giá trị.
- Empty state in the screenshot.

## AI recommendations card

Each row is a horizontal flex layout:
1. Action badge (BUY = `#E8EFE9` bg + `--pos` text; HOLD = `#F2E8D8` bg + `--amber` text; SELL = `#F4E3E0` bg + `--neg` text). Padding `4px 10px`, border-radius 6px, mono uppercase 10px.
2. Symbol (mono 13px, weight 500) · Company name (sans 12px, `--ink2`).
3. Note text below (sans 12px, `--ink2`).
4. Right side: small "Độ tin cậy" label, large mono percentage, 3px-tall confidence bar below (filled with `--pos` if ≥80%, `--amber` if 60–79%, `--neg` if <60%).

Card header: small sparkle SVG in `--amber` + "Khuyến nghị AI · 5 mã" label + "Xem tất cả" link on the right.

## "Cổ phiếu tiềm năng" card

Same card style. Header includes the star icon and the full subtitle "Dựa trên phân tích cơ bản: tin tức tích cực, tỷ số P/E hấp dẫn và tăng trưởng lợi nhuận 2 năm". Empty state with star icon, title "Chưa có cổ phiếu tiềm năng", subtitle "Hệ thống đang phân tích thị trường. Vui lòng quay lại sau để xem các mã được đề xuất."

## Footer

```
[ Pham Hoang Tuan ]  |  [✉ tuanph1970@gmail.com]
```
Background `var(--ink)`, padding `14px 22px`, border-radius 8px, centered flex.

## Verification checklist (run after the change)

- [ ] All 12 sidebar items navigate to the same routes as before.
- [ ] Submenu expand/collapse for "Công cụ" (and any other parent-with-children items) still works.
- [ ] Sidebar collapse-to-icons toggle still works.
- [ ] All numbers in stat cards, portfolio table, and AI confidence percentages render in Geist Mono.
- [ ] No purple/blue gradient anywhere.
- [ ] No decorative colored circle icons on stat cards.
- [ ] Mobile responsive layout still works (sidebar slides out as drawer below 768px).
- [ ] No console errors, no broken imports.

When done, briefly summarise which files you modified and any decisions you made that weren't explicit in this prompt.

---
**PROMPT END**
---
