"""ขั้นตอนที่ 5: The Automaton
รันทั้ง pipeline ด้วยคำสั่งเดียว:  python run_pipeline.py
"""
import sys
import time

import ingest
import transform
import publish


def main():
    steps = [("ingest", ingest.run), ("transform", transform.run), ("publish", publish.run)]
    start = time.time()
    for name, fn in steps:
        t0 = time.time()
        print(f"\n===== {name.upper()} =====")
        try:
            fn()
        except Exception as e:
            print(f"\n[ERROR] ขั้นตอน {name} ล้มเหลว: {e}")
            sys.exit(1)
        print(f"[{name}] ใช้เวลา {time.time() - t0:.1f} วินาที")
    print(f"\nเสร็จสิ้นทั้ง pipeline ใน {time.time() - start:.1f} วินาที")


if __name__ == "__main__":
    main()
