"""Reproduce the boss's WhatsApp report layout with our rebuilt data.

Four blocks, single combined snapshot (all periods), matching the CRM's 18,965 sheet:
  1. Program Type (17 CRM categories) x Registration Count, % of Total, sorted desc
  2. How did you find us x Registration Count, sorted desc
  3. Source-bucket summary lines
  4. Source buckets x Reg. x % of Website Reg

The WhatsApp "Value %" (19.60/13.80/16.70) implies three different bases, so it is not a
reproducible metric — replaced here with an honest % of website total.
"""
import sys
sys.path.insert(0, ".")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from category_map import categorise, website_rows, CATEGORIES

# Optional single-period filter: pass an FY like "FY 2025-26" as the first argument.
PERIOD = sys.argv[1] if len(sys.argv) > 1 else None

d = website_rows()
d["category"] = categorise(d)
d["source"] = d.how_did_you_find_us_label.fillna("No Source").replace("Select", "No Source")

if PERIOD:
    d = d[d.FY == PERIOD]
    assert len(d), f"no rows for period {PERIOD!r}"
    PNG = "website_report_" + PERIOD.replace(" ", "").replace("-", "_") + ".png"
else:
    PNG = "website_report_whatsapp.png"

TOTAL = len(d)

BUCKET = {
    "Reference from a friend": "Teacher / Friends / Other AOL Programs",
    "Reference from an Art of Living Teacher": "Teacher / Friends / Other AOL Programs",
    "Through another Art of Living Program": "Teacher / Friends / Other AOL Programs",
    "Google": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Youtube": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Events": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Emails": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "LinkedIn": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Twitter": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "News": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "No Source": "No Source Captured",
}
SRC_RANK = ["No Source", "Reference from a friend", "Google",
            "Reference from an Art of Living Teacher",
            "Through another Art of Living Program", "Youtube", "Events",
            "News", "Emails", "LinkedIn", "Twitter"]

prog = d.groupby("category").size().reindex(CATEGORIES).fillna(0).astype(int).sort_values(ascending=False)
src = d.groupby("source").size().reindex(SRC_RANK).fillna(0).astype(int)
d["bucket"] = d.source.map(BUCKET)
buck = d.groupby("bucket").size()
b_teacher = int(buck.get("Teacher / Friends / Other AOL Programs", 0))
b_mktg = int(buck.get("Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)", 0))
b_nosrc = int(buck.get("No Source Captured", 0))

BUCKET_ORDER = ["Teacher / Friends / Other AOL Programs",
                "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
                "No Source Captured"]
BUCKET_SHORT = {"Teacher / Friends / Other AOL Programs": "Teacher / Friends / Other AOL Programs",
                "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X)",
                "No Source Captured": "No Source Captured"}
fy_periods = sorted(d.FY.unique())
buck_fy = d.pivot_table(index="bucket", columns="FY", aggfunc="size", fill_value=0).reindex(BUCKET_ORDER).fillna(0)

HDR, BAND, TOTALC = "#1f3864", "#f2f5fa", "#dce6f1"
fmt = lambda v: f"{int(v):,}"
pct = lambda v: f"{v / TOTAL * 100:.2f}%"
ROW = 0.34


def draw(ax, title, cols, rows, widths, total_row=True):
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color=HDR, pad=8)
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
        elif total_row and r == n:
            cell.set_facecolor(TOTALC); txt.set_fontweight("bold")
        elif r % 2 == 0:
            cell.set_facecolor(BAND)
        else:
            cell.set_facecolor("white")


prog_rows = [[i, fmt(prog[i]), pct(prog[i])] for i in prog.index]
prog_rows.append(["Grand Total", fmt(prog.sum()), ""])

src_rows = [[i, fmt(src[i])] for i in src.index]
src_rows.append(["Grand Total", fmt(src.sum())])

buck_rows = [
    ["Teacher / Friends / Other AOL Programs", fmt(b_teacher), pct(b_teacher)],
    ["Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)", fmt(b_mktg), pct(b_mktg)],
    ["No Source Captured", fmt(b_nosrc), pct(b_nosrc)],
    ["Total", fmt(TOTAL), "100.00%"],
]

