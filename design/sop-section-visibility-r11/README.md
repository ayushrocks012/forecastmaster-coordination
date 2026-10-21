# Second page R11 — Independent Hide / Show controls

Open [index.html](index.html). Each of the three sections now has its own
top-right **Hide** control: Build your view (the selector), Trend view and
S&OP summary. Hiding leaves a slim heading with **Show**, so any combination
can be restored without a separate global control.

The selector's former detached Hide button has moved into its own header.
Collapsing it releases the left column and widens the graph and table. The
graph redraws at its new width. A collapsed graph or summary hides its local
presentation controls as well as its contents. Top business filters and shared
driver/sector scope stay available.

Visibility is independent of data inclusion. Hiding never clears Channels,
Sub-channels, Measures, sectors, cycles, months or summary periods. Run-rate
and growth choices also remain intact. Changes made while a section is hidden
appear when it is shown again. All three visibility choices persist in the
preview's saved state, and native buttons support keyboard use and announce
their expanded/collapsed state.

## Preserved design and checks

R10 and all earlier designs, including the approved first page, remain saved
with their original bytes. The source catalogue, audit script/receipt and R10
summary calculation rules are byte-identical copies. No Channel, measure,
calculation or source ordering changes accompany this presentation change.

`validation.json` records the existing source/derived-figure checks plus all
eight visibility combinations, independent restore, stable selections/table
values, responsive graph resizing, keyboard operation and saved-state restore.
It includes 216 amount comparisons with R10, 384 derived comparisons and 64
reconciliations. Responsive light/dark layouts, hover and zero warm requests or
script errors are checked. `preservation.json` verifies prior saved design hashes.

Review `all-hidden.png`, `graph-only.png`, `graph-hidden.png` and
`summary-only-view.png` for examples. The initial empty graph/table still require
explicit valid Channel/context/Measure choices. Values remain synthetic, and
these local checks establish no live Power BI performance or deployment result.
Power BI, application source and workbooks remain unchanged.
