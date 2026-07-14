import sys
sys.path.insert(0, ".")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np
from category_map import categorise, website_rows, CATEGORIES

PNG = "website_report_category.png"

d = website_rows()
d["category"] = categorise(d)

code = d.how_did_you_find_us.astype(float)
d["source"] = np.where(code.eq(10), "Through another Art of Living Program",
                       d.how_did_you_find_us_label)
d["source"] = d.source.fillna("No Source").replace("Select", "No Source")

# Column order copied from the CRM Analytics sheet so the two read side by side.
SRC_ORDER = ["Emails", "Events", "Google", "LinkedIn", "News", "No Source",
             "Reference from a friend", "Reference from an Art of Living Teacher",
             "Through another Art of Living Program", "Twitter", "Youtube"]
SHORT = {"Reference from a friend": "Friend",
         "Reference from an Art of Living Teacher": "Teacher",
         "Through another Art of Living Program": "Other AOL Prog.",
         "No Source": "No Source"}

HDR, BAND, TOTAL = "#1f3864", "#f2f5fa", "#dce6f1"
fmt = lambda v: f"{int(v):,}" if v else "-"
ROW = 0.32


def draw(ax, title, cols, rows, widths):
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color=HDR, pad=10)
    t = ax.table(cellText=rows, colLabels=cols, colWidths=widths, bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    n = len(rows)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#c9d3e0")
        cell.set_linewidth(0.6)
        cell.PAD = 0.03
        txt = cell.get_text()
        txt.set_ha("right" if c > 0 else "left")
        if r == 0:
            cell.set_facecolor(HDR); txt.set_color("white")
            txt.set_fontweight("bold"); txt.set_ha("center"); txt.set_fontsize(8.5)
        elif r == n:
            cell.set_facecolor(TOTAL); txt.set_fontweight("bold")
        elif r % 2 == 0:
            cell.set_facecolor(BAND)
        else:
            cell.set_facecolor("white")


def widths(first, n):
    return [first] + [(1 - first) / n] * n


def period_rows(col):
    per = sorted(d[col].unique())
    p = d.pivot_table(index="category", columns=col, aggfunc="size", fill_value=0)
    p = p.reindex(CATEGORIES).fillna(0)
    rows = [[i] + [fmt(p.loc[i, x]) for x in per] + [fmt(p.loc[i].sum())] for i in p.index]
    rows.append(["Grand Total"] + [fmt(p[x].sum()) for x in per] + [fmt(p.values.sum())])
    return per, rows


def source_rows():
    p = d.pivot_table(index="category", columns="source", aggfunc="size", fill_value=0)
    p = p.reindex(index=CATEGORIES, columns=SRC_ORDER).fillna(0)
    rows = [[i] + [fmt(p.loc[i, s]) for s in SRC_ORDER] + [fmt(p.loc[i].sum())] for i in p.index]
    rows.append(["Grand Total"] + [fmt(p[s].sum()) for s in SRC_ORDER] + [fmt(p.values.sum())])
    return rows


cy_per, cy_rows = period_rows("CY")
fy_per, fy_rows = period_rows("FY")
src = source_rows()

NR = len(CATEGORIES) + 2          # header + 17 categories + grand total
FIG_W, FIG_H = 20.5, NR * ROW * 2 + 4.6
fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor="white")
fig.suptitle("Website Registrations by Course Category — CRM Grouping",
             fontsize=20, fontweight="bold", color=HDR, x=0.010, ha="left",
             y=1 - 0.30 / FIG_H)
fig.text(0.010, 1 - 1.00 / FIG_H,
         "Source: aol_website_rebuilt.csv   |   "
         "Categories per CRM - GWS Data - leads.csv (Course Type → Course Category)   |   "
         "Bucketed by course_event_start_date   |   "
         "Website = host artofliving.org   |   Status = Registered + Completed   |   Raw counts",
         fontsize=10, color="#5a6a7d", ha="left")

TOP = 1 - 1.70 / FIG_H


def place(x0, x1, y_top, nrows):
    h = nrows * ROW / FIG_H
    return fig.add_axes([x0, y_top - h, x1 - x0, h])


draw(place(0.010, 0.487, TOP, NR), "Calendar Year",
     ["Course Category"] + cy_per + ["Total"], cy_rows, widths(0.36, len(cy_per) + 1))
draw(place(0.523, 0.990, TOP, NR), "Financial Year",
     ["Course Category"] + fy_per + ["Total"], fy_rows, widths(0.36, len(fy_per) + 1))

y = TOP - NR * ROW / FIG_H - 1.30 / FIG_H
draw(place(0.010, 0.990, y, NR), "How Did You Find Us  (by course category)",
     ["Course Category"] + [SHORT.get(s, s) for s in SRC_ORDER] + ["Total"], src,
     widths(0.17, len(SRC_ORDER) + 1))

fig.text(0.010, 0.35 / FIG_H,
         "Category mapping: 60,678 rows matched a CRM course type exactly; 4,994 folded in by the Intuition Process rule "
         "(the CRM treats all IP variants as one type); 154 by explicit override; 391 defaulted to Others.\n"
         "Periods are course start dates, so later periods are forward-looking: 743 courses start after the 10-Jul-2026 pull date, "
         "the last in Feb-2029. CY2023 / FY 2023-24 begin at the extract's floor of 01-Apr-2023.\n"
         "Source capture began Feb-2024, so courses starting in CY2023 / FY 2023-24 are overwhelmingly No Source. "
         "No Source = 36,596 (rebuilt join; 131 rows have no CiviCRM details record).\n"
         "Universe: artofliving.org only. The upstream extract now contains no artofliving.online rows at all.",
         fontsize=8.5, color="#5a6a7d", ha="left", va="bottom", linespacing=1.7)

fig.savefig(PNG, dpi=150, facecolor="white")
print(f"saved {PNG}")
