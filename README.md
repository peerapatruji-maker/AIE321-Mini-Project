# Corporate Events Data Pipeline

ไปป์ไลน์ข้อมูลอัตโนมัติแบบครบวงจรบนเครื่องของตัวเอง จากชุดข้อมูล Kaggle **Corporate Events** (ข่าวเหตุการณ์ทางธุรกิจ เช่น M&A, Lawsuit, Layoffs, IPO ปี 2019 - 2026 จำนวน ~99,756 แถว)
ไปจนถึง Dashboard บน Looker Studio (เดิมคือ Google Data Studio)

```
CSV (Kaggle) -> ingest.py -> PostgreSQL (raw_data) -> transform.py -> PostgreSQL (production)
                                                                          |
                                         Looker Studio <- Google Sheets <- publish.py
```

## สิ่งที่ต้องมี

- Python 3.10 ขึ้นไป
- Docker และ Docker Compose
- บัญชี Google และ Service Account (ดูขั้นตอนด้านล่าง)

## โครงสร้างโปรเจกต์

| ไฟล์ | หน้าที่ |
|---|---|
| `docker-compose.yml` | เปิด PostgreSQL 16 บน Docker |
| `config.py` | ค่าตั้งต้นและตัวเชื่อมต่อฐานข้อมูล (อ่านจาก `.env`) |
| `ingest.py` | โหลด CSV ดิบเข้า `raw_data.corporate_events_clean` |
| `transform.py` | Clean + Feature Engineering + Aggregation แล้วเขียนลง schema `production` |
| `publish.py` | อ่านตาราง `production` แล้วส่งขึ้น Google Sheets ด้วย gspread |
| `run_pipeline.py` | รันทั้ง 3 ขั้นตอนต่อเนื่องด้วยคำสั่งเดียว |

## วิธีรัน

### 1) ดาวน์โหลดข้อมูล

ดาวน์โหลด `corporate_events_clean.csv` จาก Kaggle แล้ววางไว้ที่ `data/corporate_events_clean.csv`

### 2) ติดตั้ง library

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3) ตั้งค่า environment

```bash
cp .env.example .env             # แก้รหัสผ่านและชื่อ Google Sheet ตามต้องการ
```

### 4) เปิดฐานข้อมูล

```bash
docker compose up -d
docker compose ps                # รอให้สถานะเป็น healthy
```

### 5) ตั้งค่า Google API Credentials

1. เข้า [Google Cloud Console](https://console.cloud.google.com/) แล้วสร้าง Project ใหม่
2. ไปที่ **APIs & Services > Library** เปิดใช้งาน **Google Sheets API** และ **Google Drive API**
3. ไปที่ **APIs & Services > Credentials > Create Credentials > Service Account** ตั้งชื่อแล้วกด Done
4. เปิด Service Account ที่สร้าง ไปแท็บ **Keys > Add Key > Create new key > JSON** จะได้ไฟล์ JSON ดาวน์โหลดมา
5. เปลี่ยนชื่อไฟล์เป็น `credentials.json` แล้ววางไว้ที่โฟลเดอร์โปรเจกต์ (**ห้าม commit** ไฟล์นี้อยู่ใน `.gitignore` แล้ว)
6. สร้าง Google Sheet ว่างชื่อเดียวกับ `GOOGLE_SHEET_NAME` ใน `.env` (ค่าเริ่มต้น `corporate_events_dashboard`)
7. กด **Share** ที่ Google Sheet นั้น แล้วเพิ่มอีเมลของ Service Account (ค่า `client_email` ในไฟล์ JSON) เป็น **Editor**

### 6) รัน pipeline

```bash
python run_pipeline.py
```

หรือรันทีละขั้นตอน:

```bash
python ingest.py
python transform.py
python publish.py
```

สคริปต์ออกแบบให้รันซ้ำได้ (idempotent) ข้อมูลเดิมจะถูกแทนที่ ไม่ซ้ำซ้อน

## ตารางที่ได้

**`raw_data.corporate_events_clean`** ข้อมูลดิบตามไฟล์ CSV (21 คอลัมน์)

**`production.corporate_events`** ตารางหลักของ Dashboard ระดับ 1 แถว = 1 เหตุการณ์ หลัง Clean แล้ว (~99,737 แถว 17 คอลัมน์)
ตัดคอลัมน์ `headline` ออกเพื่อลดจำนวน cell คอลัมน์ที่เพิ่มจาก Feature Engineering:
`event_category`, `year_month`, `is_deal`, `is_negative_event`, `is_country_known`

**`production.events_monthly`** ตารางสรุปรายเดือน x ประเภทเหตุการณ์ x กลุ่มอุตสาหกรรม (~8,100 แถว)

## ข้อควรระวังเรื่องขนาดข้อมูล

Google Sheets จำกัด 10 ล้าน cell ต่อ Spreadsheet ตาราง `corporate_events` มีประมาณ 1.7 ล้าน cell และ `events_monthly` อีกประมาณ 57,000 cell
`publish.py` ตรวจจำนวน cell ก่อนเขียนทุกครั้ง

## Dashboard

สร้างที่ [lookerstudio.google.com](https://lookerstudio.google.com) (ชื่อเดิมคือ Data Studio) เลือก Connector **Google Sheets** แล้วเลือก worksheet `corporate_events` และ `events_monthly`
ตั้งค่าแชร์เป็น "Anyone with the link can view"

## ข้อควรรู้เกี่ยวกับข้อมูล

- 1 เหตุการณ์ M&A อาจมี 2 แถว (ฝั่ง acquirer และ target) จึงนับเป็น "จำนวนแถวเหตุการณ์" ไม่ใช่ "จำนวนดีล"
- ข้อมูลปี 2026 มีถึง 30 มิถุนายน 2026 เท่านั้น ไม่ควรเทียบกับปีเต็ม
- ข้อมูลมาจากข่าว จึงสะท้อนความสนใจของสื่อด้วย ไม่ใช่กิจกรรมจริงทั้งหมดของตลาด
