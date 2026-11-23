#!/usr/bin/env python3
"""驗證三套 SQL 練習領域資料庫（bookstore / cloud-academy / swift-logistics）：
1. 基礎層（schema.sql + seed.sql）：外鍵、完整性與全部邊界反例 SQL 斷言
2. 壓測層（疊加 seed_scale.sql）：ID 區段零撞號、外鍵與完整性，以及執行計畫／效能差距驗證
"""

from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parent / "domains"


def load_domain(name: str, with_scale: bool = False) -> sqlite3.Connection:
    domain_dir = ROOT / name
    schema_sql = (domain_dir / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (domain_dir / "seed.sql").read_text(encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(schema_sql)
    conn.executescript(seed_sql)
    if with_scale:
        scale_sql = (domain_dir / "seed_scale.sql").read_text(encoding="utf-8")
        conn.executescript(scale_sql)

    fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
    assert fk_errors == [], f"{name} (scale={with_scale}): foreign_key_check 失敗：{fk_errors}"

    integrity = conn.execute("PRAGMA integrity_check;").fetchall()
    assert integrity == [("ok",)], f"{name} (scale={with_scale}): integrity_check 失敗：{integrity}"

    return conn


def explain_text(conn: sqlite3.Connection, sql: str) -> str:
    rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
    return "\n".join(str(r[-1]) for r in rows)


def verify_bookstore(conn: sqlite3.Connection) -> None:
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
    }
    expected = {
        "customers",
        "categories",
        "books",
        "orders",
        "order_items",
        "reviews",
        "coupons",
        "order_coupons",
        "daily_sales_snapshots",
        "export_jobs",
        "store_shifts",
        "book_details",
        "book_view_events",
    }
    assert tables == expected, f"bookstore 表集合不符：{tables ^ expected}"

    wrong_cnt = conn.execute(
        "SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE c.customer_id = 3;"
    ).fetchone()[0]
    right_cnt = conn.execute(
        "SELECT COUNT(o.order_id) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE c.customer_id = 3;"
    ).fetchone()[0]
    assert wrong_cnt == 1 and right_cnt == 0, f"未下單計數陷阱未觸發：{wrong_cnt}, {right_cnt}"

    where_or_ids = {
        r[0]
        for r in conn.execute(
            """
            SELECT DISTINCT c.customer_id FROM customers c
            LEFT JOIN orders o ON o.customer_id = c.customer_id
            WHERE (o.status = 'paid' AND o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01')
               OR o.order_id IS NULL;
            """
        ).fetchall()
    }
    on_ids = {
        r[0]
        for r in conn.execute(
            """
            SELECT DISTINCT c.customer_id FROM customers c
            LEFT JOIN orders o
              ON o.customer_id = c.customer_id
             AND o.status = 'paid'
             AND o.ordered_at >= '2026-03-01'
             AND o.ordered_at < '2026-04-01';
            """
        ).fetchall()
    }
    assert 4 not in where_or_ids and 4 in on_ids, "顧客 4（2 月有單、3 月無單）反例未觸發"

    not_in_rows = conn.execute(
        "SELECT order_id FROM orders WHERE order_id NOT IN (SELECT order_id FROM reviews WHERE rating = 5);"
    ).fetchall()
    not_exists_ids = {
        r[0]
        for r in conn.execute(
            "SELECT o.order_id FROM orders o WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = o.order_id AND r.rating = 5);"
        ).fetchall()
    }
    assert not_in_rows == [], f"NOT IN 應受 NULL 影響回傳 0 列，實得 {not_in_rows}"
    assert 102 in not_exists_ids and 103 in not_exists_ids and 101 not in not_exists_ids

    inflated = conn.execute(
        "SELECT SUM(o.total_amount) FROM orders o LEFT JOIN reviews r ON r.order_id = o.order_id WHERE o.order_id = 101;"
    ).fetchone()[0]
    assert inflated == 1800, f"列數膨脹應為 1800，實得 {inflated}"

    between_ids = {
        r[0]
        for r in conn.execute(
            "SELECT order_id FROM orders WHERE ordered_at BETWEEN '2026-03-01' AND '2026-03-31';"
        ).fetchall()
    }
    half_open_ids = {
        r[0]
        for r in conn.execute(
            "SELECT order_id FROM orders WHERE ordered_at >= '2026-03-01 00:00:00' AND ordered_at < '2026-04-01 00:00:00';"
        ).fetchall()
    }
    assert 107 not in between_ids and 107 in half_open_ids, "月底深夜訂單 107 反例未觸發"

    lag_no_gap = conn.execute(
        """
        SELECT snapshot_date FROM (
          SELECT snapshot_date, revenue,
                 LAG(revenue) OVER (PARTITION BY store_code ORDER BY snapshot_date) AS prev_rev
          FROM daily_sales_snapshots WHERE store_code = 'TPE-01'
        ) WHERE revenue > prev_rev;
        """
    ).fetchall()
    lag_with_gap = conn.execute(
        """
        SELECT snapshot_date FROM (
          SELECT snapshot_date, revenue,
                 LAG(revenue) OVER (PARTITION BY store_code ORDER BY snapshot_date) AS prev_rev,
                 LAG(snapshot_date) OVER (PARTITION BY store_code ORDER BY snapshot_date) AS prev_date
          FROM daily_sales_snapshots WHERE store_code = 'TPE-01'
        ) WHERE prev_date = date(snapshot_date, '-1 day') AND revenue > prev_rev;
        """
    ).fetchall()
    assert [r[0] for r in lag_no_gap] == ["2026-03-02", "2026-03-04"]
    assert [r[0] for r in lag_with_gap] == ["2026-03-02"]

    zero_rows = conn.execute(
        """
        SELECT b.category_id
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
        JOIN books b ON b.book_id = oi.book_id
        GROUP BY b.category_id
        HAVING COUNT(CASE WHEN o.status = 'refunded' THEN 1 END) / COUNT(*) > 0.1;
        """
    ).fetchall()
    assert zero_rows == [], f"整數除法應回傳 0 列，實得 {zero_rows}"


def verify_bookstore_scale(conn: sqlite3.Connection) -> None:
    order_cnt = conn.execute("SELECT COUNT(*) FROM orders;").fetchone()[0]
    hot_cnt = conn.execute("SELECT COUNT(*) FROM customers WHERE email = 'hot@bookstore.tw';").fetchone()[0]
    assert order_cnt == 50009, f"orders 規模列數不符：{order_cnt}"
    assert hot_cnt == 2000, f"熱點 email 列數不符：{hot_cnt}"

    # 計畫分岔：non-sargable 掃全表 vs half-open 走 idx_orders_ordered_id
    p_bad = explain_text(conn, "SELECT order_id FROM orders WHERE substr(ordered_at, 1, 7) = '2025-06';")
    p_good = explain_text(
        conn,
        "SELECT order_id FROM orders WHERE ordered_at >= '2025-06-01 00:00:00' AND ordered_at < '2025-07-01 00:00:00';",
    )
    assert "SCAN orders" in p_bad and "SEARCH orders USING" in p_good, f"Sargable 計畫未分岔：\n{p_bad}\nvs\n{p_good}"

    # 部分索引命中：20,011 筆 export_jobs 僅靠 idx_export_jobs_queued 定位 7 筆 queued
    p_partial = explain_text(
        conn, "SELECT job_id FROM export_jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1;"
    )
    assert "idx_export_jobs_queued" in p_partial, f"export_jobs 部分索引未命中：{p_partial}"


def verify_cloud_academy(conn: sqlite3.Connection) -> None:
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
    }
    expected = {
        "users",
        "courses",
        "course_contents",
        "tags",
        "course_tags",
        "subscriptions",
        "invoices",
        "lesson_progress",
        "certificates",
        "webhook_events",
    }
    assert tables == expected, f"cloud-academy 表集合不符：{tables ^ expected}"

    not_in_rows = conn.execute(
        "SELECT sub_id FROM subscriptions WHERE status = 'active' AND sub_id NOT IN (SELECT sub_id FROM invoices WHERE status = 'paid');"
    ).fetchall()
    not_exists_ids = {
        r[0]
        for r in conn.execute(
            "SELECT s.sub_id FROM subscriptions s WHERE s.status = 'active' AND NOT EXISTS (SELECT 1 FROM invoices i WHERE i.sub_id = s.sub_id AND i.status = 'paid');"
        ).fetchall()
    }
    wrong_d_ids = {
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT s.sub_id FROM subscriptions s LEFT JOIN invoices i ON i.sub_id = s.sub_id WHERE s.status = 'active' AND (i.status <> 'paid' OR i.invoice_id IS NULL);"
        ).fetchall()
    }
    assert not_in_rows == []
    assert not_exists_ids == {2003, 2005}
    assert 2002 in wrong_d_ids and 2002 not in not_exists_ids

    raw_invoice_sum = conn.execute(
        "SELECT SUM(i.amount) FROM subscriptions s JOIN invoices i ON i.sub_id = s.sub_id WHERE s.user_id = 1 AND i.status = 'paid';"
    ).fetchone()[0]
    inflated_sum = conn.execute(
        """
        SELECT SUM(i.amount)
        FROM subscriptions s
        JOIN invoices i ON i.sub_id = s.sub_id
        JOIN lesson_progress lp ON lp.user_id = s.user_id
        WHERE s.user_id = 1 AND i.status = 'paid';
        """
    ).fetchone()[0]
    assert inflated_sum == raw_invoice_sum * 3, "雲課堂雙重膨脹反例未觸發"

    dup_webhooks = conn.execute(
        "SELECT provider, external_id FROM webhook_events GROUP BY provider, external_id HAVING COUNT(*) > 1;"
    ).fetchall()
    assert dup_webhooks == [("stripe", "evt_dup_001")]


