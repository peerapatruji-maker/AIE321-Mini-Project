"""ค่าตั้งต้นของ pipeline ทั้งหมด (อ่านจากไฟล์ .env ถ้ามี)

ingest.py / transform.py / publish.py เรียกใช้ผ่าน `import config`
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ---------- ไฟล์ข้อมูลต้นทาง ----------
CSV_PATH = Path(os.getenv("CSV_PATH", BASE_DIR / "data" / "corporate_events_clean.csv"))

# ---------- PostgreSQL (ค่า default ตรงกับ docker-compose.yml) ----------
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "corporate_events")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

RAW_SCHEMA = "raw_data"
PROD_SCHEMA = "production"
# โจทย์: ตั้งชื่อตารางตามชื่อไฟล์/ชุดข้อมูล
RAW_TABLE = "corporate_events_clean"

# ---------- Google Sheets ----------
GOOGLE_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", str(BASE_DIR / "credentials.json")
)
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "corporate_events_dashboard")


def get_engine():
    """สร้าง SQLAlchemy engine เชื่อม PostgreSQL (URL.create รองรับรหัสผ่านที่มีอักขระพิเศษ)"""
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
    )
    return create_engine(url)
