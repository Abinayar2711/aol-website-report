import sys
import pandas as pd, numpy as np

CALENDAR = "--calendar" in sys.argv

# WEB_SRC is pre-filtered to rows whose referal_site mentions artofliving.org anywhere,
# so it holds the numerator but no non-website rows. ALL_SRC supplies Sheet 1's denominator.
WEB_SRC = "aol_websitequery_result_with_tags_and_referral.csv"
ALL_SRC = "query_result_with_tags.csv"
OUT = "website_report_3CY.xlsx" if CALENDAR else "website_report_3FY.xlsx"

BASE = ["global_participant_id", "global_event_id", "registration_date",
        "referal_site", "participant_status"]


def period_of(reg):
    if CALENDAR:
        # The extract starts 2023-04-01, so CY2023 is Apr-Dec and CY2026 runs to the
        # extract date. Nothing here rescales them; the report labels them instead.
        return "CY" + reg.dt.year.astype(str)
    fy = reg.dt.to_period("Q-MAR").dt.qyear
    return "FY" + (fy - 1).astype(str).str[-2:] + "-" + fy.astype(str).str[-2:]


# Denominator. Duplicates come only from the tag file listing two course names twice,
# so deduping on BASE equals a full-row dedup — verified: it leaves global_participant_id unique.
a = pd.read_csv(ALL_SRC, dtype=str, usecols=BASE).drop_duplicates()
assert a.global_participant_id.is_unique, "ALL_SRC still duplicated after dedup on BASE"
a = a[a.participant_status.isin(["Registered", "Completed"])]
a["period"] = period_of(pd.to_datetime(a.registration_date))

# The referal.csv join fans out (its `id` is not unique) and the tag file lists two
# course names twice. Every resulting duplicate is byte-identical, so this is lossless.
d = pd.read_csv(WEB_SRC, dtype=str).drop_duplicates()

d = d[d.participant_status.isin(["Registered", "Completed"])]
d["period"] = period_of(pd.to_datetime(d.registration_date))

# Match on host, not substring. `.online` registration-portal URLs carry the marketing site
# in a `referrer=` query param, and translate.goog proxies the hostname as artofliving-org;
# both contain "artofliving.org" as a substring but neither is the site.
host = d.referal_site.str.extract(r"^https?://([^/:]+)", expand=False).str.lower()
d["is_web"] = host.str.match(r"(.*\.)?artofliving\.org$", na=False)

# code 10 has no label in staging; inferred from the reference report. Pending CRM confirmation.
code = d.how_did_you_find_us.astype(float)
lbl = d.how_did_you_find_us_label
d["source"] = np.where(code.eq(10), "Through another Art of Living Program*", lbl)
d["source"] = d.source.fillna("No Source").replace("Select", "No Source")

w = d[d.is_web]

# --- Sheet 1: website share of all registrations, by period
share = pd.DataFrame({
    "Website Registrations": w.groupby("period").size(),
    "All Registrations": a.groupby("period").size(),
})
share["Website Share %"] = (share["Website Registrations"] / share["All Registrations"] * 100).round(2)
share.loc["Grand Total"] = share.sum()
share.loc["Grand Total", "Website Share %"] = round(
    share.loc["Grand Total", "Website Registrations"] / share.loc["Grand Total", "All Registrations"] * 100, 2)

# --- Sheet 2: program type (tag) x period, with % of website total
# Upstream now emits the renamed tags directly; these remain for older extracts.
RENAME = {"Institutional": "HP_Institutional", "combine": "HP+Sahaj Combo",
          "NO TAG": "others"}
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
prog = w.assign(tag=w.tag.fillna("NO TAG").replace(RENAME)).pivot_table(
    index="tag", columns="period", aggfunc="size", fill_value=0)
prog["Total"] = prog.sum(axis=1)

missing = set(prog.index) - set(PROGRAM_ORDER)
assert not missing, f"tags absent from PROGRAM_ORDER: {sorted(missing)}"
# Keep every listed program as a row, even at zero, so absences are visible.
prog = prog.reindex(PROGRAM_ORDER).fillna(0)
for c in [c for c in prog.columns if c != "Total"]:
    prog[c + " %"] = (prog[c] / prog[c].sum() * 100).round(2)
prog["% of Total Reg"] = (prog["Total"] / prog["Total"].sum() * 100).round(2)
prog.loc["Grand Total"] = prog.sum()

# --- Sheet 3: how did you find us x period
ORDER = ["No Source", "Reference from a friend", "Google",
         "Reference from an Art of Living Teacher", "Through another Art of Living Program*", "Youtube",
         "Events", "News", "Emails", "LinkedIn", "Twitter"]
src = w.pivot_table(index="source", columns="period", aggfunc="size", fill_value=0)
src["Total"] = src.sum(axis=1)
src = src.reindex([s for s in ORDER if s in src.index])
src["% of Website Reg"] = (src["Total"] / src["Total"].sum() * 100).round(2)
src.loc["Grand Total"] = src.sum()

# --- Sheet 4: source buckets
BUCKET = {
    "Reference from an Art of Living Teacher": "Teacher / Friends / Other AOL Programs",
    "Reference from a friend": "Teacher / Friends / Other AOL Programs",
    "Through another Art of Living Program*": "Teacher / Friends / Other AOL Programs",
    "Google": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Youtube": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Events": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Emails": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "LinkedIn": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "Twitter": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "News": "Marketing Channels (YT/Google/Events/Emails/LinkedIn/X etc.)",
    "No Source": "No Source Captured",
}
b = w.assign(bucket=w.source.map(BUCKET))
buck = b.pivot_table(index="bucket", columns="period", aggfunc="size", fill_value=0)
buck["Total"] = buck.sum(axis=1)
buck["% of Website Reg"] = (buck["Total"] / buck["Total"].sum() * 100).round(2)
buck.loc["Grand Total"] = buck.sum()

with pd.ExcelWriter(OUT) as xl:
    share.to_excel(xl, "1_Website Share")
    prog.to_excel(xl, "2_Program Type")
    src.to_excel(xl, "3_How Did You Find Us")
    buck.to_excel(xl, "4_Source Buckets")

for n, t in [("WEBSITE SHARE", share), ("PROGRAM TYPE", prog),
             ("HOW DID YOU FIND US", src), ("SOURCE BUCKETS", buck)]:
    print("\n===", n, "===\n", t.to_string())
# WEB_SRC is already substring-filtered, so what we drop here is .online + translate.goog only.
print("\nExcluded (mentions artofliving.org but host does not match, all periods):")
print(host[~d.is_web].value_counts().to_string())
