#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, time, math, os, sys
from datetime import datetime
from collections import defaultdict

# Reuse your DB helper (same as reports)
from report_common import connect, q

SQL_COUNTS = """
SELECT source,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,
       COUNT(*) FILTER (WHERE embedding IS NULL)     AS pending,
       ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 2) AS pct
FROM public.rag_corpus
WHERE {filter_clause}
GROUP BY source
ORDER BY source;
"""

SQL_ERRORS_IF_TABLE = """
SELECT source, COUNT(*) AS errs
FROM public.rag_embed_errors
WHERE {filter_clause_errors}
GROUP BY source
ORDER BY source;
"""

def table_exists(conn, schema, name):
    rows = q(conn, """
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema=%s AND table_name=%s
      LIMIT 1
    """, (schema, name))
    return bool(rows)

def format_row(cols, widths):
    return " | ".join(str(c).ljust(w) for c, w in zip(cols, widths))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--like", default="mimic%", help="Filter sources with ILIKE pattern (default: mimic%)")
    ap.add_argument("--interval", type=float, default=3.0, help="Refresh interval seconds")
    ap.add_argument("--wide", action="store_true", help="Show extra columns (qps, eta)")
    args = ap.parse_args()

    conn = connect()
    has_err_table = table_exists(conn, "public", "rag_embed_errors")

    last_done = defaultdict(int)
    last_ts   = defaultdict(lambda: time.time())

    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.system("clear")
        print(f"[{now}] Embedding watch  —  filter: ILIKE '{args.like}'   (Ctrl-C to exit)")
        print()

        counts = q(conn, SQL_COUNTS.format(filter_clause="source ILIKE %s"), (args.like,))
        errmap = {}
        if has_err_table:
            errs = q(conn, SQL_ERRORS_IF_TABLE.format(filter_clause_errors="source ILIKE %s"), (args.like,))
            errmap = {r["source"]: int(r["errs"]) for r in errs}

        widths = [18, 10, 10, 10, 7]
        headers = ["source", "total", "done", "pending", "%"]
        if args.wide:
            headers += ["qps", "eta"]
            widths  += [7, 10]
        headers += ["errors"]
        widths  += [8]

        print(format_row(headers, widths))
        print("-" * (sum(widths) + 3 * (len(widths) - 1)))

        total_total = total_done = total_pending = 0
        total_errors = 0

        for r in counts:
            src   = r["source"]
            total = int(r["total"] or 0)
            done  = int(r["done"] or 0)
            pend  = int(r["pending"] or 0)
            pct   = float(r["pct"] or 0.0)

            total_total   += total
            total_done    += done
            total_pending += pend

            # rate + ETA (per source)
            qps = ""
            eta = ""
            if args.wide:
                now_t = time.time()
                dt = max(now_t - last_ts[src], 1e-6)
                dd = max(done - last_done[src], 0)
                rate = dd / dt
                qps = f"{rate:.1f}"
                remaining = max(total - done, 0)
                if rate > 0:
                    sec = remaining / rate
                    m, s = divmod(int(sec), 60)
                    h, m = divmod(m, 60)
                    eta = f"{h:02d}:{m:02d}:{s:02d}"
                else:
                    eta = "--:--:--"
                last_done[src] = done
                last_ts[src]   = now_t

            errs = errmap.get(src, 0)
            total_errors += errs

            row = [src, total, done, pend, f"{pct:.2f}"]
            if args.wide:
                row += [qps, eta]
            row += [errs]
            print(format_row(row, widths))

        # Totals row
        tot_pct = (100.0 * total_done / total_total) if total_total else 0.0
        tot_row = ["TOTAL", total_total, total_done, total_pending, f"{tot_pct:.2f}"]
        if args.wide:
            tot_row += ["", ""]
        tot_row += [total_errors]
        print("-" * (sum(widths) + 3 * (len(widths) - 1)))
        print(format_row(tot_row, widths))

        sys.stdout.flush()
        time.sleep(args.interval)

if __name__ == "__main__":
    main()

