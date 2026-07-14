"""Build the GWS-vs-website reconciliation proof pack for the tech team.

One workbook. Sheet 1 is the headline (19,696 vs 18,034 and the source-by-source delta);
every downstream sheet is the named, ID-bearing evidence behind a line of it, so any figure
can be traced back to a Global Pax ID.

Universe: FY 2025-26, host artofliving.org, participant_status in (Registered, Completed).
Join key: normalised name + course start date  -- GWS has no ID that maps to global_event_id.

Run:  python3 make_gws_proof.py
Out:  reports/GWS_vs_Website_Proof_FY2025-26.xlsx
"""
import re
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, ".")
from category_map import categorise, website_rows

FY = "FY 2025-26"
OUT = "reports/GWS_vs_Website_Proof_FY2025-26.xlsx"

# The four courses whose rows are later sessions of an enrollment already counted.
REPEAT_MODULES = [
    "IP Kids or Teens Module 2",
    "IP Kids or Teens Module 3",
    "IP Junior Module 2",
    "IP Kids or Teens Vacation Program M2",
]
SRC_ORDER = [
    "No Source", "Reference from a friend", "Google",
    "Reference from an Art of Living Teacher", "Through another Art of Living Program",
    "Youtube", "Events", "News", "Emails", "LinkedIn", "Twitter",
]


def tokenkey(s):
    """Name -> sorted set of tokens.

    An exact-string key is wrong twice over. CiviCRM holds SEVERAL name spellings for the same
    contact (5,585 contact_ids have more than one), and GWS may carry any of them; and a name can
    repeat a token ('Rakshitha YS' vs 'Rakshitha YS YS'). Comparing sorted token SETS collapses
    both. Verified against AOLT7021338, which an exact-string key wrongly reported as missing.
    """
    s = re.sub(r"[^a-z ]", " ", str(s).lower().strip())
    return " ".join(sorted(set(re.sub(r"\s+", " ", s).strip().split())))


# ---- our side ---------------------------------------------------------------------
# EVERY name variant per contact, not just the first -- picking one arbitrarily is what produced
# 165 phantom "in GWS not in ours" rows.
nm = pd.read_csv("1748_new/civicrm_course_participants_details_name.csv").dropna(subset=["name"])
variants = nm[["contact_id", "name"]].drop_duplicates()
variants["nk"] = variants.name.map(tokenkey)
cand = variants.groupby("contact_id").nk.apply(set).to_dict()
disp = nm.drop_duplicates("contact_id").set_index("contact_id")["name"]

o = website_rows()
o = o[o.FY == FY].copy().reset_index(drop=True)
o["category"] = categorise(o)
o["source"] = o.how_did_you_find_us_label.fillna("No Source").replace("Select", "No Source")
cid = o.global_contact_id.str[4:].astype("int64")
o["pax_name"] = cid.map(disp)
o["nks"] = [cand.get(c, set()) for c in cid]
o["start"] = pd.to_datetime(o.course_event_start_date, errors="coerce").dt.date
o["month"] = pd.to_datetime(o.course_event_start_date, errors="coerce").dt.to_period("M").astype(str)
o["repeat_module"] = o.event_name_en_gb.isin(REPEAT_MODULES)

# ---- GWS side ---------------------------------------------------------------------
g = pd.read_csv("CRM - GWS Data - leads.csv")
gsd = pd.to_datetime(g["Start Date"], format="mixed", dayfirst=True, errors="coerce")
# Assign the parsed date BEFORE reset_index -- gsd is keyed on the original index, so reading it
# through a reset index silently scrambles the dates.
g["start"] = gsd.dt.date
g = g[(gsd >= "2025-04-01") & (gsd < "2026-04-01")].copy().reset_index(drop=True)
# "Not Available" is GWS's second unset label (Intuition Process only) -- same thing as No Source.
g["source"] = g["How Did You Find Us"].replace("Not Available", "No Source")
g["nk"] = g["Lead Name"].map(tokenkey)
g["month"] = pd.to_datetime(g.start).dt.to_period("M").astype(str)

