#!/usr/bin/env python3
"""在拋棄式 PostgreSQL 實測階段七的負載取捨題（S7-01、S7-02、S7-03、S7-05），輸出 live-postgres-measured 快照。

這四個概念要量的東西在瀏覽器的 SQLite 量不出來：百萬列上的聚合與快取欄、TOAST 與垂直拆表、
多連線搶同一列的鎖、Range 分區的 DROP 與逐列 DELETE。每一組基準自己建表、灌資料、量完就刪表，
所以叢集裡只要有一個空的資料庫可用；資料以 setseed 固定，耗時會隨主機負載浮動，計畫與計數不會。

用法（需要 PATH 上有 psql 與 pgbench；叢集要是拋棄式的，腳本會 DROP DATABASE workload_bench）：
  docker run -d --name sqlpractice-pg18 -e POSTGRES_HOST_AUTH_METHOD=trust \\
    -p 127.0.0.1:55432:5432 postgres:18 -c shared_buffers=512MB -c max_wal_size=512MB
  python3 scripts/sql-practice/pg_workload_bench.py --port 55432 --out <輸出的 JSON 路徑>
  python3 scripts/sql-practice/pg_workload_bench.py --port 55432 --only hot-counter   # 只跑一組
  docker rm -fv sqlpractice-pg18

每一組的 findings 由量到的數字組成；方向不成立（例如快取欄沒有比即時聚合快）時腳本以 exit 1 結束，
不寫出快照，讓題目的敘述跟著實測修正，而不是讓快照跟著敘述。
"""

import argparse
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile

DB = "workload_bench"
# psql 依用戶端語系翻譯 \timing 的「Time:」與錯誤訊息；固定成 C 語系，輸出才解析得了
C_LOCALE = {**os.environ, "LC_ALL": "C", "LANG": "C", "PGCLIENTENCODING": "UTF8"}


class Pg:
    def __init__(self, host: str, port: int, user: str):
        self.conn = ["-h", host, "-p", str(port), "-U", user]
        self.base = ["psql", "-X", "-q", "-At", "-v", "ON_ERROR_STOP=1", *self.conn]

    def sql(self, text: str, db: str = DB) -> str:
        r = subprocess.run(self.base + ["-d", db], input=text, text=True, capture_output=True, env=C_LOCALE)
        if r.returncode != 0:
            raise RuntimeError(f"SQL 失敗：\n{text[:400]}\n{r.stderr.strip()}")
        return r.stdout.strip()

    def try_sql(self, text: str) -> tuple[bool, str]:
        r = subprocess.run(self.base + ["-d", DB], input=text, text=True, capture_output=True, env=C_LOCALE)
        return r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr).strip()

    def val(self, text: str):
        out = self.sql(text)
        try:
            return int(out)
        except ValueError:
            return float(out)

    def timed_with_wal(self, stmt: str) -> dict:
        """同一個連線裡量一條敘述的耗時與它產生的 WAL 位元組。量之前先 CHECKPOINT，讓每次的 full-page write 起點一致。"""
        script = (
            "CHECKPOINT;\n"
            "SELECT pg_current_wal_insert_lsn() AS lsn0 \\gset\n"
            "\\timing on\n"
            f"{stmt.rstrip(';')};\n"
            "\\timing off\n"
            "SELECT 'WAL=' || pg_wal_lsn_diff(pg_current_wal_insert_lsn(), :'lsn0');\n"
        )
        out = self.sql(script)
        times = [float(m) for m in re.findall(r"Time: ([\d.]+) ms", out)]
        if not times:
            raise RuntimeError(f"psql 沒有印出 \\timing 的耗時：\n{out}")
        wal = int(float(grab(r"WAL=([\d.]+)", out)))
        return {"ms": round(sum(times), 2), "walBytes": wal}

    def explain(self, query: str, runs: int = 7, serialize: bool = False) -> dict:
        opts = "ANALYZE, BUFFERS, FORMAT JSON" + (", SERIALIZE" if serialize else "")
        self.sql(query)  # 暖快取：比較的是資料頁都在 shared_buffers 時，各寫法要碰多少頁
        samples = []
        for _ in range(runs):
            doc = json.loads(self.sql(f"EXPLAIN ({opts}) {query}"))[0]
            samples.append(doc)
        plan = samples[-1]["Plan"]
        result = {
            "medianMs": round(statistics.median(s["Execution Time"] for s in samples), 3),
            "sharedBlocks": plan.get("Shared Hit Blocks", 0) + plan.get("Shared Read Blocks", 0),
            "plan": plan_nodes(plan),
        }
        if serialize:
            ser = samples[-1].get("Serialization", {})
            result["serializeBlocks"] = ser.get("Shared Hit Blocks", 0) + ser.get("Shared Read Blocks", 0)
            result["serializeKB"] = ser.get("Output Volume")
        return result

    def pgbench(self, script: str, clients: int, seconds: int, env: dict | None = None) -> dict:
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as f:
            f.write(script)
            path = f.name
        threads = min(clients, 8)
        cmd = ["pgbench", "-n", *self.conn, "-c", str(clients), "-j", str(threads), "-T", str(seconds),
               "-f", path, DB]
        r = subprocess.run(cmd, text=True, capture_output=True, env={**C_LOCALE, **(env or {})})
        Path(path).unlink()
        out = r.stdout + r.stderr
        if r.returncode not in (0, 2) or "tps =" not in out:
            raise RuntimeError(f"pgbench 失敗：\n{out}")
        failed = re.search(r"number of failed transactions: (\d+)", out)
        return {
            "clients": clients,
            "seconds": seconds,
            "transactions": int(grab(r"number of transactions actually processed: (\d+)", out)),
            "failedTransactions": int(failed.group(1)) if failed else 0,
            "tps": round(float(grab(r"tps = ([\d.]+)", out)), 1),
            "latencyAvgMs": round(float(grab(r"latency average = ([\d.]+) ms", out)), 3),
        }


