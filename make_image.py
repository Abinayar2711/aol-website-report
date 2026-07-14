import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

CALENDAR = "--calendar" in sys.argv
XL = "website_report_3CY.xlsx" if CALENDAR else "website_report_3FY.xlsx"
PNG = XL.replace(".xlsx", ".png")

share = pd.read_excel(XL, "1_Website Share", index_col=0)
prog = pd.read_excel(XL, "2_Program Type", index_col=0)
src = pd.read_excel(XL, "3_How Did You Find Us", index_col=0)
buck = pd.read_excel(XL, "4_Source Buckets", index_col=0)

# Period columns come from the workbook, so FY (3 cols) and CY (4) both render.
FY = [p for p in share.index if p != "Grand Total"]
PERIOD_LABEL = "Calendar Year" if CALENDAR else "Financial Year"

HDR, BAND, TOTAL = "#1f3864", "#f2f5fa", "#dce6f1"
fmt = lambda v: f"{int(v):,}"
pct = lambda v: f"{v:.2f}%"
ROW = 0.30  # inches per row, used to size the axes


def widths(first, n):
    """`first` for the label column, the remainder split evenly across n columns."""
    return [first] + [(1 - first) / n] * n


def draw(ax, title, cols, rows, widths):
    """Render a table that exactly fills `ax` (bbox=[0,0,1,1] defeats auto-sizing)."""
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color=HDR, pad=10)
    t = ax.table(cellText=rows, colLabels=cols, colWidths=widths,
                 bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False)
    t.set_fontsize(9.5)
    n = len(rows)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#c9d3e0")
        cell.set_linewidth(0.6)
        cell.PAD = 0.04
        txt = cell.get_text()
        txt.set_ha("right" if c > 0 else "left")
        if r == 0:
            cell.set_facecolor(HDR)
            txt.set_color("white")
            txt.set_fontweight("bold")
            txt.set_ha("center")
        elif r == n:  # last data row is always the total
            cell.set_facecolor(TOTAL)
            txt.set_fontweight("bold")
        elif r % 2 == 0:
            cell.set_facecolor(BAND)
        else:
            cell.set_facecolor("white")


# ---- assemble row sets first, so the figure can be sized from them
p = prog.drop(index="Grand Total")
prog_rows = [[i, fmt(p.loc[i, "Total"])] + [fmt(p.loc[i, f]) for f in FY]
             + [pct(p.loc[i, "% of Total Reg"])] for i in p.index]
prog_rows.append(["Grand Total", fmt(p["Total"].sum())] + [fmt(p[f].sum()) for f in FY] + ["100.00%"])

s = src.drop(index="Grand Total")
src_rows = [[i, fmt(s.loc[i, "Total"])] + [fmt(s.loc[i, f]) for f in FY]
            + [pct(s.loc[i, "% of Website Reg"])] for i in s.index]
src_rows.append(["Grand Total", fmt(s["Total"].sum())] + [fmt(s[f].sum()) for f in FY] + ["100.00%"])

sh = share.drop(index="Grand Total")
share_rows = [[i, fmt(sh.loc[i, "Website Registrations"]), fmt(sh.loc[i, "All Registrations"]),
               pct(sh.loc[i, "Website Share %"])] for i in sh.index]
share_rows.append(["Grand Total", fmt(sh["Website Registrations"].sum()),
                   fmt(sh["All Registrations"].sum()),
                   pct(sh["Website Registrations"].sum() / sh["All Registrations"].sum() * 100)])

b = buck.drop(index="Grand Total").sort_values("Total", ascending=False)
SHORT = {"Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)":
         "Marketing Channels (YT/Google/Events/Email/…)"}
buck_rows = [[SHORT.get(i, i), fmt(b.loc[i, "Total"])] + [fmt(b.loc[i, f]) for f in FY]
             + [pct(b.loc[i, "% of Website Reg"])] for i in b.index]
buck_rows.append(["Total", fmt(b["Total"].sum())] + [fmt(b[f].sum()) for f in FY] + ["100.00%"])

