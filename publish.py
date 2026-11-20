"""ขั้นตอนที่ 4: The Publication
อ่านตารางจาก schema production แล้วเขียนลง Google Sheets ด้วย gspread

เขียนทีละก้อน (CHUNK_ROWS แถวต่อครั้ง) แทนการส่งทั้งตารางในคำขอเดียว
เพราะตาราง corporate_events มีประมาณ 1.7 ล้าน cell ซึ่งใหญ่เกินไปสำหรับ request เดียว
"""
import json
import time

import gspread
import pandas as pd
from gspread.utils import rowcol_to_a1

import config

# (ตารางใน production, ชื่อ worksheet)
TABLES = [
    ("corporate_events", "corporate_events"),
    ("events_monthly", "events_monthly"),
]
SHEETS_CELL_LIMIT = 10_000_000  # ลิมิตต่อ Spreadsheet ของ Google Sheets
CHUNK_ROWS = 5_000              # ~85,000 cell ต่อ request สำหรับตาราง 17 คอลัมน์
MAX_RETRIES = 5


def to_values(df: pd.DataFrame) -> list[list]:
    """แปลง DataFrame เป็น list ของแถวที่ส่งให้ Sheets ได้ (NaN -> ค่าว่าง, ไม่มี numpy type)"""
    rows = json.loads(df.to_json(orient="values", date_format="iso"))
    return [["" if v is None else v for v in row] for row in rows]


def write_chunk(ws, values: list[list], start_row: int) -> None:
    """เขียนหนึ่งก้อนที่เริ่มแถว start_row (ลองใหม่เมื่อชน rate limit/ข้อผิดพลาดชั่วคราว)"""
    cell = rowcol_to_a1(start_row, 1)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # RAW = เก็บค่าตามที่ส่ง ไม่ให้ Sheets เดาชนิดข้อมูลเอง
            ws.update(values=values, range_name=cell, value_input_option="RAW")
            return
        except gspread.exceptions.APIError as e:
            if attempt == MAX_RETRIES:
                raise
            wait = 2 ** attempt * 5
            print(f"[publish]   APIError ({e}) รอ {wait} วินาทีแล้วลองใหม่ ({attempt}/{MAX_RETRIES})")
            time.sleep(wait)


def write_dataframe(ws, df: pd.DataFrame) -> None:
    ws.resize(rows=len(df) + 1, cols=df.shape[1])
    write_chunk(ws, [list(df.columns)], start_row=1)  # header

    values = to_values(df)
    total_chunks = (len(values) + CHUNK_ROWS - 1) // CHUNK_ROWS
    for i in range(total_chunks):
        chunk = values[i * CHUNK_ROWS:(i + 1) * CHUNK_ROWS]
        write_chunk(ws, chunk, start_row=2 + i * CHUNK_ROWS)
        print(f"[publish]   ก้อน {i + 1}/{total_chunks} ({len(chunk):,} แถว)")
        time.sleep(1)  # เว้นจังหวะ เพื่อไม่ให้ชน quota การเขียนต่อนาที


def run():
    engine = config.get_engine()
    gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE)
    sh = gc.open(config.GOOGLE_SHEET_NAME)  # ต้องแชร์ Sheet ให้ service account เป็น Editor ก่อน

    # อ่านทุกตารางและตรวจลิมิต cell ก่อนเขียน จะได้ไม่เขียนค้างครึ่งทาง
    frames = []
    total_cells = 0
    for table, ws_name in TABLES:
        df = pd.read_sql_table(table, engine, schema=config.PROD_SCHEMA)
        cells = df.shape[0] * df.shape[1]
        total_cells += cells
        print(f"[publish] {table}: {len(df):,} แถว ({cells:,} cell)")
        frames.append((ws_name, df))
    if total_cells > SHEETS_CELL_LIMIT:
        raise RuntimeError(f"ข้อมูลเกินลิมิต {SHEETS_CELL_LIMIT:,} cell ของ Google Sheets")

    for ws_name, df in frames:
        try:
            ws = sh.worksheet(ws_name)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=ws_name, rows=1, cols=1)
        write_dataframe(ws, df)
        print(f"[publish] เขียน worksheet '{ws_name}' สำเร็จ")

    print(f"[publish] รวม {total_cells:,} cell")


if __name__ == "__main__":
    run()