def grab(pattern: str, text: str) -> str:
    m = re.search(pattern, text)
    if m is None:
        raise RuntimeError(f"輸出裡找不到 {pattern!r}：\n{text}")
    return m.group(1)


def plan_nodes(plan: dict) -> list[str]:
    label = plan["Node Type"]
    if plan.get("Relation Name"):
        label += f" on {plan['Relation Name']}"
    if plan.get("Index Name"):
        label += f" using {plan['Index Name']}"
    nodes = [label]
    for child in plan.get("Plans", []):
        nodes += plan_nodes(child)
    return nodes


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(f"實測方向不成立：{msg}")


# ---------------------------------------------------------------- S7-01
def bench_review_cache(pg: Pg, scale: float) -> dict:
    n_books, n_reviews = 10_000, int(6_000_000 * scale)
    pg.sql(f"""
        DROP TABLE IF EXISTS reviews, books;
        CREATE TABLE books (book_id int PRIMARY KEY, title text NOT NULL,
                            review_count int NOT NULL DEFAULT 0, rating_sum int NOT NULL DEFAULT 0);
        CREATE TABLE reviews (review_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                              book_id int NOT NULL REFERENCES books, rating smallint NOT NULL,
                              created_at timestamptz NOT NULL);
        INSERT INTO books (book_id, title) SELECT g, 'book-' || g FROM generate_series(1, {n_books}) g;
        SELECT setseed(0.42);
        -- 熱門度偏斜：book_id 越小評價越多（random()^2），首頁的 1–20 號是熱門書，5001–5020 號是長尾
        INSERT INTO reviews (book_id, rating, created_at)
        SELECT 1 + floor(power(random(), 2) * {n_books})::int, 1 + floor(random() * 5)::int,
               timestamptz '2025-01-01' + random() * interval '600 days'
        FROM generate_series(1, {n_reviews});
        CREATE INDEX reviews_book_id ON reviews (book_id);
        UPDATE books b SET review_count = s.c, rating_sum = s.s
        FROM (SELECT book_id, count(*) c, sum(rating) s FROM reviews GROUP BY book_id) s WHERE s.book_id = b.book_id;
        VACUUM ANALYZE books; VACUUM ANALYZE reviews;
    """)
    live = ("SELECT b.book_id, b.title, round(avg(r.rating), 2), count(r.review_id) FROM books b "
            "LEFT JOIN reviews r ON r.book_id = b.book_id WHERE b.book_id BETWEEN {lo} AND {hi} "
            "GROUP BY b.book_id, b.title ORDER BY b.book_id")
    cache = ("SELECT book_id, title, round(rating_sum::numeric / NULLIF(review_count, 0), 2), review_count "
             "FROM books WHERE book_id BETWEEN {lo} AND {hi} ORDER BY book_id")
    pages = {"popular_page_1_20": (1, 20), "long_tail_page_5001_5020": (5001, 5020)}
    variants: dict = {"live_join_agg": {}, "live_join_agg_covering_index": {}, "counter_sum_cache_cols": {}}
    page_reviews = {k: pg.val(f"SELECT count(*) FROM reviews WHERE book_id BETWEEN {lo} AND {hi}")
                    for k, (lo, hi) in pages.items()}
    check(pg.sql(live.format(lo=1, hi=20)) == pg.sql(cache.format(lo=1, hi=20)), "快取欄與即時聚合的結果應相同")
    for k, (lo, hi) in pages.items():
        variants["live_join_agg"][k] = pg.explain(live.format(lo=lo, hi=hi))
        variants["counter_sum_cache_cols"][k] = pg.explain(cache.format(lo=lo, hi=hi))
    pg.sql("CREATE INDEX reviews_book_rating ON reviews (book_id) INCLUDE (rating); VACUUM ANALYZE reviews;")
    for k, (lo, hi) in pages.items():
        variants["live_join_agg_covering_index"][k] = pg.explain(
            live.format(lo=lo, hi=hi).replace("count(r.review_id)", "count(r.rating)"))
    pg.sql("DROP INDEX reviews_book_rating;")
    bench_read = "\\set p random(0, 49)\n" + live.format(lo="1 + :p * 200", hi="20 + :p * 200") + ";\n"
    bench_cache = "\\set p random(0, 49)\n" + cache.format(lo="1 + :p * 200", hi="20 + :p * 200") + ";\n"
    variants["live_join_agg"]["pgbench_8_clients"] = pg.pgbench(bench_read, 8, 10)
    variants["counter_sum_cache_cols"]["pgbench_8_clients"] = pg.pgbench(bench_cache, 8, 10)
    w_plain = "\\set b random(1, 10000)\nINSERT INTO reviews (book_id, rating, created_at) VALUES (:b, 4, now());\n"
    w_cache = ("\\set b random(1, 10000)\nBEGIN;\nINSERT INTO reviews (book_id, rating, created_at) VALUES (:b, 4, now());\n"
               "UPDATE books SET review_count = review_count + 1, rating_sum = rating_sum + 4 WHERE book_id = :b;\nCOMMIT;\n")
    # 先跑同交易更新快取欄的寫入並檢查漂移；純新增評價不更新快取欄，放在後面跑
    variants["counter_sum_cache_cols"]["write_pgbench_1_client"] = pg.pgbench(w_cache, 1, 5)
    drift = pg.val("SELECT count(*) FROM books b WHERE review_count <> (SELECT count(*) FROM reviews r WHERE r.book_id = b.book_id)")
    variants["live_join_agg"]["write_pgbench_1_client"] = pg.pgbench(w_plain, 1, 5)
    pg.sql("DROP TABLE reviews, books;")

    lv, cc, ci = variants["live_join_agg"], variants["counter_sum_cache_cols"], variants["live_join_agg_covering_index"]
    for k in pages:
        check(cc[k]["medianMs"] < lv[k]["medianMs"] and cc[k]["sharedBlocks"] < lv[k]["sharedBlocks"], f"{k} 快取欄應比即時聚合快、碰的頁少")
        check(cc[k]["medianMs"] < ci[k]["medianMs"], f"{k} 快取欄應比覆蓋索引的即時聚合快")
    check(cc["pgbench_8_clients"]["tps"] > lv["pgbench_8_clients"]["tps"], "快取欄的讀取吞吐量應高於即時聚合")
    check(drift == 0, "同交易更新快取欄之後不應有漂移")
    p, t = "popular_page_1_20", "long_tail_page_5001_5020"
    findings = [
        f"熱門頁（book_id 1–20，{page_reviews[p]:,} 筆評價）即時聚合 {lv[p]['medianMs']} ms、碰 {lv[p]['sharedBlocks']:,} 個資料頁；"
        f"補上 (book_id) INCLUDE (rating) 覆蓋索引後 {ci[p]['medianMs']} ms；讀快取欄 {cc[p]['medianMs']} ms、{cc[p]['sharedBlocks']} 個資料頁",
        f"長尾頁（book_id 5001–5020，{page_reviews[t]:,} 筆評價）即時聚合 {lv[t]['medianMs']} ms，快取欄 {cc[t]['medianMs']} ms：即時聚合的成本跟著這一頁的評價數成長，快取欄不會",
        f"8 條連線、每次隨機一頁：即時聚合 {lv['pgbench_8_clients']['tps']:,} TPS，快取欄 {cc['pgbench_8_clients']['tps']:,} TPS",
        f"寫入路徑：單一連線新增評價 {lv['write_pgbench_1_client']['latencyAvgMs']} ms，"
        f"同交易加上快取欄的 UPDATE 後 {cc['write_pgbench_1_client']['latencyAvgMs']} ms；寫入結束後快取欄與實際筆數不一致的書 {drift} 本",
    ]
    return {
        "benchmarkId": "pg-bookstore-review-agg-vs-cache-cols",
        "domain": "bookstore",
        "conceptIds": ["S7-01"],
        "title": "列表頁的平均星等與評價數：每次即時聚合 vs 讀 books 的快取欄（rating_sum、review_count）",
        "workload": "列表頁一次 20 本書；評價依熱門度偏斜分布",
        "scale": {"books": n_books, "reviews": n_reviews, "reviewsOnPage": page_reviews},
        "variants": variants,
        "findings": findings,
    }


