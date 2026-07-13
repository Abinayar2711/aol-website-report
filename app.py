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

# UPDATE THIS whenever aol_website_rebuilt.csv is rebuilt.
# It cannot be read from the file's mtime: git does not preserve modification times, so on
# Streamlit Cloud the CSV carries the DEPLOY timestamp and the page would confidently show
# today's date on stale data. An explicit constant is the only honest option.
# CiviCRM participant details extracted 10 Jul 2026; base view_pax extract 11 Jul 2026.
DATA_AS_OF = "10–11 Jul 2026"

# ---- Look & feel -----------------------------------------------------------------
# Ink is INHERITED from the active Streamlit theme, never hardcoded: the browser's
# prefers-color-scheme and Streamlit's theme are independent, so a media query here
# would paint white text on a light page whenever the two disagree. Surfaces are
# translucent gray for the same reason. Only the accent (blue, categorical slot 1)
# is a fixed hex — it clears contrast on both the light and dark surfaces.
CSS = """
<style>
:root {
  --surface-1: rgba(128,128,128,0.055);
  --surface-2: rgba(128,128,128,0.10);
  --hairline: rgba(128,128,128,0.24);
  --accent: #3987e5;
  /* Categorical slots 1-2, validated for CVD + contrast in BOTH modes (dE 95).
     No Source is deliberately gray: it encodes an absence, not a third category. */
  --c-referral: #3987e5;
  --c-marketing: #d9703f;
  --c-nosource: rgba(128,128,128,0.55);
}
.block-container { padding-top: 1.6rem; max-width: 1360px; }

/* Header band */
.hdr {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-left: 4px solid var(--accent);
  border-radius: 12px;
  padding: 1.3rem 1.5rem;
  margin-bottom: 1.3rem;
}
.hdr h1 {
  font-size: 1.85rem; font-weight: 700; letter-spacing: -0.02em;
  margin: 0 0 0.3rem 0; padding: 0; line-height: 1.15;
}
.hdr p { opacity: 0.7; font-size: 0.92rem; margin: 0; line-height: 1.55; }
/* Data-freshness badge: readers must not have to guess how old the numbers are. */
.hdr .stamp {
  display: inline-block; background: var(--surface-2); border: 1px solid var(--hairline);
  border-radius: 999px; padding: 0.08rem 0.6rem;
  font-size: 0.78rem; font-weight: 650; opacity: 0.95;
}

/* KPI tiles. Grid, not flex-wrap: every tile gets the same width AND the same height, so a
   long value like "Reference from a friend" wrapping to two lines can no longer leave the
   row ragged. Content is pinned top/bottom inside each tile. */
.kpis {
  display: grid; grid-template-columns: 1.35fr repeat(3, 1fr);
  gap: 0.7rem; margin: 0.4rem 0 1.6rem 0;
}
.kpi {
  background: var(--surface-1); border: 1px solid var(--hairline);
  border-radius: 12px; padding: 0.95rem 1.1rem;
  display: flex; flex-direction: column; justify-content: space-between;
  min-height: 118px;
}
.kpi .lbl {
  opacity: 0.55; font-size: 0.68rem; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
}
/* Proportional figures at display size; tabular is for columns, not heroes. */
.kpi .val { font-size: 1.45rem; font-weight: 700; line-height: 1.2; margin: 0.35rem 0 0.2rem 0; }
.kpi .val.sm { font-size: 1.12rem; }          /* long text values don't blow the tile out */
.kpi.hero { border-left: 4px solid var(--accent); background: var(--surface-2); }
.kpi.hero .val { font-size: 2.6rem; letter-spacing: -0.02em; }
.kpi .sub { opacity: 0.6; font-size: 0.76rem; }

/* Source-mix share bar: one 100% stacked row. A 2px surface gap separates the segments so
   they read as distinct marks; every segment is directly labelled, so identity never
   depends on colour alone. */
.mixwrap { margin: 0 0 1.7rem 0; }
.mix { display: flex; height: 30px; gap: 2px; margin-bottom: 0.55rem; }
.mix span {
  display: flex; align-items: center; justify-content: center;
  font-size: 0.74rem; font-weight: 700; color: #fff; overflow: hidden; white-space: nowrap;
}
.mix span:first-child { border-radius: 5px 0 0 5px; }
.mix span:last-child  { border-radius: 0 5px 5px 0; }
/* The no-source segment is a low-chroma gray by design, so it cannot carry white text.
   Inherit the theme's ink instead — readable on the gray in both light and dark. */
.mix span.muted { color: inherit; opacity: 0.95; }
.key { display: flex; gap: 1.4rem; flex-wrap: wrap; font-size: 0.8rem; }
.key i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; margin-right: 0.4rem; }
.key b { font-weight: 650; font-variant-numeric: tabular-nums; }
.key em { opacity: 0.6; font-style: normal; }

/* Section headers. A rule above each one does the separating, so sections read as
   distinct blocks rather than one continuous column of tables. */
.sec {
  display: flex; align-items: baseline; gap: 0.6rem;
  margin: 2.4rem 0 0.9rem 0;
  padding-top: 1.1rem;
  border-top: 1px solid var(--hairline);
}
.sec.tight { margin-top: 1.6rem; }          /* for a section that follows st.divider() */
.sec .bar {
  width: 4px; height: 1.35rem; background: var(--accent);
  border-radius: 2px; align-self: center;
}
.sec .ttl { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.015em; }
.sec .cnt {
  opacity: 0.65; font-size: 0.92rem; font-weight: 500;
  font-variant-numeric: tabular-nums;
}
/* Breathing room under each table so the next section isn't crowded. */
[data-testid="stDataFrame"] { margin-bottom: 0.9rem; }

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


def section(title, count=None, tight=False):
    cnt = f'<span class="cnt">{count}</span>' if count else ""
    st.markdown(f'<div class="sec{" tight" if tight else ""}"><span class="bar"></span>'
                f'<span class="ttl">{title}</span>{cnt}</div>', unsafe_allow_html=True)


def fit(df):
    """Height that shows every row, Grand Total included. Streamlit's default is a fixed ~400px
    that does not grow with baseFontSize, so at 18px the tables silently scroll and the last
    rows get cut off. Row height is ~40px at this font; the +12 keeps the last row off the edge."""
    return (len(df) + 1) * 40 + 12

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
    f'Source: aol_website_rebuilt.csv &nbsp;·&nbsp; '
    f'<span class="stamp">Data as of {DATA_AS_OF}</span></p>'
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
    # Long text values get a smaller class rather than wrapping the tile out of alignment.
    cls = "val sm" if not hero and len(str(value)) > 14 else "val"
    return (f'<div class="kpi{" hero" if hero else ""}"><div class="lbl">{label}</div>'
            f'<div class="{cls}">{value}</div><div class="sub">{sub}</div></div>')

st.markdown(
    '<div class="kpis">'
    + kpi("Total registrations", f"{TOTAL:,}", period, hero=True)
    + kpi("Top program", _cat.index[0] if len(_cat) else "—",
          f"{int(_cat.iloc[0]):,} regs · {pct(_cat.iloc[0])}" if len(_cat) else "")
    + kpi("Top captured source", _src.index[0] if len(_src) else "—",
          f"{int(_src.iloc[0]):,} regs · {pct(_src.iloc[0])}" if len(_src) else "")
    + kpi("No source captured", pct(_ns), f"{_ns:,} registrations")
    + '</div>', unsafe_allow_html=True)

# ---- Source-mix share bar (same three bucket counts as the table below) -------------
_tf = int((view.bucket == "Teacher / Friends / Other AOL Programs").sum())
_mix = [("Teacher / Friends / Other AOL Programs", _tf, "var(--c-referral)", ""),
        ("Marketing Channels", _mk, "var(--c-marketing)", ""),
        ("No Source Captured", _ns, "var(--c-nosource)", " muted")]
if TOTAL:
    bars = "".join(
        f'<span class="{m.strip()}" style="width:{v / TOTAL * 100:.2f}%;background:{c}">'
        f'{pct(v) if v / TOTAL > 0.06 else ""}</span>' for _, v, c, m in _mix)
    keys = "".join(
        f'<span><i style="background:{c}"></i><b>{v:,}</b> <em>{lbl} · {pct(v)}</em></span>'
        for lbl, v, c, _m in _mix)
    st.markdown(f'<div class="mixwrap"><div class="mix">{bars}</div>'
                f'<div class="key">{keys}</div></div>', unsafe_allow_html=True)

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
    st.dataframe(pt, hide_index=True, use_container_width=True, height=fit(pt),
                 column_config={"Registration Count": st.column_config.NumberColumn(format="%d")})

with right:
    section("How Did You Find Us")
    src = view.groupby("source").size().reindex(SRC_RANK).fillna(0).astype(int)
    src = src[src > 0]
    sd = pd.DataFrame({"How did you find us": src.index, "Registration Count": src.values})
    sd.loc[len(sd)] = ["Grand Total", int(src.sum())]
    st.dataframe(sd, hide_index=True, use_container_width=True, height=fit(sd),
                 column_config={"Registration Count": st.column_config.NumberColumn(format="%d")})

    section("Source Buckets")
    buck = view.groupby("bucket").size().reindex(BUCKET_ORDER).fillna(0).astype(int)
    bd = pd.DataFrame({"Source": BUCKET_ORDER,
                       "Reg.": buck.values,
                       "% of Website": [pct(v) for v in buck.values]})
    bd.loc[len(bd)] = ["Total", int(buck.sum()), "100.00%"]
    st.dataframe(bd, hide_index=True, use_container_width=True, height=fit(bd),
                 column_config={"Reg.": st.column_config.NumberColumn(format="%d")})

st.divider()

# ---- Below: source buckets by FY -------------------------------------------------
section("Source Buckets by Financial Year", "all periods", tight=True)
bf = (d.pivot_table(index="bucket", columns="FY", aggfunc="size", fill_value=0)
      .reindex(BUCKET_ORDER).fillna(0).astype(int))
bf["Total"] = bf.sum(axis=1)
bf.loc["Total (all sources)"] = bf.sum(axis=0)   # per-FY totals; the column totals were already there
st.dataframe(bf, use_container_width=True, height=fit(bf),
             column_config={c: st.column_config.NumberColumn(format="%d") for c in bf.columns})
st.caption("Each column totals that financial year; the Total column totals each source bucket "
           "across all years. FY 2023-24 source data is 96% unset — see the caveat before comparing "
           "source mix across years.")

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