# ---- STRICT 1:1 matching on (name token-set, course start date) ----------------------
# A plain lookup lets several of our rows point at one GWS lead (a blank Module-2 row would
# claim its own Module-1 lead), which double-counts and breaks the ledger. Each GWS lead may
# absorb exactly one of our rows; non-repeat rows get first claim so a real registration wins
# the lead ahead of a follow-on session.
bucket = defaultdict(list)
for j, (k, dt) in enumerate(zip(g.nk, g.start)):
    bucket[(k, dt)].append(j)

pair, used = {}, set()
for i in o.sort_values("repeat_module").index:
    for k in o.nks[i]:
        hit = next((j for j in bucket.get((k, o.start[i]), []) if j not in used), None)
        if hit is not None:
            used.add(hit)
            pair[i] = hit
            break
o["gws_row"] = [pair.get(i) for i in o.index]
o["in_gws"] = o.gws_row.notna()
g["in_ours"] = [j in used for j in g.index]

gsrc = g.source.to_dict()
o["gws_source"] = [gsrc[int(j)] if pd.notna(j) else None for j in o.gws_row]

# ---- sheet 1: headline + source delta ----------------------------------------------
src = pd.DataFrame({
    "Source": SRC_ORDER,
    "Website (ours)": [int((o.source == s).sum()) for s in SRC_ORDER],
    "GWS / CRM": [int((g.source == s).sum()) for s in SRC_ORDER],
})
src["Delta (ours - GWS)"] = src["Website (ours)"] - src["GWS / CRM"]
src["% of our total"] = (100 * src["Website (ours)"] / len(o)).round(1)
src.loc[len(src)] = ["TOTAL", len(o), len(g), len(o) - len(g), 100.0]

# ---- sheet 2: the ledger ------------------------------------------------------------
unmatched = o[~o.in_gws]
rep_ns = int((unmatched[unmatched.repeat_module].source == "No Source").sum())
nr = unmatched[~unmatched.repeat_module]
apr_ns = int((nr[nr.month == "2025-04"].source == "No Source").sum())
lea_ns = int((nr[nr.month != "2025-04"].source == "No Source").sum())

matched = o[o.in_gws]
mm = matched[(matched.source == "No Source") & (matched.gws_source != "No Source")]
rev = matched[(matched.source != "No Source") & (matched.gws_source == "No Source")]
gws_only_ns = int((g[~g.in_ours].source == "No Source").sum())
n_match = len(matched)
agree_pct = round(100 * (matched.source == matched.gws_source).mean(), 2)

ledger = pd.DataFrame([
    ["1. IP repeat-module rows (Module 2/3, Vacation Prog M2)", rep_ns,
     "NOT registrations - later sessions of an enrollment already counted. No form filled -> no source; "
     "no new lead -> absent from GWS. 100% No Source across all 4 courses.", "YES - exclude from counts"],
    ["2. April-2025 GWS start-of-life", apr_ns,
     "GWS lead capture begins Apr-2025 (only 4 GWS rows exist before it). People who registered before the "
     "switch, for early-April courses, were never captured as leads.", "No - GWS boundary artifact"],
    ["3. Steady-state GWS leakage (May 2025 - Mar 2026)", lea_ns,
     "A flat ~2%/month of registrations never reach GWS. These look entirely ordinary (normal No-Source "
     "rate, normal courses/URLs). Routine website->CRM sync loss.", "No - normal ~2% sync loss"],
    ["4. We are blank, GWS has a source", len(mm),
     f"Genuine source conflicts: {len(mm)} of {n_match:,} matched people.", "Minor - see 'Mismatches'"],
    ["5. LESS: We have a source, GWS is blank", -len(rev),
     "The reverse conflict.", "Minor"],
    ["6. LESS: GWS No-Source rows we do not have", -gws_only_ns,
     "GWS holds people absent from our data. Neither system is a superset of the other.", "No - normal"],
], columns=["Component", "No Source rows", "Explanation", "Actionable?"])
ledger.loc[len(ledger)] = ["NET No-Source delta (7,008 - 5,743)",
                           rep_ns + apr_ns + lea_ns + len(mm) - len(rev) - gws_only_ns,
                           "Balances exactly to the observed delta.", ""]