# ---------------------------------------------------------------- S7-02
def bench_vertical_split(pg: Pg, scale: float) -> dict:
    n = int(50_000 * scale)
    core = "shipment_id bigint PRIMARY KEY, merchant_id int NOT NULL, warehouse_id int NOT NULL, status text NOT NULL, fee_cents int NOT NULL, created_at timestamptz NOT NULL"
    core_sel = ("g, 1 + g % 300, 1 + g % 12, (ARRAY['created','in_transit','delivered'])[1 + g % 3], 80 + g % 400, "
                "timestamptz '2026-01-01' + g * interval '1 minute'")
    # 報文用 md5 串成的十六進位字串：pglz 幾乎壓不動，8KB 的值一定被移到 TOAST，1KB 的值留在主表
    payload = "jsonb_build_object('raw', (SELECT string_agg(md5(g::text || ':' || k), '') FROM generate_series(1, {chunks}) k))"
    pg.sql(f"""
        DROP TABLE IF EXISTS ship_wide_8k, ship_wide_1k, ship_payload, ship_core;
        CREATE TABLE ship_wide_8k ({core}, payload jsonb NOT NULL);
        CREATE TABLE ship_wide_1k ({core}, payload jsonb NOT NULL);
        CREATE TABLE ship_core ({core});
        CREATE TABLE ship_payload (shipment_id bigint PRIMARY KEY REFERENCES ship_core, payload jsonb NOT NULL);
        INSERT INTO ship_wide_8k SELECT {core_sel}, {payload.format(chunks=256)} FROM generate_series(1, {n}) g;
        INSERT INTO ship_wide_1k SELECT {core_sel}, {payload.format(chunks=32)} FROM generate_series(1, {n}) g;
        INSERT INTO ship_core SELECT {core_sel} FROM generate_series(1, {n}) g;
        INSERT INTO ship_payload SELECT shipment_id, payload FROM ship_wide_8k;
        VACUUM ANALYZE ship_wide_8k; VACUUM ANALYZE ship_wide_1k; VACUUM ANALYZE ship_core; VACUUM ANALYZE ship_payload;
    """)
    tables = {"single_wide_table_8kb_payload": "ship_wide_8k", "single_wide_table_1kb_payload": "ship_wide_1k",
              "vertical_split_core": "ship_core"}
    variants: dict = {}
    for name, t in tables.items():
        v = {
            "heapBytes": pg.val(f"SELECT pg_relation_size('{t}')"),
            "toastBytes": pg.val(f"SELECT COALESCE(pg_relation_size(reltoastrelid), 0) FROM pg_class WHERE relname = '{t}'"),
            "list_scan_group_by_status": pg.explain(f"SELECT status, count(*), sum(fee_cents) FROM {t} GROUP BY status"),
            "list_page_core_columns": pg.explain(
                f"SELECT shipment_id, merchant_id, status, fee_cents, created_at FROM {t} ORDER BY shipment_id LIMIT 200", serialize=True),
            "list_page_select_star": pg.explain(f"SELECT * FROM {t} ORDER BY shipment_id LIMIT 200", serialize=True),
        }
        variants[name] = v
    variants["vertical_split_core"]["payloadTable"] = {
        "heapBytes": pg.val("SELECT pg_relation_size('ship_payload')"),
        "toastBytes": pg.val("SELECT pg_relation_size(reltoastrelid) FROM pg_class WHERE relname = 'ship_payload'"),
        "detail_lookup_by_pk": pg.explain(
            "SELECT c.*, p.payload FROM ship_core c JOIN ship_payload p USING (shipment_id) WHERE c.shipment_id = 31337", serialize=True),
    }
    for name, t in tables.items():
        variants[name]["update_status_10pct"] = pg.timed_with_wal(f"UPDATE {t} SET status = 'returned' WHERE shipment_id % 10 = 0")
    pg.sql("DROP TABLE ship_payload, ship_core, ship_wide_1k, ship_wide_8k;")

    w8, w1, sp = (variants[k] for k in tables)
    scan = "list_scan_group_by_status"
    check(w1[scan]["sharedBlocks"] > 3 * sp[scan]["sharedBlocks"], "1KB 報文留在主表時，列表掃描碰的頁應遠多於拆表")
    check(w8["toastBytes"] > 10 * w8["heapBytes"], "8KB 報文應被移到 TOAST")
    check(w8["list_page_select_star"]["serializeBlocks"] > 10 * max(1, w8["list_page_core_columns"]["serializeBlocks"]),
          "SELECT * 應把 TOAST 裡的報文讀回來")
    check(w1["update_status_10pct"]["walBytes"] > 2 * sp["update_status_10pct"]["walBytes"], "1KB 寬表改狀態的 WAL 應遠多於拆表")
    findings = [
        f"{n:,} 張運單。8KB 報文超過 TOAST 門檻，被移到 TOAST 表（主表 {w8['heapBytes'] // 1024:,} KB、TOAST {w8['toastBytes'] // 1048576:,} MB）；"
        f"1KB 報文低於門檻，留在主表（主表 {w1['heapBytes'] // 1048576:,} MB）；拆表後的核心表 {sp['heapBytes'] // 1024:,} KB",
        f"列表掃描（GROUP BY status）碰的資料頁：8KB 寬表 {w8[scan]['sharedBlocks']:,}、1KB 寬表 {w1[scan]['sharedBlocks']:,}、拆表核心表 {sp[scan]['sharedBlocks']:,}；"
        f"耗時 {w8[scan]['medianMs']} / {w1[scan]['medianMs']} / {sp[scan]['medianMs']} ms",
        f"8KB 寬表上 SELECT * 取 200 列，送出結果時要讀回 TOAST：{w8['list_page_select_star']['serializeBlocks']:,} 個資料頁、輸出 {w8['list_page_select_star']['serializeKB']:,} KB；"
        f"只選核心欄 {w8['list_page_core_columns']['serializeBlocks']} 個資料頁、{w8['list_page_core_columns']['serializeKB']} KB",
        f"把 10% 運單的 status 改掉產生的 WAL：8KB 寬表 {w8['update_status_10pct']['walBytes'] // 1024:,} KB（TOAST 裡的報文沒有重寫）、"
        f"1KB 寬表 {w1['update_status_10pct']['walBytes'] // 1024:,} KB、拆表核心表 {sp['update_status_10pct']['walBytes'] // 1024:,} KB",
    ]
    return {
        "benchmarkId": "pg-logistics-wide-table-vs-vertical-split",
        "domain": "swift-logistics",
        "conceptIds": ["S7-02"],
        "title": "運單核心欄與冷報文：同一張寬表（8KB／1KB 報文）vs 垂直拆成 shipments 與 shipment_payloads",
        "workload": "列表高頻讀核心欄、單張調閱才讀報文；狀態欄常更新",
        "scale": {"shipments": n, "payloadBytes": {"single_wide_table_8kb_payload": 8192, "single_wide_table_1kb_payload": 1024}},
        "variants": variants,
        "findings": findings,
    }