def verify_cloud_academy_scale(conn: sqlite3.Connection) -> None:
    inv_cnt = conn.execute("SELECT COUNT(*) FROM invoices;").fetchone()[0]
    storm_cnt = conn.execute(
        "SELECT COUNT(*) FROM webhook_events WHERE external_id = 'evt_storm_hot';"
    ).fetchone()[0]
    assert inv_cnt == 50007, f"invoices 規模列數不符：{inv_cnt}"
    assert storm_cnt == 1500, f"webhook 重送風暴列數不符：{storm_cnt}"

    p_partial = explain_text(
        conn, "SELECT event_id FROM webhook_events WHERE status = 'pending' ORDER BY received_at ASC LIMIT 1;"
    )
    assert "idx_webhook_pending" in p_partial, f"webhook 部分索引未命中：{p_partial}"


def verify_swift_logistics(conn: sqlite3.Connection) -> None:
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
    }
    expected = {
        "warehouses",
        "merchants",
        "shipments",
        "shipment_packages",
        "shipment_payloads",
        "shipment_events",
        "driver_shifts",
        "dispatch_tasks",
        "billing_statements",
    }
    assert tables == expected, f"swift-logistics 表集合不符：{tables ^ expected}"

    sqlite_default_top = conn.execute(
        """
        SELECT event_type FROM (
          SELECT event_type,
                 ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY recorded_at DESC) AS rn
          FROM shipment_events WHERE shipment_id = 7002
        ) WHERE rn = 1;
        """
    ).fetchone()[0]
    pg_like_top = conn.execute(
        """
        SELECT event_type FROM (
          SELECT event_type,
                 ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY recorded_at DESC NULLS FIRST) AS rn
          FROM shipment_events WHERE shipment_id = 7002
        ) WHERE rn = 1;
        """
    ).fetchone()[0]
    assert sqlite_default_top == "signed" and pg_like_top == "exception", "C03 NULL 排序跨引擎反例未觸發"

    bad_next = [
        r[0]
        for r in conn.execute(
            """
            SELECT shipment_id FROM shipments
            WHERE warehouse_id = 11 AND status = 'in_transit'
              AND (created_at, shipment_id) < ('2026-03-15 14:00:00', 7005)
            ORDER BY created_at DESC, shipment_id ASC;
            """
        ).fetchall()
    ]
    good_next = [
        r[0]
        for r in conn.execute(
            """
            SELECT shipment_id FROM shipments
            WHERE warehouse_id = 11 AND status = 'in_transit'
              AND (created_at < '2026-03-15 14:00:00'
                   OR (created_at = '2026-03-15 14:00:00' AND shipment_id > 7005))
            ORDER BY created_at DESC, shipment_id ASC;
            """
        ).fetchall()
    ]
    assert bad_next == [7008], f"C04 錯誤列值比較應漏 7006/7007，實得 {bad_next}"
    assert good_next == [7006, 7007, 7008], f"C04 展開式應回傳 7006/7007/7008，實得 {good_next}"

    not_in_shipments = conn.execute(
        "SELECT shipment_id FROM shipments WHERE shipment_id NOT IN (SELECT shipment_id FROM shipment_events WHERE event_type = 'exception');"
    ).fetchall()
    assert not_in_shipments == []

    p_partial = explain_text(
        conn, "SELECT task_id FROM dispatch_tasks WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1;"
    )
    assert "idx_dispatch_queued" in p_partial, f"部分索引未命中：{p_partial}"


