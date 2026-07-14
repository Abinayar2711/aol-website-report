import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd, numpy as np

WEB = "aol_website_rebuilt.csv"
PNG = "website_report_CY_FY_split.png"
KEEP = ["Registered", "Completed"]

d = pd.read_csv(WEB, dtype=str).drop_duplicates()
d = d[d.participant_status.isin(KEEP)]
# Host match, not substring: .online carries the marketing site in a referrer= param.
host = d.referal_site.str.extract(r"^https?://([^/:]+)", expand=False).str.lower()
d = d[host.str.match(r"(.*\.)?artofliving\.org$", na=False)]
code = d.how_did_you_find_us.astype(float)
d["source"] = np.where(code.eq(10), "Through another Art of Living Program",
                       d.how_did_you_find_us_label)
d["source"] = d.source.fillna("No Source").replace("Select", "No Source")

ORDER = ["No Source", "Reference from a friend", "Google",
         "Reference from an Art of Living Teacher",
         "Through another Art of Living Program", "Youtube",
         "Events", "News", "Emails", "LinkedIn", "Twitter"]

HDR, BAND, TOTAL = "#1f3864", "#f2f5fa", "#dce6f1"
fmt = lambda v: f"{int(v):,}"
ROW = 0.32


def draw(ax, title, cols, rows, widths):
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color=HDR, pad=10)
    t = ax.table(cellText=rows, colLabels=cols, colWidths=widths, bbox=[0, 0, 1, 1])
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
            cell.set_facecolor(HDR); txt.set_color("white")
            txt.set_fontweight("bold"); txt.set_ha("center")
        elif r == n:
            cell.set_facecolor(TOTAL); txt.set_fontweight("bold")
        elif r % 2 == 0:
            cell.set_facecolor(BAND)
        else:
            cell.set_facecolor("white")


def widths(first, n):
    return [first] + [(1 - first) / n] * n


def src_rows(col):
    per = sorted(d[col].unique())
    piv = d.pivot_table(index="source", columns=col, aggfunc="size", fill_value=0)
    piv = piv.reindex([s for s in ORDER if s in piv.index])
    rows = [[i] + [fmt(piv.loc[i, p]) for p in per] + [fmt(piv.loc[i].sum())] for i in piv.index]
    rows.append(["Grand Total"] + [fmt(piv[p].sum()) for p in per] + [fmt(piv.values.sum())])
    return per, rows


cy_sper, cy_src = src_rows("CY")
fy_sper, fy_src = src_rows("FY")

FIG_W = 17.5
FIG_H = (len(cy_src) + 1) * ROW + 4.3
fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor="white")
fig.suptitle("Website Registrations — How Did You Find Us — Calendar Year vs Financial Year",
             fontsize=20, fontweight="bold", color=HDR, x=0.012, ha="left", y=0.975)
fig.text(0.012, 1 - 1.05 / FIG_H,
         "Source: aol_website_rebuilt.csv   |   "
         "Website = host artofliving.org   |   Status = Registered + Completed   |   "
         "Bucketed by course_event_start_date   |   Raw counts",
         fontsize=10, color="#5a6a7d", ha="left")

TOP = 1 - 1.75 / FIG_H


def place(x0, x1, y_top, nrows):
    h = nrows * ROW / FIG_H
    return fig.add_axes([x0, y_top - h, x1 - x0, h])


draw(place(0.012, 0.487, TOP, len(cy_src) + 1),
     "Calendar Year",
     ["Source"] + cy_sper + ["Total"], cy_src, widths(0.40, len(cy_sper) + 1))
draw(place(0.523, 0.988, TOP, len(fy_src) + 1),
     "Financial Year",
     ["Source"] + fy_sper + ["Total"], fy_src, widths(0.40, len(fy_sper) + 1))

fig.text(0.012, 0.35 / FIG_H,
         "Code 10 now carries its label in staging (Through another Art of Living Program); the inference is retired.\n"
         "Periods are course start dates: 743 courses start after the 10-Jul-2026 pull date (last: Feb-2029). CY2023 / FY 2023-24 begin at the extract floor of 01-Apr-2023.\n"
         "Source capture began Feb-2024, so courses starting in CY2023 / FY 2023-24 are overwhelmingly No Source.\n"
         
         "Universe: artofliving.org only. The upstream extract now contains no artofliving.online rows at all.",
         fontsize=9, color="#5a6a7d", ha="left", va="bottom", linespacing=1.7)

fig.savefig(PNG, dpi=150, facecolor="white")
print(f"saved {PNG}")