# ---------------------------------------------------------------- S7-03
def bench_hot_counter(pg: Pg, seconds: int) -> dict:
    pg.sql("""
        DROP TABLE IF EXISTS hot_counter, hot_buckets, hot_events;
        CREATE TABLE hot_counter (book_id int PRIMARY KEY, view_count bigint NOT NULL);
        CREATE TABLE hot_buckets (book_id int, bucket int, n bigint NOT NULL, PRIMARY KEY (book_id, bucket));
        CREATE TABLE hot_events (event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, book_id int NOT NULL,
                                 viewed_at timestamptz NOT NULL DEFAULT now());
        INSERT INTO hot_counter SELECT g, 0 FROM generate_series(1, 1000) g;
        INSERT INTO hot_buckets SELECT 201, b, 0 FROM generate_series(0, 31) b;
        VACUUM ANALYZE hot_counter; VACUUM ANALYZE hot_buckets;
    """)
    in_place = "UPDATE hot_counter SET view_count = view_count + 1 WHERE book_id = 201;\n"
    bucket = "\\set b random(0, 31)\nUPDATE hot_buckets SET n = n + 1 WHERE book_id = 201 AND bucket = :b;\n"
    append = "INSERT INTO hot_events (book_id) VALUES (201);\n"
    read_add_write = ("BEGIN;\nSELECT view_count AS v FROM hot_counter WHERE book_id = 202 \\gset\n"
                      "UPDATE hot_counter SET view_count = :v + 1 WHERE book_id = 202;\nCOMMIT;\n")
    size0 = pg.val("SELECT pg_relation_size('hot_counter')")
    v: dict = {}
    v["in_place_update_1_client"] = pg.pgbench(in_place, 1, seconds)
    v["in_place_update_32_clients"] = pg.pgbench(in_place, 32, seconds)
    v["in_place_update_32_clients"]["tableBytesBefore"] = size0
    v["in_place_update_32_clients"]["tableBytesAfter"] = pg.val("SELECT pg_relation_size('hot_counter')")
    total_in_place = v["in_place_update_1_client"]["transactions"] + v["in_place_update_32_clients"]["transactions"]
    check(pg.val("SELECT view_count FROM hot_counter WHERE book_id = 201") == total_in_place, "就地 UPDATE 不應遺失計數")
    v["bucketed_counter_32_slots_32_clients"] = pg.pgbench(bucket, 32, seconds)
    v["append_only_events_32_clients"] = pg.pgbench(append, 32, seconds)
    rw = pg.pgbench(read_add_write, 32, seconds)
    rw["finalCount"] = pg.val("SELECT view_count FROM hot_counter WHERE book_id = 202")
    rw["lostIncrements"] = rw["transactions"] - rw["finalCount"]
    v["app_read_then_write_32_clients"] = rw
    ser = pg.pgbench(in_place.replace("201", "203"), 32, seconds,
                     env={"PGOPTIONS": "-c default_transaction_isolation=serializable"})
    v["serializable_in_place_update_32_clients"] = ser
    check(pg.val("SELECT sum(n) FROM hot_buckets") == v["bucketed_counter_32_slots_32_clients"]["transactions"], "分桶計數加總應等於交易數")
    check(pg.val("SELECT count(*) FROM hot_events") == v["append_only_events_32_clients"]["transactions"], "事件列數應等於交易數")
    pg.sql("DROP TABLE hot_counter, hot_buckets, hot_events;")

    one, many = v["in_place_update_1_client"], v["in_place_update_32_clients"]
    bk, ap = v["bucketed_counter_32_slots_32_clients"], v["append_only_events_32_clients"]
    check(bk["tps"] > many["tps"] and ap["tps"] > many["tps"], "32 條連線下分桶與只新增事件的吞吐量應高於就地 UPDATE")
    check(many["latencyAvgMs"] > 2 * one["latencyAvgMs"], "連線變多時就地 UPDATE 的平均延遲應明顯上升")
    check(rw["lostIncrements"] > 0, "應用層先讀後寫應遺失計數")
    ser_failed_pct = 100 * ser["failedTransactions"] / (ser["transactions"] + ser["failedTransactions"])
    check(ser_failed_pct > 50, "SERIALIZABLE 下搶同一列，過半交易應因序列化失敗被中止")
    check(ser["tps"] < 2 * many["tps"], "SERIALIZABLE 成功的交易數不應明顯多於 READ COMMITTED")
    findings = [
        f"就地 UPDATE 同一列：1 條連線 {one['tps']:,} TPS、平均 {one['latencyAvgMs']} ms；32 條連線 {many['tps']:,} TPS、平均 {many['latencyAvgMs']} ms。"
        f"連線多了 32 倍，吞吐量是 {many['tps'] / one['tps']:.1f} 倍，每筆的等待時間變長",
        f"32 條連線下：32 個分桶 {bk['tps']:,} TPS（平均 {bk['latencyAvgMs']} ms），只新增事件列 {ap['tps']:,} TPS（平均 {ap['latencyAvgMs']} ms）",
        f"計數表（1,000 列，熱點只有 201 號）跑完就地 UPDATE 後從 {size0:,} bytes 長到 {many['tableBytesAfter']:,} bytes：每次 UPDATE 留下一個舊版本",
        f"應用層先 SELECT 再 UPDATE：{rw['transactions']:,} 次交易，計數只增加 {rw['finalCount']:,}，遺失 {rw['lostIncrements']:,} 次",
        f"SERIALIZABLE 下就地 UPDATE：{ser['transactions']:,} 次成功（{ser['tps']:,} TPS，READ COMMITTED 是 {many['tps']:,} TPS）、"
        f"{ser['failedTransactions']:,} 次因序列化失敗被中止（{ser_failed_pct:.0f}%）：成功的寫入沒有變多，被中止的要由應用層重試",
    ]
    return {
        "benchmarkId": "pg-bookstore-hot-row-counter",
        "domain": "bookstore",
        "conceptIds": ["S7-03"],
        "title": "熱門書的瀏覽計數：就地 UPDATE 同一列 vs 32 個分桶 vs 只新增事件列（另測應用層先讀後寫與 SERIALIZABLE）",
        "workload": f"pgbench 每組 {seconds} 秒，每筆交易一次計數",
        "scale": {"hotRows": 1, "buckets": 32},
        "variants": v,
        "findings": findings,
    }