def verify_swift_logistics_scale(conn: sqlite3.Connection) -> None:
    ship_cnt = conn.execute("SELECT COUNT(*) FROM shipments;").fetchone()[0]
    skew_cnt = conn.execute("SELECT COUNT(*) FROM shipments WHERE merchant_id = 1001;").fetchone()[0]
    assert ship_cnt == 50008, f"shipments 規模列數不符：{ship_cnt}"
    assert skew_cnt / ship_cnt >= 0.34, f"大客戶資料傾斜比例不足：{skew_cnt}/{ship_cnt}"

    p_partial = explain_text(
        conn, "SELECT task_id FROM dispatch_tasks WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1;"
    )
    assert "idx_dispatch_queued" in p_partial, f"規模壓測下 dispatch_tasks 部分索引未命中：{p_partial}"

    p_keyset = explain_text(
        conn,
        """
        SELECT shipment_id FROM shipments
        WHERE warehouse_id = 11 AND status = 'in_transit'
          AND created_at < '2025-10-01 00:00:00'
        ORDER BY created_at DESC, shipment_id ASC LIMIT 30;
        """,
    )
    assert "idx_shipments_wh_status_created" in p_keyset, f"複合索引未命中：{p_keyset}"


def main() -> int:
    verifiers = [
        ("bookstore", verify_bookstore, verify_bookstore_scale),
        ("cloud-academy", verify_cloud_academy, verify_cloud_academy_scale),
        ("swift-logistics", verify_swift_logistics, verify_swift_logistics_scale),
    ]
    for name, fn_base, fn_scale in verifiers:
        conn = load_domain(name, with_scale=False)
        try:
            fn_base(conn)
            table_count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
            ).fetchone()[0]
            print(f"OK  {name} [base ]: {table_count} tables, fk=0, integrity=ok, edge-case assertions passed")
        finally:
            conn.close()

        t0 = time.perf_counter()
        conn_s = load_domain(name, with_scale=True)
        seed_ms = (time.perf_counter() - t0) * 1000
        try:
            fn_scale(conn_s)
            print(f"OK  {name} [scale]: seeded in {seed_ms:.1f}ms, fk=0, integrity=ok, plan/skew assertions passed")
        finally:
            conn_s.close()

    print(f"verify_domains: {len(verifiers)} domain(s) verified (base + scale)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
