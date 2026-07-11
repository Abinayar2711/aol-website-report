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

st.set_page_config(page_title="Website Registrations Report", layout="wide")

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

st.title("Website Registrations Report")

periods = ["All periods"] + sorted(d.FY.unique())
period = st.selectbox("Financial Year", periods, index=periods.index("FY 2025-26")
                      if "FY 2025-26" in periods else 0)
view = d if period == "All periods" else d[d.FY == period]
TOTAL = len(view)

st.caption(f"Source: aol_website_rebuilt.csv  ·  Bucketed by course start date  ·  "
           f"Website = host artofliving.org  ·  {period}  ·  Total registrations: {TOTAL:,}")

pct = lambda v: f"{v / TOTAL * 100:.2f}%" if TOTAL else "0.00%"

# ---- Page 1: the WhatsApp layout -------------------------------------------------
left, right = st.columns([1, 1])

with left:
    st.subheader("Program Type")
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
    st.subheader("How Did You Find Us")
    src = view.groupby("source").size().reindex(SRC_RANK).fillna(0).astype(int)
    src = src[src > 0]
    sd = pd.DataFrame({"How did you find us": src.index, "Registration Count": src.values})
    sd.loc[len(sd)] = ["Grand Total", int(src.sum())]
    st.dataframe(sd, hide_index=True, use_container_width=True,
                 column_config={"Registration Count": st.column_config.NumberColumn(format="%d")})

    st.subheader("Source Buckets")
    buck = view.groupby("bucket").size().reindex(BUCKET_ORDER).fillna(0).astype(int)
    bd = pd.DataFrame({"Source": BUCKET_ORDER,
                       "Reg.": buck.values,
                       "% of Website": [pct(v) for v in buck.values]})
    bd.loc[len(bd)] = ["Total", int(buck.sum()), "100.00%"]
    st.dataframe(bd, hide_index=True, use_container_width=True,
                 column_config={"Reg.": st.column_config.NumberColumn(format="%d")})

st.divider()

# ---- Below: source buckets by FY -------------------------------------------------
st.subheader("Source Buckets by Financial Year")
bf = (d.pivot_table(index="bucket", columns="FY", aggfunc="size", fill_value=0)
      .reindex(BUCKET_ORDER).fillna(0).astype(int))
bf["Total"] = bf.sum(axis=1)
st.dataframe(bf, use_container_width=True)

# ---- Below: category composition drill-down --------------------------------------
st.subheader("Category composition — what got summed together")
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
