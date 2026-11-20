"""ขั้นตอนที่ 3: The Refinery
อ่านจาก raw_data -> ทำความสะอาด/สร้างฟีเจอร์/สรุปผลด้วย Pandas -> เขียนลง production
"""
import pandas as pd
from sqlalchemy import text

import config

# กลุ่มเหตุการณ์ (Feature Engineering) เพื่อให้ Dashboard อ่านง่ายขึ้น
EVENT_CATEGORY = {
    "M&A": "Deal",
    "Asset acquisition": "Deal",
    "IPO": "Capital Market",
    "Share buyback": "Capital Market",
    "Contract": "Business Operation",
    "New product": "Business Operation",
    "Company announcement": "Business Operation",
    "Incorporation": "Business Operation",
    "Job creation": "Workforce",
    "Layoffs": "Workforce",
    "Lawsuit": "Legal & Regulatory",
    "Regulatory": "Legal & Regulatory",
    "FDA approval": "Legal & Regulatory",
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1) Data type
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df = df.dropna(subset=["event_date"])

    # 2) ตัดช่องว่าง + ค่าว่างให้เป็น Unknown/Unclassified
    text_cols = ["company_name", "company_domain", "country", "sector",
                 "sector_group", "event_type", "role", "news_source", "headline"]
    for c in text_cols:
        df[c] = df[c].astype("string").str.strip()
    df["country"] = df["country"].fillna("Unknown").replace("", "Unknown")
    df["sector"] = df["sector"].fillna("Unclassified").replace("", "Unclassified")
    df["sector_group"] = df["sector_group"].fillna("Unclassified").replace("", "Unclassified")
    df["news_source"] = df["news_source"].fillna("Unknown").replace("", "Unknown")

    # 3) ตัดแถวซ้ำ
    before = len(df)
    df = df.drop_duplicates(subset="event_id")
    df = df.drop_duplicates(subset=["company_name", "event_date", "headline"])
    print(f"[transform] ตัดแถวซ้ำ {before - len(df):,} แถว")

    # 4) flag ให้เป็น int 0/1
    for c in ["is_acquirer", "is_target", "is_plaintiff", "is_defendant", "has_news_source"]:
        df[c] = df[c].fillna(0).astype(int)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["event_category"] = df["event_type"].map(EVENT_CATEGORY).fillna("Other")
    df["year_month"] = df["event_date"].dt.to_period("M").dt.to_timestamp()
    df["day_of_week"] = df["event_date"].dt.day_name()
    df["is_country_known"] = (df["country"] != "Unknown").astype(int)
    df["is_sector_known"] = (df["sector_group"] != "Unclassified").astype(int)
    df["is_deal"] = df["event_type"].isin(["M&A", "Asset acquisition"]).astype(int)
    df["is_negative_event"] = df["event_type"].isin(["Layoffs", "Lawsuit"]).astype(int)
    return df


def select_for_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    """เลือกเฉพาะคอลัมน์ที่ Dashboard ใช้ เพื่อลดจำนวน cell ใน Google Sheets
    (ตัด headline ที่ยาวออก ~100k แถว x 17 คอลัมน์ ~ 1.7 ล้าน cell < ลิมิต 10 ล้าน)
    """
    cols = [
        "event_id", "event_date", "year", "quarter", "year_quarter", "year_month",
        "event_type", "event_category", "role", "company_name", "country",
        "sector", "sector_group", "is_deal", "is_negative_event",
        "is_country_known", "has_news_source",
    ]
    out = df[cols].copy()
    out["event_date"] = out["event_date"].dt.strftime("%Y-%m-%d")
    out["year_month"] = out["year_month"].dt.strftime("%Y-%m-%d")
    return out


def aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """สรุปจำนวนเหตุการณ์รายเดือน x ประเภทเหตุการณ์ x กลุ่มอุตสาหกรรม"""
    agg = (
        df.groupby(["year_month", "year", "event_type", "event_category", "sector_group"],
                   as_index=False)
        .agg(event_count=("event_id", "count"),
             company_count=("company_name", "nunique"))
    )
    agg["year_month"] = agg["year_month"].dt.strftime("%Y-%m-%d")
    return agg


def run():
    engine = config.get_engine()
    print(f"[transform] อ่านจาก {config.RAW_SCHEMA}.{config.RAW_TABLE}")
    raw = pd.read_sql_table(config.RAW_TABLE, engine, schema=config.RAW_SCHEMA)
    print(f"[transform] อ่านมา {len(raw):,} แถว")

    cleaned = clean(raw)
    featured = add_features(cleaned)
    events = select_for_dashboard(featured)
    monthly = aggregate_monthly(featured)

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.PROD_SCHEMA}"))

    events.to_sql("corporate_events", engine, schema=config.PROD_SCHEMA,
                  if_exists="replace", index=False, chunksize=10_000, method="multi")
    monthly.to_sql("events_monthly", engine, schema=config.PROD_SCHEMA,
                   if_exists="replace", index=False, chunksize=10_000, method="multi")
    print(f"[transform] เขียน {config.PROD_SCHEMA}.corporate_events {len(events):,} แถว")
    print(f"[transform] เขียน {config.PROD_SCHEMA}.events_monthly {len(monthly):,} แถว")


if __name__ == "__main__":
    run()