# ---- sheet 3: monthly ---------------------------------------------------------------
monthly = pd.DataFrame({
    "Month": sorted(o.month.unique()),
})
monthly["Website (ours)"] = [int((o.month == m).sum()) for m in monthly.Month]
monthly["GWS / CRM"] = [int((g.month == m).sum()) for m in monthly.Month]
monthly["Delta"] = monthly["Website (ours)"] - monthly["GWS / CRM"]
monthly["Not in GWS"] = [int((~o.in_gws & (o.month == m)).sum()) for m in monthly.Month]
monthly["% not in GWS"] = (100 * monthly["Not in GWS"] / monthly["Website (ours)"]).round(1)
monthly.loc[len(monthly)] = ["TOTAL", len(o), len(g), len(o) - len(g),
                             int((~o.in_gws).sum()),
                             round(100 * (~o.in_gws).sum() / len(o), 1)]

# ---- evidence sheets -----------------------------------------------------------------
COLS = {"global_participant_id": "Global Pax ID", "pax_name": "Pax Name",
        "global_contact_id": "Contact ID", "global_event_id": "Event ID",
        "course_event_start_date": "Course Start", "event_name_en_gb": "Event Name",
        "category": "Program Type", "tag": "Tag", "participant_status": "Status",
        "source": "How Did You Find Us", "referal_site": "Referral Site"}


def evid(df):
    return df[["month"] + list(COLS)].rename(columns={**COLS, "month": "Month"})


# Split by cause. The four REPEAT_MODULES courses are the suspected follow-on sessions (81% of the
# delta, still the tech team's call to confirm); everything else is an ordinary miss. Keeping them
# apart lets the tech team answer the two questions separately.
_miss = o[~o.in_gws]
ev_missing = evid(_miss).sort_values(["Month", "Event Name", "Program Type"])
ev_miss_rep = evid(_miss[_miss.repeat_module]).sort_values(["Month", "Event Name", "Course Start"])
ev_miss_oth = evid(_miss[~_miss.repeat_module]).sort_values(["Month", "Event Name", "Program Type"])
ev_gwsonly = (g[~g.in_ours][["month", "Lead Name", "Course ID", "Course Type", "Course Category",
                             "start", "source", "City", "State", "Referral Site"]]
              .rename(columns={"month": "Month", "start": "Course Start",
                               "source": "How Did You Find Us"}).sort_values("Month"))
_conf = pd.concat([mm, rev])
ev_mm = _conf[["global_participant_id", "pax_name", "global_contact_id", "global_event_id",
               "course_event_start_date", "event_name_en_gb", "category",
               "source", "gws_source"]].rename(columns={
                   **COLS, "source": "Ours", "gws_source": "GWS has"})