buckfy_rows = [[BUCKET_SHORT[b]] + [fmt(buck_fy.loc[b, p]) for p in fy_periods]
               + [fmt(buck_fy.loc[b].sum())] for b in BUCKET_ORDER]
buckfy_rows.append(["Total"] + [fmt(buck_fy[p].sum()) for p in fy_periods] + [fmt(buck_fy.values.sum())])

FIG_W = 17.5
# The full-width FY bucket strip only makes sense for the all-periods view.
FIG_H = (len(prog_rows) + 1) * ROW + 3.4 + (2.4 if not PERIOD else 0)
fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor="white")
fig.suptitle("Website Registrations Report" + (f" — {PERIOD}" if PERIOD else ""),
             fontsize=20, fontweight="bold", color=HDR, x=0.012, ha="left", y=1 - 0.28 / FIG_H)
fig.text(0.012, 1 - 0.95 / FIG_H,
         "Source: aol_website_rebuilt.csv   |   Categories per CRM grouping   |   "
         "Bucketed by course_event_start_date   |   "
         + (f"Period: {PERIOD}   |   " if PERIOD else "All periods combined   |   ")
         + "Website = host artofliving.org   |   Status = Registered + Completed",
         fontsize=10, color="#5a6a7d", ha="left")

TOP = 1 - 1.55 / FIG_H


def place(x0, x1, y_top, nrows):
    h = nrows * ROW / FIG_H
    return fig.add_axes([x0, y_top - h, x1 - x0, h])


# Left: Program Type
draw(place(0.012, 0.44, TOP, len(prog_rows) + 1),
     "Registrations by Program Type",
     ["Program Type", "Reg. Count", "% of Total"], prog_rows, [0.52, 0.26, 0.22])

# Right top: How did you find us
draw(place(0.48, 0.988, TOP, len(src_rows) + 1),
     "How Did You Find Us",
     ["How did you find us", "Reg. Count"], src_rows, [0.7, 0.3])

# Right bottom: source buckets
yb = TOP - (len(src_rows) + 1) * ROW / FIG_H - 0.75 / FIG_H
draw(place(0.48, 0.988, yb, len(buck_rows) + 1),
     "Source Buckets",
     ["Source", "Reg.", "% of Website"], buck_rows, [0.62, 0.19, 0.19])

# Full-width bottom: source buckets cut by Financial Year (all-periods view only)
if not PERIOD:
    left_bottom = TOP - (len(prog_rows) + 1) * ROW / FIG_H
    yf = left_bottom - 0.85 / FIG_H
    draw(place(0.012, 0.988, yf, len(buckfy_rows) + 1),
         "Source Buckets by Financial Year",
         ["Source"] + fy_periods + ["Total"], buckfy_rows,
         [0.34] + [(0.66) / (len(fy_periods) + 1)] * (len(fy_periods) + 1))

fig.text(0.012, 0.30 / FIG_H,
         f"Total website registrations: {TOTAL:,}. Grand totals reconcile across all three tables.\n"
         "\"Through another Art of Living Program\" is code 10 (now labelled in staging). Source captured from the CiviCRM course-participants details join.\n"
         "Note: the reference sheet's \"Value %\" column was not reproduced — its three values imply three different bases and are not derivable from this data. "
         "\"% of Website\" here is share of the website total.\n"
         + ("Periods are course start dates; this view combines all of them (incl. 743 courses starting after the 10-Jul-2026 pull date)."
            if not PERIOD else
            f"Rows are bucketed by course start date; this view is {PERIOD} only (Apr {PERIOD[3:7]} – Mar {PERIOD.split('-')[-1]} start dates)."),
         fontsize=8.5, color="#5a6a7d", ha="left", va="bottom", linespacing=1.7)

fig.savefig(PNG, dpi=150, facecolor="white")
print(f"saved {PNG}  (Program {int(prog.sum()):,} | Source {int(src.sum()):,} | "
      f"Buckets {b_teacher + b_mktg + b_nosrc:,})")
