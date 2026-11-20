"""ขั้นตอนที่ 2: Extraction & Load
อ่านไฟล์ CSV จาก Kaggle แล้วโหลดข้อมูลดิบเข้า PostgreSQL schema raw_data
"""
import pandas as pd
from sqlalchemy import text

import config


def run():
    print(f"[ingest] อ่านไฟล์ {config.CSV_PATH}")
    df = pd.read_csv(config.CSV_PATH)
    print(f"[ingest] พบ {len(df):,} แถว {df.shape[1]} คอลัมน์")

    engine = config.get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.RAW_SCHEMA}"))

    # โหลดข้อมูลดิบตามเดิม ไม่แก้ไขอะไร (replace = รันซ้ำได้ ผลลัพธ์เหมือนเดิม)
    df.to_sql(
        config.RAW_TABLE,
        engine,
        schema=config.RAW_SCHEMA,
        if_exists="replace",
        index=False,
        chunksize=10_000,
        method="multi",
    )
    print(f"[ingest] โหลดเข้า {config.RAW_SCHEMA}.{config.RAW_TABLE} สำเร็จ")


if __name__ == "__main__":
    run()
