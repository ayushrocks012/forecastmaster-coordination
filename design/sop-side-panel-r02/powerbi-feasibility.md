# Power BI feasibility — design guidance, 21 October 2026

An anchored selector with a floating appearance is a feasible design direction.
Microsoft documents selectable button slicers in vertical/grid layouts and
bookmarks that control object visibility. A report can therefore offer a styled
selector and show/hide controls. Use display-only bookmarks when hiding controls
so the user's filters are retained.

- [Button slicers](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-button-slicer)
- [Bookmarks, display properties and visibility](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-bookmarks)

This is design feasibility, not a tested company implementation. The preview's
buttons select heterogeneous measures, including ratios and parent/child totals;
they are not simply a channel filter on fact rows. Implementation must preserve
that distinction. Exact click-on/off behavior and Clear all = no measures need
qualification in the receiving Power BI version. The preview's automatic space
reflow on hiding the selector is also a custom-layout behavior, not a promise
that native bookmarks resize report visuals.

The current report's custom visual is a possible implementation route for those
interactions inside its allocated canvas. No new package or model change has
been prepared here. Free dragging across the report or the Service shell is not
part of the proposal. Actual data freshness and response times still require
separate production checks after design approval.
