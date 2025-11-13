#!/usr/bin/env python3
import time, psycopg, datetime as dt
DSN = "postgresql://localhost/2ndopinionmd"
SRC = "mimic4_note"
INTERVAL = 30

def pending(cur):
    cur.execute("""SELECT
      COUNT(*) FILTER (WHERE source=%s) total,
      COUNT(*) FILTER (WHERE source=%s AND embedding IS NULL) pending
      FROM rag_corpus""", (SRC, SRC))
    return cur.fetchone()

with psycopg.connect(DSN) as conn, conn.cursor() as cur:
    t0 = dt.datetime.now()
    total0, pend0 = pending(cur)
    print(f"Start: total={total0:,}, pending={pend0:,}")
    while True:
        time.sleep(INTERVAL)
        now = dt.datetime.now()
        total, pend = pending(cur)
        done = total - pend
        rate = (pend0 - pend) / max((now - t0).total_seconds(), 1)  # rows/sec
        eta = "n/a" if rate <= 0 else str(dt.timedelta(seconds=int(pend / rate)))
        print(f"{now:%H:%M:%S}  done={done:,}/{total:,}  pending={pend:,}  "
              f"rate={rate:.1f} r/s  ETA~{eta}")