# ---------------------------------------------------------------- S7-05
def bench_partition(pg: Pg, scale: float) -> dict:
    per_month = int(400_000 * scale)
    months = ["2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01", "2026-10-01", "2026-11-01"]
    cols = "event_id bigint NOT NULL, shipment_id bigint NOT NULL, scanner_tx_id text NOT NULL, status text NOT NULL, recorded_at timestamptz NOT NULL"
    parts = "\n".join(
        f"CREATE TABLE ev_part_{months[i][:7].replace('-', '_')} PARTITION OF ev_part FOR VALUES FROM ('{months[i]}') TO ('{months[i + 1]}');"
        for i in range(6))
    rows = (f"SELECT g, 1 + g / 4, 'tx-' || g, (ARRAY['picked','sorted','out_for_delivery','delivered'])[1 + g % 4], "
            f"date_trunc('month', timestamptz '2026-05-01' + ((g - 1) / {per_month}) * interval '1 month') "
            f"+ ((g - 1) % {per_month})::float / {per_month} * interval '28 days' FROM generate_series(1, {per_month * 6}) g")
    pg.sql(f"""
        DROP TABLE IF EXISTS ev_plain, ev_part;
        CREATE TABLE ev_plain ({cols}, PRIMARY KEY (event_id), UNIQUE (scanner_tx_id));
        CREATE INDEX ev_plain_recorded ON ev_plain (recorded_at);
        CREATE TABLE ev_part ({cols}, PRIMARY KEY (event_id, recorded_at), UNIQUE (scanner_tx_id, recorded_at))
            PARTITION BY RANGE (recorded_at);
        {parts}
        CREATE INDEX ev_part_recorded ON ev_part (recorded_at);
        INSERT INTO ev_plain {rows};
        INSERT INTO ev_part {rows};
        VACUUM ANALYZE ev_plain; VACUUM ANALYZE ev_part;
    """)
    ok, err = pg.try_sql("ALTER TABLE ev_part ADD CONSTRAINT ev_part_tx_global UNIQUE (scanner_tx_id);")
    check(not ok, "分區表上不含分區鍵的 UNIQUE 應建立失敗")
    unique_error = err.splitlines()[0].removeprefix("psql:<stdin>:1: ")
    prune = json.loads(pg.sql("EXPLAIN (FORMAT JSON) SELECT count(*) FROM ev_part WHERE recorded_at >= '2026-10-20'"))[0]["Plan"]
    scanned = sorted({n.split(" on ")[1].split(" ")[0] for n in plan_nodes(prune) if " on ev_part_" in n})
    total = lambda t: pg.val(f"SELECT pg_total_relation_size('{t}')")  # noqa: E731
    part_total = lambda: pg.val("SELECT sum(pg_total_relation_size(relid)) FROM pg_partition_tree('ev_part')")  # noqa: E731

    plain_before = total("ev_plain")
    d = pg.timed_with_wal("DELETE FROM ev_plain WHERE recorded_at < '2026-06-01'")
    d["rowsDeleted"] = per_month
    d["totalBytesBefore"] = plain_before
    d["totalBytesAfterDelete"] = total("ev_plain")
    pg.sql("VACUUM ev_plain;")
    d["totalBytesAfterVacuum"] = total("ev_plain")
    check(pg.val("SELECT count(*) FROM ev_plain WHERE recorded_at < '2026-06-01'") == 0, "DELETE 應清掉五月")

    part_before = part_total()
    p = pg.timed_with_wal("ALTER TABLE ev_part DETACH PARTITION ev_part_2026_05;\nDROP TABLE ev_part_2026_05")
    p["rowsRemoved"] = per_month
    p["totalBytesBefore"] = part_before
    p["totalBytesAfterDrop"] = part_total()
    p["partitionsScannedForLast12Days"] = scanned
    p["globalUniqueError"] = unique_error
    dup = "INSERT INTO {t} VALUES (999999999, 1, 'tx-dup', 'picked', '2026-07-15'), (999999998, 1, 'tx-dup', 'picked', '2026-09-15');"
    ok_part, _ = pg.try_sql(dup.format(t="ev_part"))
    ok_plain, _ = pg.try_sql(dup.format(t="ev_plain"))
    p["sameScannerTxIdInTwoMonthsAccepted"] = ok_part
    d["sameScannerTxIdInTwoMonthsAccepted"] = ok_plain
    pg.sql("DROP TABLE ev_plain, ev_part;")

    check(p["ms"] < d["ms"] and p["walBytes"] < d["walBytes"] / 10, "DROP 分區應比逐列 DELETE 快、WAL 少一個數量級以上")
    check(d["totalBytesAfterVacuum"] >= d["totalBytesBefore"] * 0.95, "一般 VACUUM 不會把空間還給作業系統")
    check(p["totalBytesAfterDrop"] < part_before * 0.9, "DROP 分區後總大小應下降")
    check(ok_part and not ok_plain, "分區表擋不住跨月重送，單表的全域 UNIQUE 擋得住")
    check(len(scanned) == 1, "最近 12 天的查詢應只掃一個分區")
    findings = [
        f"清掉最舊一個月（{per_month:,} 列）：逐列 DELETE {d['ms']:,} ms、產生 WAL {d['walBytes'] // 1048576:,} MB；"
        f"DETACH 加 DROP 分區 {p['ms']:,} ms、WAL {p['walBytes'] // 1024:,} KB",
        f"DELETE 前後表加索引都是 {d['totalBytesBefore'] // 1048576:,} MB → {d['totalBytesAfterDelete'] // 1048576:,} MB，"
        f"跑完一般 VACUUM 仍是 {d['totalBytesAfterVacuum'] // 1048576:,} MB：空間留給之後的寫入重用，不還給作業系統；"
        f"DROP 分區後總大小 {part_before // 1048576:,} MB → {p['totalBytesAfterDrop'] // 1048576:,} MB",
        f"在分區表加不含分區鍵的 UNIQUE (scanner_tx_id)：{unique_error}",
        f"同一個 scanner_tx_id 分別寫進七月與九月：分區表上的 UNIQUE (scanner_tx_id, recorded_at) 兩筆都收下；單表的 UNIQUE (scanner_tx_id) 擋下第二筆",
        f"查最近 12 天的事件，分區裁剪後只掃 {', '.join(scanned)}",
    ]
    return {
        "benchmarkId": "pg-logistics-partition-drop-vs-delete",
        "domain": "swift-logistics",
        "conceptIds": ["S7-05"],
        "title": "事件表過期清理：單表逐列 DELETE vs 按月 Range 分區 DETACH + DROP；分區表的唯一約束",
        "workload": "6 個月的掃描事件，清掉最舊的一個月",
        "scale": {"rowsPerMonth": per_month, "months": 6},
        "variants": {"batch_delete": d, "range_partition_drop": p},
        "findings": findings,
    }