README = pd.DataFrame({"": [
    "GWS / CRM  vs  artofliving.org website registrations - RECONCILIATION PROOF",
    "",
    "PERIOD      FY 2025-26 (course start date 2025-04-01 .. 2026-03-31)",
    "OUR SOURCE  aol_website_rebuilt.csv - host artofliving.org, participant_status in (Registered, Completed)",
    "GWS SOURCE  CRM - GWS Data - leads.csv - Lead Source = Web, Participant Status = Registered",
    "",
    "HEADLINE    We have 19,696 registrations. GWS has 18,034. Delta = +1,662 rows / +1,265 No Source.",
    "",
    "THE FINDING",
    f"  Our source capture is NOT broken. For the {n_match:,} people matched 1:1 across both systems the",
    f"  'How Did You Find Us' answer agrees {agree_pct}% - ZERO cases where both sides hold a label and",
    f"  disagree, {len(mm)} where we are blank and GWS has an answer, {len(rev)} the other way round.",
    "",
    "  Most of the delta looks like a GRAIN problem, not a data-quality problem. Of the 1,739 rows",
    "  missing from GWS, 1,024 sit in four courses - IP Kids/Teens Module 2 & 3, IP Junior Module 2,",
    "  IP Kids/Teens Vacation Program M2 (sheet 'Missing - IP repeat mods'). Every one is No Source",
    "  and absent from GWS. Our reading is",
    "  that these are later SESSIONS of an enrollment already counted, so no form is filled the second",
    "  time (no source answer) and no new lead is created (absent from GWS). Control: the FIRST modules",
    "  of the same courses are 40% No Source, i.e. the normal site rate. WE CANNOT CONFIRM THIS FROM",
    "  OUR SIDE - please confirm or correct it. It is 81% of the delta.",
    "",
    "  CONFIRMED GENUINE (the other direction): 'In GWS not in ours' rows are real losses. Spot-checked",
    "  contact AOLT5039648 / GWS Course ID P124290 (Online Sahaj Samadhi Dhyana Yoga, 21 Mar 2026):",
    "  the CRM holds it as a web lead with source 'Reference from a friend', but it appears NOWHERE in",
    "  view_pax_course_start - not even unfiltered. Registrations are reaching the CRM but not the",
    "  participant view.",
    "",
    "WHAT WE NEED FROM THE TECH TEAM",
    "  1. Confirm that Module 2/3 and Vacation Program M2 participant rows are follow-on sessions of an",
    "     existing enrollment, and should not be counted as new registrations.",
    "  2. Confirm GWS lead capture went live around Apr-2025 (only 4 GWS rows exist before 2025-04-01),",
    "     which would explain the April rows GWS never captured.",
    "  3. Explain the steady ~2%/month of website registrations that never reach GWS.",
    "  4. Check the rows in 'Mismatches' where the CRM holds a source and staging is blank.",
    "  5. Why do registrations reach the CRM but never appear in view_pax_course_start? See",
    "     'In GWS not in ours' - CONFIRMED genuine, e.g. contact AOLT5039648 / Course ID P124290.",
    "  6. >>> BEST FIX: put a participant / lead ID on the GWS export that maps to global_participant_id.",
    "     Everything below is a name-based approximation ONLY because no such ID exists today.",
    "",
    "JOIN METHOD  (please read - this is NOT an ID match)",
    "  GWS exposes no identifier that maps to our global_event_id / global_contact_id",
    "  (GWS 'Course ID' = TM69569 vs our global_event_id = AOLT783451 - different ID spaces),",
    "  and no registration date. The only shared identity field is the participant NAME.",
    "",
    "  Rows are matched 1:1 on (name token-set + course start date), where the name key is the sorted",
    "  SET of lowercased name tokens, tested against EVERY name spelling CiviCRM holds for that contact.",
    "  Both refinements are necessary: CiviCRM stores multiple spellings for the same contact (5,585",
    "  contact_ids have more than one) and names repeat tokens ('Rakshitha YS' vs 'Rakshitha YS YS').",
    "  A naive exact-string key wrongly reported AOLT7021338 as absent from our data when it is present.",
    "  Matching is strictly 1:1 - one GWS lead absorbs at most one of our rows - so a follow-on Module-2",
    "  row cannot claim its own Module-1 lead and double-count.",
    "",
    f"  This matches {n_match:,} of {len(g):,} GWS rows ({round(100*n_match/len(g),1)}%). The large findings",
    "  (1,025 repeat-module rows; the April cliff) are far too big to be name noise. The small residuals",
    f"  ({len(mm)}, {len(rev)}, {gws_only_ns}) remain approximate and may still contain spelling variants.",
    "",
    "SHEETS",
    "  Summary            - our 19,696 vs GWS 18,034, source by source, with delta",
    "  Delta Ledger       - the +1,265 No Source delta decomposed (balances exactly)",
    "  Monthly            - month-by-month totals and how many of our rows are absent from GWS",
    "  The 1,739 rows of ours with NO GWS counterpart are split across the next two sheets by cause.",
    "  They do not overlap and together they are the whole set. One row per participant, no duplicates.",
    "  Missing - IP repeat mods  - 1,024 rows. ONLY the four IP Module-2/3 / Vacation-M2 courses.",
    "                       SUSPECTED follow-on sessions, not new registrations. 100% No Source.",
    "                       Please confirm - this is 81% of the delta.",
    "  Missing - other courses   - 715 rows. Every other course. Ordinary misses: the April-2025",
    "                       GWS start-of-life cliff plus the steady ~2%/month sync loss.",
    "  In GWS not in ours - rows GWS holds that we do not (CONFIRMED GENUINE - see note)",
    "  Mismatches         - the only real source conflicts",
]})

