#!/usr/bin/env python3
"""驗證三套 SQL 練習領域資料庫（bookstore / cloud-academy / swift-logistics）：
1. schema.sql 與 seed.sql 在 PRAGMA foreign_keys = ON 下能完整建庫
2. PRAGMA foreign_key_check 與 PRAGMA integrity_check 零錯誤
3. 每個領域刻意埋設的邊界反例列確實能觸發對應的 SQL 陷阱差異
"""

from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parent / "domains"


def load_domain(name: str) -> sqlite3.Connection:
    domain_dir = ROOT / name
    schema_sql = (domain_dir / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (domain_dir / "seed.sql").read_text(encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(schema_sql)
    conn.executescript(seed_sql)

    fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
    assert fk_errors == [], f"{name}: foreign_key_check 失敗：{fk_errors}"

    integrity = conn.execute("PRAGMA integrity_check;").fetchall()
    assert integrity == [("ok",)], f"{name}: integrity_check 失敗：{integrity}"

    return conn


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

    # 1. COUNT(*) vs COUNT(o.order_id) 在未下單顧客（雅文 id=3）上分岔
    wrong_cnt = conn.execute(
        "SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE c.customer_id = 3;"
    ).fetchone()[0]
    right_cnt = conn.execute(
        "SELECT COUNT(o.order_id) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE c.customer_id = 3;"
    ).fetchone()[0]
    assert wrong_cnt == 1 and right_cnt == 0, f"未下單計數陷阱未觸發：{wrong_cnt}, {right_cnt}"

    # 2. ON vs WHERE + OR o.order_id IS NULL：顧客 4（2 月有單、3 月無單）仍會被錯漏
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

    # 3. NOT IN 遇 reviews.order_id IS NULL 靜默回傳 0 列；NOT EXISTS 回傳正確訂單集合
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

    # 4. 訂單 101 雙重膨脹（2 則評價讓 900 變 1800）
    inflated = conn.execute(
        "SELECT SUM(o.total_amount) FROM orders o LEFT JOIN reviews r ON r.order_id = o.order_id WHERE o.order_id = 101;"
    ).fetchone()[0]
    assert inflated == 1800, f"列數膨脹應為 1800，實得 {inflated}"

    # 5. BETWEEN '2026-03-31' 漏掉月底深夜訂單 107
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

    # 6. 視窗函式 LAG() 未檢查日期差時會把公休後 03-04 誤判為高於「前一天」
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

    # 7. C06 整數除法陷阱：SQLite 下退款率永遠為 0
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

    # 1. C01：NOT IN 遇 invoices.sub_id IS NULL 且 paid 靜默回空；NOT EXISTS 找出無付費帳單的 active 訂閱 2003、2005
    not_in_rows = conn.execute(
        "SELECT sub_id FROM subscriptions WHERE status = 'active' AND sub_id NOT IN (SELECT sub_id FROM invoices WHERE status = 'paid');"
    ).fetchall()
    not_exists_ids = {
        r[0]
        for r in conn.execute(
            "SELECT s.sub_id FROM subscriptions s WHERE s.status = 'active' AND NOT EXISTS (SELECT 1 FROM invoices i WHERE i.sub_id = s.sub_id AND i.status = 'paid');"
        ).fetchall()
    }
    # 錯誤寫法 D（<> 'paid' OR IS NULL）會把同時有 paid 與 void 的訂閱 2002 錯抓進來
    wrong_d_ids = {
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT s.sub_id FROM subscriptions s LEFT JOIN invoices i ON i.sub_id = s.sub_id WHERE s.status = 'active' AND (i.status <> 'paid' OR i.invoice_id IS NULL);"
        ).fetchall()
    }
    assert not_in_rows == []
    assert not_exists_ids == {2003, 2005}
    assert 2002 in wrong_d_ids and 2002 not in not_exists_ids

    # 2. 雙重一對多膨脹：學員 1 有兩筆訂閱、多筆帳單與多筆課程進度
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

    # 3. 重複 webhook 偵測
    dup_webhooks = conn.execute(
        "SELECT provider, external_id FROM webhook_events GROUP BY provider, external_id HAVING COUNT(*) > 1;"
    ).fetchall()
    assert dup_webhooks == [("stripe", "evt_dup_001")]


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

    # 1. C03：運單 7002 含 recorded_at IS NULL 的 exception 事件；SQLite DESC 預設 NULL 排最後，顯式 NULLS FIRST 會反轉
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

    # 2. C04：混合方向 (created_at DESC, shipment_id ASC) 誤用列值比較 < 會漏掉同秒較大 shipment_id
    # 第一頁取 1 筆：7005 (2026-03-15 14:00:00, id=7005)
    # 下一頁正確應看到 7006、7007、7008；誤用 (created_at, shipment_id) < ('2026-03-15 14:00:00', 7005) 會漏 7006 與 7007
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

    # 3. 孤兒事件 shipment_id IS NULL 觸發 NOT IN 回空
    not_in_shipments = conn.execute(
        "SELECT shipment_id FROM shipments WHERE shipment_id NOT IN (SELECT shipment_id FROM shipment_events WHERE event_type = 'exception');"
    ).fetchall()
    assert not_in_shipments == []

    # 4. 部分索引命中檢查（queued 查詢應使用 idx_dispatch_queued）
    plan_text = "\n".join(
        str(r)
        for r in conn.execute(
            "EXPLAIN QUERY PLAN SELECT task_id FROM dispatch_tasks WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1;"
        ).fetchall()
    )
    assert "idx_dispatch_queued" in plan_text, f"部分索引未命中：{plan_text}"


def main() -> int:
    verifiers = [
        ("bookstore", verify_bookstore),
        ("cloud-academy", verify_cloud_academy),
        ("swift-logistics", verify_swift_logistics),
    ]
    for name, fn in verifiers:
        conn = load_domain(name)
        try:
            fn(conn)
            table_count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
            ).fetchone()[0]
            print(f"OK  {name}: {table_count} tables, foreign_key_check=0, integrity=ok, edge-case assertions passed")
        finally:
            conn.close()
    print(f"verify_domains: {len(verifiers)} domain(s) verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