BENCHES = {
    "review-cache": lambda pg, a: bench_review_cache(pg, a.scale),
    "vertical-split": lambda pg, a: bench_vertical_split(pg, a.scale),
    "hot-counter": lambda pg, a: bench_hot_counter(pg, a.seconds),
    "partition": lambda pg, a: bench_partition(pg, a.scale),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=55432)
    ap.add_argument("--user", default="postgres")
    ap.add_argument("--out", type=Path, help="快照 JSON 的輸出路徑；不給時印到標準輸出")
    ap.add_argument("--only", choices=sorted(BENCHES), action="append", help="只跑指定的組，可重複")
    ap.add_argument("--scale", type=float, default=1.0, help="資料量倍率（預設 1.0：600 萬評價、5 萬運單、240 萬事件）")
    ap.add_argument("--seconds", type=int, default=10, help="熱點列每組 pgbench 的秒數")
    args = ap.parse_args()

    pg = Pg(args.host, args.port, args.user)
    pg.sql(f"DROP DATABASE IF EXISTS {DB};", db="postgres")
    pg.sql(f"CREATE DATABASE {DB};", db="postgres")
    env = {
        "engine": pg.sql("SELECT version()"),
        "sharedBuffers": pg.sql("SHOW shared_buffers"),
        "cpus": int(pg.sql("SELECT count(*) FROM pg_ls_dir('/sys/devices/system/cpu') d WHERE d ~ '^cpu[0-9]+$'") or 0),
        "pgbenchClient": subprocess.run(["pgbench", "--version"], text=True, capture_output=True).stdout.strip(),
    }
    results = []
    try:
        for name in args.only or list(BENCHES):
            print(f"[run] {name}", file=sys.stderr)
            results.append(BENCHES[name](pg, args))
    except AssertionError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 1
    finally:
        pg.sql(f"DROP DATABASE IF EXISTS {DB};", db="postgres")
    snapshot = {
        "schemaVersion": "1.0",
        "measurementSource": "live-postgres-measured",
        "generatedBy": "scripts/sql-practice/pg_workload_bench.py",
        "note": "在拋棄式 PostgreSQL 容器實跑；耗時與 TPS 隨主機負載浮動，資料頁數、WAL 數量級、計數與錯誤訊息可重現。",
        "environment": env,
        "scaleFactor": args.scale,
        "benchmarks": results,
    }
    text = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    for b in results:
        print(f"\n== {b['benchmarkId']}", file=sys.stderr)
        for f in b["findings"]:
            print(f"  - {f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
