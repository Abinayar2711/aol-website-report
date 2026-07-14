import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

WEB = "aol_website_rebuilt.csv"
PNG = "website_report_CY_FY_tag.png"
KEEP = ["Registered", "Completed"]

d = pd.read_csv(WEB, dtype=str).drop_duplicates()
d = d[d.participant_status.isin(KEEP)]
# Host match, not substring: .online carries the marketing site in a referrer= param.
host = d.referal_site.str.extract(r"^https?://([^/:]+)", expand=False).str.lower()
d = d[host.str.match(r"(.*\.)?artofliving\.org$", na=False)]

RENAME = {"Institutional": "HP_Institutional", "combine": "HP+Sahaj Combo", "NO TAG": "others"}
PROGRAM_ORDER = [
    "HP", "HP_Institutional", "YLTP", "HP+Sahaj Combo", "Sahaj",
    "SSY - All Programs", "SSY Challenges",
    "C&T-UY-MY-NonInstitutional", "C&T-UY-MY-Institutional",
    "C&T-PY-NonInstitutional", "C&T-PY-Institutional",
    "C&T-PY2-NonInstitutional", "C&T-PY-Special",
    "KYC-KYT", "IP repeaters", "UY_MY Upgrade",
    "DSN", "AMP", "VTP",
    "Deep Sleep", "Wellness", "Spine", "ShaktiKriya", "Blessing",
    "Eternity", "Sanyam", "KaalGyan",
    "others",
]
d["tag"] = d.tag.fillna("NO TAG").replace(RENAME)
missing = set(d.tag) - set(PROGRAM_ORDER)
assert not missing, f"tags absent from PROGRAM_ORDER: {sorted(missing)}"

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


def tag_rows(col):
    """Keep every listed program as a row, even at zero, so absences are visible."""
    per = sorted(d[col].unique())
    piv = d.pivot_table(index="tag", columns=col, aggfunc="size", fill_value=0)
    piv = piv.reindex(PROGRAM_ORDER).fillna(0)
    rows = [[i] + [fmt(piv.loc[i, p]) for p in per] + [fmt(piv.loc[i].sum())] for i in piv.index]
    rows.append(["Grand Total"] + [fmt(piv[p].sum()) for p in per] + [fmt(piv.values.sum())])
    return per, rows


cy_per, cy_tag = tag_rows("CY")
fy_per, fy_tag = tag_rows("FY")

FIG_W = 17.5
FIG_H = (len(cy_tag) + 1) * ROW + 3.6
fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor="white")
fig.suptitle("Website Registrations — Program Type — Calendar Year vs Financial Year",
             fontsize=20, fontweight="bold", color=HDR, x=0.012, ha="left", y=1 - 0.30 / FIG_H)
fig.text(0.012, 1 - 1.05 / FIG_H,
         "Source: aol_website_rebuilt.csv   |   "
         "Website = host artofliving.org   |   Status = Registered + Completed   |   "
         "Bucketed by course_event_start_date   |   Raw counts",
         fontsize=10, color="#5a6a7d", ha="left")

TOP = 1 - 1.75 / FIG_H


def place(x0, x1, y_top, nrows):
    h = nrows * ROW / FIG_H
    return fig.add_axes([x0, y_top - h, x1 - x0, h])


draw(place(0.012, 0.487, TOP, len(cy_tag) + 1),
     "Calendar Year",
     ["Program Type"] + cy_per + ["Total"], cy_tag, widths(0.36, len(cy_per) + 1))
draw(place(0.523, 0.988, TOP, len(fy_tag) + 1),
     "Financial Year",
     ["Program Type"] + fy_per + ["Total"], fy_tag, widths(0.36, len(fy_per) + 1))

fig.text(0.012, 0.35 / FIG_H,
         "Periods are course start dates: 743 courses start after the 10-Jul-2026 pull date (last: Feb-2029). CY2023 / FY 2023-24 begin at the extract floor of 01-Apr-2023.\n"
         "Programs listed with zero across all periods had no website registrations in this extract.\n"
         "Universe: artofliving.org only. The upstream extract now contains no artofliving.online rows at all.",
         fontsize=9, color="#5a6a7d", ha="left", va="bottom", linespacing=1.7)

fig.savefig(PNG, dpi=150, facecolor="white")
print(f"saved {PNG}")
