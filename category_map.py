"""Map our raw course `tag` onto the CRM's 17 Course Categories.

Tag-driven (rebuilt with Ishan, 2026-07-11). Every tag maps to exactly one category
via TAG_MAP, EXCEPT two tags that cover more than one category and are split by event
name (handled in _split). This replaces the earlier event-name/CRM-lookup approach.
"""
import pandas as pd

WEB = "aol_website_rebuilt.csv"

CATEGORIES = [
    "AMP", "Blessing Course", "DSN", "HP/OMBW", "Intuition Process", "KYC/KYT",
    "Medha Yoga", "Others", "Sahaj Samadhi", "Sanyam", "Sleep and Anxiety",
    "Sri Sri Yoga Programs", "Utkarsha Yoga", "VTP", "YLTP",
    "Yoga Classes Challenge", "Yoga Classes Gen",
]

# One category per tag. Confirmed tag by tag with Ishan, 2026-07-11.
TAG_MAP = {
    "HP": "HP/OMBW",
    "AMP": "AMP",
    "Sahaj": "Sahaj Samadhi",
    "C&T-PY-NonInstitutional": "Intuition Process",
    "C&T-PY2-NonInstitutional": "Intuition Process",
    "IP repeaters": "Intuition Process",
    "KYC-KYT": "KYC/KYT",
    "Deep Sleep": "Sleep and Anxiety",
    "DSN": "DSN",
    "VTP": "VTP",
    "SSY Challenges": "Yoga Classes Challenge",
    "Blessing": "Blessing Course",
    "Sanyam": "Sanyam",
    "YLTP": "YLTP",
    "UY_MY Upgrade": "Medha Yoga",
    "ShaktiKriya": "Others",
    "Wellness": "Others",
    "Eternity": "Others",
    "HP_Institutional": "Others",
    "others": "Others",
    "Spine": "Others",
}

# Tags that cover >1 category: resolved by event name (lower-cased).
#   C&T-UY-MY-NonInstitutional -> Utkarsha Yoga / Medha Yoga / else Others
#   SSY - All Programs -> the two "Classes" events are Yoga Classes Gen; everything
#     else (Level 1, Prenatal, Kids, Certified, Deep Dive, SSY) is Sri Sri Yoga Programs.
SSY_CLASSES = {"online sri sri yoga classes", "sri sri yoga classes"}


def _split(tag, name):
    if tag == "C&T-UY-MY-NonInstitutional":
        if "utkarsha" in name:
            return "Utkarsha Yoga"
        if "medha" in name:
            return "Medha Yoga"
        return "Others"
    if tag == "SSY - All Programs":
        return "Yoga Classes Gen" if name in SSY_CLASSES else "Sri Sri Yoga Programs"
    return "Others"


def categorise(df):
    """Return a category Series from a frame carrying `tag` and `event_name_en_gb`."""
    name = df.event_name_en_gb.str.strip().str.lower()
    cat = df.tag.map(TAG_MAP)
    split = cat.isna()
    if split.any():
        cat = cat.copy()
        cat[split] = [_split(t, n) for t, n in zip(df.tag[split], name[split])]
    return cat.fillna("Others")


def website_rows():
    d = pd.read_csv(WEB, dtype=str).drop_duplicates()
    d = d[d.participant_status.isin(["Registered", "Completed"])]
    host = d.referal_site.str.extract(r"^https?://([^/:]+)", expand=False).str.lower()
    return d[host.str.match(r"(.*\.)?artofliving\.org$", na=False)]


if __name__ == "__main__":
    d = website_rows()
    d["category"] = categorise(d)
    assert set(d.category) <= set(CATEGORIES), set(d.category) - set(CATEGORIES)

    mapped = d.tag.isin(TAG_MAP)
    print(f"rows {len(d):,}")
    print(f"  mapped by tag        : {mapped.sum():>6,}")
    print(f"  split by event name  : {(~mapped).sum():>6,}")

    out = d.groupby("category").size().reindex(CATEGORIES).fillna(0).astype(int)
    out.loc["Grand Total"] = out.sum()
    print("\n=== OUR ENROLLMENTS BY CRM CATEGORY (tag-driven) ===")
    print(out.to_string())
