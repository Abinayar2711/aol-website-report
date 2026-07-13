"""Streamlit website-registrations report.

Page 1 mirrors the boss's WhatsApp sheet: Program Type, How Did You Find Us, and the
Source-bucket summaries. Below that: a category-composition drill-down (which raw tags
and event names were summed into each of the 17 categories) and a source-bucket-by-FY cut.

Run:  streamlit run app.py
"""
import sys
sys.path.insert(0, ".")
import pandas as pd
import streamlit as st
from category_map import categorise, website_rows, CATEGORIES

st.set_page_config(page_title="Website Registrations Report", layout="wide",
                   page_icon="📈", initial_sidebar_state="collapsed")

# ---- Look & feel -----------------------------------------------------------------
# Ink is INHERITED from the active Streamlit theme, never hardcoded: the browser's
# prefers-color-scheme and Streamlit's theme are independent, so a media query here
# would paint white text on a light page whenever the two disagree. Surfaces are
# translucent gray for the same reason. Only the accent (blue, categorical slot 1)
# is a fixed hex — it clears contrast on both the light and dark surfaces.
CSS = """
<style>
:root {
  --surface-1: rgba(128,128,128,0.06);
  --hairline: rgba(128,128,128,0.28);
  --accent: #3987e5;
}
.block-container { padding-top: 2.2rem; max-width: 1400px; }

/* Header band */
.hdr {
  border-left: 4px solid var(--accent);
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  padding: 1.1rem 1.3rem;
  margin-bottom: 1.1rem;
}
.hdr h1 {
  font-size: 1.65rem; font-weight: 650; letter-spacing: -0.01em;
  margin: 0 0 0.25rem 0; padding: 0;
}
.hdr p { opacity: 0.75; font-size: 0.86rem; margin: 0; line-height: 1.5; }

/* KPI tiles */
.kpis { display: flex; gap: 0.75rem; margin: 0.2rem 0 1.4rem 0; flex-wrap: wrap; }
.kpi {
  flex: 1 1 180px; background: var(--surface-1);
  border: 1px solid var(--hairline); border-radius: 10px;
  padding: 0.85rem 1rem;
}
.kpi .lbl {
  opacity: 0.6; font-size: 0.72rem; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 0.3rem;
}
/* Proportional figures at display size; tabular is for columns, not heroes. */
.kpi .val { font-size: 1.55rem; font-weight: 650; line-height: 1.15; }
.kpi.hero .val { font-size: 2.5rem; }
.kpi.hero { border-left: 4px solid var(--accent); }
.kpi .sub { opacity: 0.7; font-size: 0.78rem; margin-top: 0.2rem; }

/* Section headers */
.sec {
  display: flex; align-items: center; gap: 0.55rem;
  margin: 0.2rem 0 0.6rem 0;
}
.sec .bar { width: 3px; height: 1.05rem; background: var(--accent); border-radius: 2px; }
.sec .ttl { font-size: 1.02rem; font-weight: 650; letter-spacing: -0.005em; }
.sec .cnt {
  opacity: 0.6; font-size: 0.78rem; font-weight: 500;
  font-variant-numeric: tabular-nums;
}

/* Tables: hairline ring, tabular figures so number columns align */
[data-testid="stDataFrame"] {
  border: 1px solid var(--hairline); border-radius: 8px; overflow: hidden;
}
[data-testid="stDataFrame"] * { font-variant-numeric: tabular-nums; }

/* Expanders in the drill-down */
[data-testid="stExpander"] details {
  border: 1px solid var(--hairline); border-radius: 8px; background: var(--surface-1);
}
[data-testid="stExpander"] summary:hover { color: var(--accent); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def section(title, count=None):
    cnt = f'<span class="cnt">{count}</span>' if count else ""
    st.markdown(f'<div class="sec"><span class="bar"></span>'
                f'<span class="ttl">{title}</span>{cnt}</div>', unsafe_allow_html=True)

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
BUCKET_ORDER = ["Teacher / Friends / Other AOL Programs",
                "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
                "No Source Captured"]


@st.cache_data
def load():
    d = website_rows()
    d["category"] = categorise(d)
    d["source"] = d.how_did_you_find_us_label.fillna("No Source").replace("Select", "No Source")
    d["bucket"] = d.source.map(BUCKET)
    return d


d = load()

st.markdown(
    '<div class="hdr">'
    '<h1>Website Registrations Report</h1>'
    '<p>Registrations captured on <b>artofliving.org</b>, bucketed by course start date.<br>'
    'Source: aol_website_rebuilt.csv</p>'
    '</div>', unsafe_allow_html=True)

periods = ["All periods"] + sorted(d.FY.unique())
period = st.selectbox("Financial Year", periods, index=periods.index("FY 2025-26")
                      if "FY 2025-26" in periods else 0)
view = d if period == "All periods" else d[d.FY == period]
TOTAL = len(view)

pct = lambda v: f"{v / TOTAL * 100:.2f}%" if TOTAL else "0.00%"

# ---- KPI row ---------------------------------------------------------------------
_cat = view.groupby("category").size().sort_values(ascending=False)
# "No Source" would win this outright and say nothing — the headline is the top
# source people actually told us about. Its own share gets its own tile below.
_src = (view[view.source != "No Source"].groupby("source").size()
        .sort_values(ascending=False))
_mk = int((view.bucket == "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)").sum())
_ns = int((view.bucket == "No Source Captured").sum())

def kpi(label, value, sub="", hero=False):
    return (f'<div class="kpi{" hero" if hero else ""}"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div><div class="sub">{sub}</div></div>')

st.markdown(
    '<div class="kpis">'
    + kpi("Total registrations", f"{TOTAL:,}", period, hero=True)
    + kpi("Top program", _cat.index[0] if len(_cat) else "—",
          f"{int(_cat.iloc[0]):,} regs · {pct(_cat.iloc[0])}" if len(_cat) else "")
    + kpi("Top captured source", _src.index[0] if len(_src) else "—",
          f"{int(_src.iloc[0]):,} regs · {pct(_src.iloc[0])}" if len(_src) else "")
    + kpi("Marketing channels", pct(_mk), f"{_mk:,} registrations")
    + kpi("No source captured", pct(_ns), f"{_ns:,} registrations")
    + '</div>', unsafe_allow_html=True)

# ---- Page 1: the WhatsApp layout -------------------------------------------------
left, right = st.columns([1, 1])

with left:
    section("Program Type", f"{len(_cat[_cat > 0])} categories")
    prog = (view.groupby("category").size().reindex(CATEGORIES).fillna(0).astype(int)
            .sort_values(ascending=False))
    prog = prog[prog > 0]
    pt = pd.DataFrame({"Program Type": prog.index,
                       "Registration Count": prog.values,
                       "% of Total Reg": [pct(v) for v in prog.values]})
    pt.loc[len(pt)] = ["Grand Total", int(prog.sum()), ""]
    st.dataframe(pt, hide_index=True, use_container_width=True,
                 column_config={"Registration Count": st.column_config.NumberColumn(format="%d")})

with right:
    section("How Did You Find Us")
    src = view.groupby("source").size().reindex(SRC_RANK).fillna(0).astype(int)
    src = src[src > 0]
    sd = pd.DataFrame({"How did you find us": src.index, "Registration Count": src.values})
    sd.loc[len(sd)] = ["Grand Total", int(src.sum())]
    st.dataframe(sd, hide_index=True, use_container_width=True,
                 column_config={"Registration Count": st.column_config.NumberColumn(format="%d")})

    section("Source Buckets")
    buck = view.groupby("bucket").size().reindex(BUCKET_ORDER).fillna(0).astype(int)
    bd = pd.DataFrame({"Source": BUCKET_ORDER,
                       "Reg.": buck.values,
                       "% of Website": [pct(v) for v in buck.values]})
    bd.loc[len(bd)] = ["Total", int(buck.sum()), "100.00%"]
    st.dataframe(bd, hide_index=True, use_container_width=True,
                 column_config={"Reg.": st.column_config.NumberColumn(format="%d")})

st.divider()

# ---- Below: source buckets by FY -------------------------------------------------
section("Source Buckets by Financial Year", "all periods")
bf = (d.pivot_table(index="bucket", columns="FY", aggfunc="size", fill_value=0)
      .reindex(BUCKET_ORDER).fillna(0).astype(int))
bf["Total"] = bf.sum(axis=1)
st.dataframe(bf, use_container_width=True)

# ---- Below: category composition drill-down --------------------------------------
section("Category composition — what got summed together", period)
st.caption("Each of the 17 categories is a rollup of one or more raw tags / event names. "
           "Expand a category to see exactly which events were added into it.")
comp = (view.groupby(["category", "tag", "event_name_en_gb"]).size()
        .reset_index(name="Registrations"))
cat_totals = view.groupby("category").size().sort_values(ascending=False)
for cat in cat_totals.index:
    sub = comp[comp.category == cat].sort_values("Registrations", ascending=False)
    tags = ", ".join(sorted(sub.tag.unique()))
    with st.expander(f"{cat} — {int(cat_totals[cat]):,}   ·   tags: {tags}"):
        st.dataframe(sub[["tag", "event_name_en_gb", "Registrations"]]
                     .rename(columns={"tag": "Raw tag", "event_name_en_gb": "Event name"}),
                     hide_index=True, use_container_width=True,
                     column_config={"Registrations": st.column_config.NumberColumn(format="%d")})