# left column height drives the figure; right column stacks three tables + gaps
left_rows = len(prog_rows) + 1
right = [(len(src_rows) + 1), (len(share_rows) + 1), (len(buck_rows) + 1)]

FIG_H = left_rows * ROW + 3.6  # header block + footnote block
FIG_W = 20 + 1.3 * (len(FY) - 3)  # keep column width roughly constant as periods grow
fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor="white")
fig.suptitle(f"Website Registrations — {PERIOD_LABEL} Report",
             fontsize=20, fontweight="bold", color=HDR, x=0.012, ha="left", y=0.985)
fig.text(0.012, 1 - 1.05 / FIG_H,
         "Source: aol_websitequery_result_with_tags_and_referral.csv   |   "
         "Website = registrations referred from artofliving.org   |   "
         f"Bucketed by registration_date ({PERIOD_LABEL.lower()})   |   "
         "Status = Registered + Completed   |   Duplicate join rows removed",
         fontsize=10, color="#5a6a7d", ha="left")

TOP, BOT = 1 - 1.7 / FIG_H, 1.5 / FIG_H
span = TOP - BOT


def place(x0, x1, y_top, nrows):
    """Axes rect for a table of nrows (incl. header), anchored at y_top (figure frac)."""
    h = nrows * ROW / FIG_H
    return fig.add_axes([x0, y_top - h, x1 - x0, h])


draw(place(0.012, 0.487, TOP, left_rows),
     "Registrations by Program Type",
     ["Program Type", "Total"] + FY + ["% of Total"], prog_rows,
     widths(0.30, len(FY) + 2))

TITLE_GAP = 0.42 / FIG_H   # room for each right-hand table's title
y = TOP
draw(place(0.523, 0.988, y, right[0]),
     "How Did You Find Us  (within website registrations)",
     ["Source", "Total"] + FY + ["% of Website"], src_rows,
     widths(0.34, len(FY) + 2))

y -= right[0] * ROW / FIG_H + TITLE_GAP + 0.9 / FIG_H
draw(place(0.523, 0.988, y, right[1]),
     "Website Share of All Registrations",
     [PERIOD_LABEL, "Website Reg.", "All Reg.", "Website Share %"], share_rows,
     widths(0.28, 3))

y -= right[1] * ROW / FIG_H + TITLE_GAP + 0.9 / FIG_H
draw(place(0.523, 0.988, y, right[2]),
     "Source Buckets",
     ["Source", "Reg."] + FY + ["Value %"], buck_rows,
     widths(0.42, len(FY) + 2))

# Source capture only began Feb 2024, so early periods are mostly unattributed.
# Name the offenders from the data rather than hardcoding a period label.
no_src = (src.loc["No Source", FY] / src.loc["Grand Total", FY] * 100)
bad = [p for p in FY if no_src[p] > 50]
good = [p for p in FY if no_src[p] <= 50]
caveat = (f"Caveat: source capture began Feb-2024 — {', '.join(f'{p} {no_src[p]:.0f}% no source' for p in bad)}"
          f"{'; read the source mix for ' + ' / '.join(good) + ' only' if good else ''}.")

# The extract starts 2023-04-01 and runs to the pull date, so the first and last CY are clipped.
partial = ("Partial years: CY2023 covers Apr–Dec 2023 (9 months) and CY2026 covers Jan–Jul 2026 "
           "(data pulled 10-Jul-2026). Do not compare their totals to the full years.\n" if CALENDAR else "")

fig.text(0.012, 0.35 / FIG_H,
         "* Code 10 has no label in staging; inferred as \"Through another Art of Living Program\" — pending CRM confirmation.\n"
         + partial + caveat + "\n"
         "Universe: artofliving.org only (host match). Excludes artofliving.online, non-AOL referrers "
         "(google.com, facebook, bit.ly, linktr.ee), and the translate.goog proxy.",
         fontsize=9, color="#5a6a7d", ha="left", va="bottom", linespacing=1.7)

fig.savefig(PNG, dpi=150, facecolor="white")
print(f"saved {PNG}  ({FIG_W:.0f}x{FIG_H:.1f} in)")