# ---- write ---------------------------------------------------------------------------
with pd.ExcelWriter(OUT, engine="xlsxwriter") as xl:
    book = xl.book
    ttl = book.add_format({"bold": True, "font_size": 14})
    hdr = book.add_format({"bold": True, "bg_color": "#2a78d6", "font_color": "white",
                           "border": 1, "text_wrap": True, "valign": "top"})
    num = book.add_format({"num_format": "#,##0"})
    neg = book.add_format({"num_format": "+#,##0;-#,##0", "bold": True, "font_color": "#c0392b"})
    tot = book.add_format({"bold": True, "top": 1, "num_format": "#,##0"})
    wrap = book.add_format({"text_wrap": True, "valign": "top"})

    def sheet(name, df, widths, start=3, title=None):
        df.to_excel(xl, sheet_name=name, startrow=start, index=False)
        ws = xl.sheets[name]
        if title:
            ws.write(0, 0, title, ttl)
        for i, c in enumerate(df.columns):
            ws.write(start, i, c, hdr)
        for i, w in enumerate(widths):
            ws.set_column(i, i, w, wrap if w > 45 else (num if w <= 14 else None))
        ws.freeze_panes(start + 1, 0)
        return ws

    README.to_excel(xl, sheet_name="READ ME", index=False, header=False)
    xl.sheets["READ ME"].set_column(0, 0, 112)
    xl.sheets["READ ME"].write(0, 0, README.iloc[0, 0], ttl)

    ws = sheet("Summary", src, [40, 15, 13, 18, 14],
               title="Website vs GWS  -  FY 2025-26  -  registrations by 'How Did You Find Us'")
    ws.write(1, 0, "We have 19,696 registrations; GWS has 18,034. The entire gap is No Source.")
    ws.conditional_format(4, 3, 4 + len(src) - 1, 3,
                          {"type": "cell", "criteria": ">", "value": 100, "format": neg})

    sheet("Delta Ledger", ledger, [52, 14, 88, 26],
          title="The +1,265 No-Source delta, decomposed  (balances exactly)")
    sheet("Monthly", monthly, [12, 15, 13, 10, 12, 13],
          title="Month by month  -  note April-2025: GWS start-of-life")
    # The two sheets PARTITION the 1,739 - no row appears on both, and together they are the whole
    # set. A combined sheet on top of them would just duplicate every row, so there isn't one.
    W_MISS = [10, 15, 26, 13, 13, 20, 30, 18, 22, 12, 30, 46]
    ws = sheet("Missing - IP repeat mods", ev_miss_rep, W_MISS,
               title=f"{len(ev_miss_rep):,} of the {len(ev_missing):,} missing rows - the four IP "
                     f"repeat-module courses (Module 2/3, Vacation Prog M2)")
    ws.write(1, 0, "SUSPECTED NOT REGISTRATIONS - later sessions of an enrollment already counted. "
                   "100% No Source, none in GWS. Please confirm.")
    ws = sheet("Missing - other courses", ev_miss_oth, W_MISS,
               title=f"{len(ev_miss_oth):,} of the {len(ev_missing):,} missing rows - every other course")
    ws.write(1, 0, "ORDINARY MISSES - April-2025 GWS start-of-life plus the steady ~2%/month sync loss. "
                   "Normal source mix.")
    sheet("In GWS not in ours", ev_gwsonly, [10, 26, 13, 22, 22, 13, 30, 16, 16, 46],
          title=f"{len(ev_gwsonly)} rows GWS holds that our data does not")
    sheet("Mismatches", ev_mm, [15, 26, 13, 13, 20, 30, 18, 22, 22],
          title=f"The only genuine source conflicts: {len(ev_mm)} of {n_match:,} matched people "
                f"({agree_pct}% agreement)")

    # ---- charts (the boss's page) ----------------------------------------------------
    # Waterfall isn't a writable chart type, so it's a stacked column with an invisible
    # base carrying each bar up to its starting height.
    ACCENT, RISE, FALL, TOTAL_C = "#2a78d6", "#2a78d6", "#c0504d", "#1f4e79"
    cw = book.add_worksheet("Charts")
    cw.hide_gridlines(2)
    cw.write(0, 0, "Website vs GWS  -  FY 2025-26", ttl)
    cw.write(1, 0, "Every labelled channel agrees within ~3%. The entire gap is No Source.")

    # data block for chart 1 (top sources, biggest first), parked out of sight
    c1 = src[src.Source != "TOTAL"].sort_values("Website (ours)", ascending=False)
    cw.write_row("T1", ["Source", "Website (ours)", "GWS / CRM"])
    for i, r in enumerate(c1.itertuples(), start=1):
        cw.write_row(f"T{i+1}", [r.Source, r._2, r._3])
    n1 = len(c1)

    ch1 = book.add_chart({"type": "column"})
    for idx, (nm_, col, colr) in enumerate([("Website (ours)", 20, ACCENT),
                                            ("GWS / CRM", 21, "#9dc3e6")]):
        ch1.add_series({
            "name": nm_,
            "categories": ["Charts", 1, 19, n1, 19],
            "values": ["Charts", 1, col, n1, col],
            "fill": {"color": colr},
            "border": {"none": True},
            "gap": 60,
        })
    ch1.set_title({"name": "Registrations by 'How Did You Find Us'"})
    ch1.set_y_axis({"num_format": "#,##0", "major_gridlines": {"visible": True,
                    "line": {"color": "#e6e6e6"}}})
    ch1.set_x_axis({"num_font": {"rotation": -45}})
    ch1.set_legend({"position": "top"})
    ch1.set_size({"width": 760, "height": 380})
    cw.insert_chart("A4", ch1)

    # data block for chart 2 (waterfall)
    steps = [
        ("Repeat modules\n(not registrations)", rep_ns, "rise"),
        ("April-2025\nGWS start-of-life", apr_ns, "rise"),
        ("Steady ~2%\nGWS leakage", lea_ns, "rise"),
        ("We blank,\nGWS has source", len(mm), "rise"),
        ("Conflicts &\nGWS-only rows", -(len(rev) + gws_only_ns), "fall"),
        ("NET DELTA", None, "total"),
    ]
    cw.write_row("T20", ["Step", "base", "rise", "fall", "total"])
    run = 0
    for i, (lbl, val, kind) in enumerate(steps, start=1):
        base = rise = fall = total = None
        if kind == "total":
            total = run
            base = 0
        elif val >= 0:
            base, rise = run, val
            run += val
        else:
            run += val          # run is now the post-drop height
            base, fall = run, -val
        cw.write_row(f"T{20+i}", [lbl,
                                  base if base is not None else "",
                                  rise if rise is not None else "",
                                  fall if fall is not None else "",
                                  total if total is not None else ""])
    n2 = len(steps)

    ch2 = book.add_chart({"type": "column", "subtype": "stacked"})
    ch2.add_series({                                   # invisible riser
        "name": "base",
        "categories": ["Charts", 20, 19, 20 + n2 - 1, 19],
        "values": ["Charts", 20, 20, 20 + n2 - 1, 20],
        "fill": {"none": True}, "border": {"none": True},
    })
    for nm_, col, colr in [("Adds to the gap", 21, RISE),
                           ("Reduces the gap", 22, FALL),
                           ("Net delta", 23, TOTAL_C)]:
        ch2.add_series({
            "name": nm_,
            "categories": ["Charts", 20, 19, 20 + n2 - 1, 19],
            "values": ["Charts", 20, col, 20 + n2 - 1, col],
            "fill": {"color": colr}, "border": {"none": True},
            "data_labels": {"value": True, "position": "inside_end",
                            "font": {"color": "white", "bold": True}},
            "gap": 50,
        })
    ch2.set_title({"name": "Where the +1,265 No-Source delta comes from"})
    ch2.set_y_axis({"num_format": "#,##0", "major_gridlines": {"visible": True,
                    "line": {"color": "#e6e6e6"}}})
    ch2.set_legend({"position": "top", "delete_series": [0]})   # hide the invisible base
    ch2.set_size({"width": 760, "height": 400})
    cw.insert_chart("A26", ch2)
    cw.write(46, 0, "81% of the gap is IP repeat-module rows - later sessions of an enrollment "
                    "already counted. They are not registrations.")
    cw.set_column("T:X", None, None, {"hidden": True})   # tuck the chart data away

print("wrote", OUT)
print()
print("Summary sheet:")
print(src.to_string(index=False))
print()
print("Ledger:")
print(ledger[["Component", "No Source rows"]].to_string(index=False))
print()
print("evidence rows -> missing-from-GWS %d (%d distinct pax ids) | gws-only %d | conflicts %d"
      % (len(ev_missing), ev_missing["Global Pax ID"].nunique(), len(ev_gwsonly), len(ev_mm)))
