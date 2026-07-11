# Website Registrations Report

Streamlit dashboard for Art of Living website course registrations.

The first page mirrors the internal WhatsApp sheet — Program Type (17 CRM categories),
How Did You Find Us, and the source-bucket summaries — with a Financial Year selector.
Below that: source buckets by FY and a category-composition drill-down (which raw tags
and event names roll into each category).

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `app.py` — the Streamlit dashboard.
- `category_map.py` — tag → 17-category mapping (tag-driven; two shared tags split by event name).
- `aol_website_rebuilt.csv` — deduped registration extract the app renders (pseudonymous contact IDs; no names/emails).

Data is bucketed by course start date; universe is host `artofliving.org`, status Registered + Completed.
