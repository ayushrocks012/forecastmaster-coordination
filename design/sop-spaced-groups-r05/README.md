# Second page R05 — Spaced bridge selector

Open [index.html](index.html). This separately saved proposal follows the user's
spacing sketch: each channel has its own band, with its subchannels beside it
and Community's Share, Abbott and Market measures on the right. The graph and
summary remain to the right of the selector on desktop.

Community, Contracts and Retail no longer form a tightly stacked first column.
Homecare and Hospital align with Contracts. Its five other publishing members
are under **5 more channels**; the four other Community IMS measures are under
**More IMS measures**. Both lists expand, retain their state after selection and
open automatically for matching search results. Select all includes these
available choices. The Ex-factory ADS visibility switch remains shared across
chosen channel/subchannel totals, with remembered targets when switched off.

Share now uses the **right percentage axis on the same line graph** as selected
unit/GBP measures. Effective uplift also uses that percentage axis if selected.
Tooltips format each series using its own axis; share has a distinct colour and
an explicit right-axis legend label. Solid actuals and dashed forecast retain
each row's IMS/EF cutoff. Share is included in the useful default selection.

Summary periods are selected beside the S&OP table. Selected rows always follow
the bridge story, regardless of click order: Market, Abbott/share, PI, net IMS,
matched Community and uplift, Community Ex-factory and its children, Contracts
and its seven members, Retail, Unassigned, Total ADS. Selected FY/YTD/YTG columns
follow their canonical year/period order. Monthly mode follows the top calendars;
calendar changes do not redefine FY/YTD/YTG amounts. Parent totals include their
children and are never summed again as an extra total.

All data is synthetic. The fixture and calculation definitions match R04;
`preservation.json` binds those definitions and every earlier saved design.
The approved first page R11 and all preceding second-page versions are retained.
No application code, workbook, visual package or live Power BI content changed.

Run `node check-sop.cjs` with Playwright installed (Windows uses Microsoft Edge).
`validation.json` records 13 behavior groups, 58 reconciliation comparisons and
388 raw/formatted cells matching R01 in five scenarios. It also covers the
numeric right-axis geometry, ratio-only selections, shared hover/touch details,
summary period interaction and responsive light/dark rendering. Synthetic local
timings are not company Power BI performance evidence. Source binding, live
feasibility and production performance require separately authorized work.

Edit `page.fragment.html`; `build.py` inserts pinned MIT-licensed D3 from R01's
preserved vendor folder. `review.fragment.html` is the offline fragment and
`index.html` its prepared standalone preview.
