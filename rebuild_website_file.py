"""Rebuild the website extract from the base file + fresh CiviCRM details.

Join chain, established empirically 2026-07-10:
  base.global_participant_id minus 'AOLT'  ==  civicrm_participant.id   (66,261/66,261)
  details.entity_id                        ==  civicrm_participant.event_id
  -> details has no participant id, so the only reachable key is (event_id, contact_id).

That key is NOT unique in details (up to 136 rows). Collapse rules confirmed with Ishan:
  - prefer any real answer (how_did_you_find_us > 0) over 0/Select
  - among the remaining candidates, the highest `id` (latest record) wins
  - the answer is per (contact, event); sibling registrations inherit it
  - rows with no details match get No Source; referal_site always comes from the base
"""
import pandas as pd

NEW = "1748_new/"
BASE = "TAOL_View_pax_course_start.csv"
DETAILS = NEW + "civicrm_course_participants_details_202607101831.csv"
TAGS = "query_result_with_tags_and_referral.csv"   # full extract; tag is a 1:1 function of event_name_en_gb
OUT = "aol_website_rebuilt.csv"

LABELS = {0: "Select", 1: "Google", 2: "Youtube", 3: "Twitter", 4: "LinkedIn",
          5: "Emails", 6: "Events", 7: "News", 8: "Reference from a friend",
          9: "Reference from an Art of Living Teacher",
          10: "Through another Art of Living Program"}


def fy_of(s):
    q = s.dt.to_period("Q-MAR").dt.qyear
    return "FY " + (q - 1).astype(str) + "-" + q.astype(str).str[-2:]


b = pd.read_csv(BASE, dtype=str).drop_duplicates()
b["eid"] = b.global_event_id.str[4:]
b["cid"] = b.global_contact_id.str[4:]

d = pd.read_csv(DETAILS, dtype=str)
d["hd"] = d.how_did_you_find_us.fillna("0").astype(int)
d["idn"] = d.id.astype(int)

# Collapse: real answer beats 0; then latest id. sort_values puts the winner first.
d = d.sort_values(["hd", "idn"], ascending=[False, False], kind="mergesort")
win = d.drop_duplicates(subset=["entity_id", "contact_id"], keep="first")
assert not win.duplicated(["entity_id", "contact_id"]).any()

m = b.merge(win[["entity_id", "contact_id", "hd"]],
            left_on=["eid", "cid"], right_on=["entity_id", "contact_id"],
            how="left", validate="m:1")
assert len(m) == len(b), f"fan-out: {len(m)} vs {len(b)}"

m["how_did_you_find_us"] = m.hd.fillna(0).astype(int)
m["how_did_you_find_us_label"] = m.how_did_you_find_us.map(LABELS)
s = pd.to_datetime(m.course_event_start_date)
m["CY"] = "CY" + s.dt.year.astype(str)
m["FY"] = fy_of(s)

# Tags come from the notebook's tagging step. tag is a 1:1 function of event_name_en_gb,
# so join on the event name (robust to the per-participant extract being regenerated).
t = pd.read_csv(TAGS, dtype=str, usecols=["event_name_en_gb", "course_match_key",
                                          "tag", "tag_status"])
t = t.dropna(subset=["event_name_en_gb"]).drop_duplicates("event_name_en_gb")
m = m.merge(t, on="event_name_en_gb", how="left", validate="m:1")

# Fallback for event names the big extract never tagged (e.g. Speed Reading appears only in
# Registered rows): use the canonical grouping table (name_en_gb -> tag), matching on the name
# after stripping a leading "Online ".
miss = m.tag.isna()
if miss.any():
    grp = pd.read_csv("coursetype groupings types - website_grouping_tags.csv", dtype=str)
    gmap = dict(zip(grp.name_en_gb, grp.tag))
    fill = m.loc[miss, "event_name_en_gb"].str.replace(r"^Online ", "", regex=True).map(gmap)
    m.loc[miss, "tag"] = fill.values
    m.loc[miss & m.tag_status.isna(), "tag_status"] = "grouping_fallback"
assert m.tag.notna().all(), f"{m.tag.isna().sum()} rows still have no tag: " \
    f"{m.loc[m.tag.isna(), 'event_name_en_gb'].unique()[:5]}"

cols = ["global_participant_id", "global_contact_id", "global_event_id",
        "course_event_start_date", "event_name_en_gb", "referal_site",
        "participant_status", "course_match_key", "tag", "tag_status", "CY", "FY",
        "how_did_you_find_us", "how_did_you_find_us_label"]
m[cols].to_csv(OUT, index=False)

print(f"base rows {len(b):,} -> output rows {len(m):,} (no fan-out)")
print(f"no details match (forced to Select): {m.hd.isna().sum():,}")
print(f"\nlabel spread:\n{m.how_did_you_find_us_label.value_counts().to_string()}")
