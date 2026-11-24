#!/usr/bin/env python3
"""在 PostgreSQL 實跑三套領域的 schema_pg.sql + seed.sql + security_pg.sql，驗證：
1. DDL、seed 與角色腳本在 PostgreSQL 可完整執行（ON_ERROR_STOP）
2. 以各角色身分查詢時，RLS 租戶隔離、BI 唯讀邊界、唯附寫稽核與檢視表擁有者設定的實際行為
3. 題庫宣稱的跨引擎差異（NULL 排序、SELECT 別名、非分組欄位）在 PostgreSQL 確實成立

用法（純 Python 3 標準函式庫，需要 PATH 上有 initdb / pg_ctl / psql）：
  python3 scripts/sql-practice/verify_pg.py              # 在暫存目錄建立拋棄式叢集，跑完即停機並刪除
  python3 scripts/sql-practice/verify_pg.py --dsn-port 5433 --dsn-host localhost --dsn-user postgres
                                                         # 改連既有的拋棄式叢集（角色是叢集層級物件，叢集內不可已有同名角色）
"""

import argparse
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent / "domains"
DOMAINS = ["bookstore", "cloud-academy", "swift-logistics"]


class Pg:
    def __init__(self, host: str, port: int, user: str):
        self.base = ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", host, "-p", str(port), "-U", user]

    def run_file(self, db: str, sql: str) -> None:
        r = subprocess.run(self.base + ["-d", db], input=sql, text=True, capture_output=True)
        if r.returncode != 0:
            raise AssertionError(f"[{db}] 執行 SQL 失敗：\n{r.stderr.strip()}")

    def query(self, db: str, sql: str, role: str | None = None, settings: dict | None = None) -> tuple[bool, str]:
        """在單一交易內以 SET LOCAL ROLE 與 SET LOCAL app.* 執行查詢；回傳 (成功與否, 輸出或錯誤訊息)。"""
        lines = ["BEGIN;"]
        if role:
            lines.append(f"SET LOCAL ROLE {role};")
        for k, v in (settings or {}).items():
            lines.append(f"SET LOCAL {k} = '{v}';")
        lines += [sql.rstrip(";") + ";", "ROLLBACK;"]
        r = subprocess.run(
            self.base + ["-d", db, "-At", "-F", ","], input="\n".join(lines), text=True, capture_output=True
        )
        if r.returncode != 0:
            return False, r.stderr.strip()
        return True, r.stdout.strip()


def rows(pg: Pg, db: str, sql: str, **kw) -> list[str]:
    ok, out = pg.query(db, sql, **kw)
    assert ok, f"[{db}] 預期成功卻報錯：{sql}\n{out}"
    return [line for line in out.splitlines() if line]


def expect_error(pg: Pg, db: str, sql: str, needle: str, **kw) -> None:
    ok, out = pg.query(db, sql, **kw)
    assert not ok, f"[{db}] 預期報錯卻成功：{sql}\n{out}"
    assert needle in out, f"[{db}] 錯誤訊息應含 {needle!r}：{out}"


def expect_rows(pg: Pg, db: str, sql: str, expected: list[str], label: str, **kw) -> None:
    got = rows(pg, db, sql, **kw)
    assert got == expected, f"[{db}] {label}：預期 {expected}，實得 {got}"


def load_domain(pg: Pg, name: str) -> str:
    db = "sqlpractice_" + name.replace("-", "_")
    pg.run_file("postgres", f"DROP DATABASE IF EXISTS {db};\nCREATE DATABASE {db};\nALTER DATABASE {db} SET timezone = 'UTC';")
    d = ROOT / name
    pg.run_file(db, (d / "schema_pg.sql").read_text(encoding="utf-8"))
    seed = "\n".join(
        line for line in (d / "seed.sql").read_text(encoding="utf-8").splitlines() if not line.startswith("PRAGMA")
    )
    pg.run_file(db, seed)
    pg.run_file(db, (d / "security_pg.sql").read_text(encoding="utf-8"))
    return db


def verify_bookstore(pg: Pg, db: str) -> None:
    app, bi, mig = "bookstore_app_login", "bookstore_bi_login", "bookstore_migrator_login"
    sql = "SELECT job_id FROM export_jobs ORDER BY job_id"
    expect_rows(pg, db, sql, ["501", "503", "504", "505"], "門市 TPE-01 只看到自己門市的任務",
                role=app, settings={"app.current_store_code": "TPE-01"})
    expect_rows(pg, db, sql, ["501", "502", "503", "504", "505"], "加上全域旗標才看得到跨門市任務 502",
                role=app, settings={"app.current_store_code": "TPE-01", "app.is_global_scope": "true"})
    expect_rows(pg, db, sql, [], "漏設門市上下文時 fail-closed 回 0 列", role=app)
    expect_rows(pg, db, "SELECT count(*) FROM v_customer_analytics", ["7"], "BI 透過檢視表讀到全部顧客", role=bi)
    expect_error(pg, db, "SELECT email FROM customers", "permission denied", role=bi)
    expect_error(pg, db, "SELECT * FROM customer_pii", "permission denied", role=bi)
    expect_error(pg, db, "UPDATE order_audit_logs SET reason = 'x' WHERE audit_id = 1", "permission denied", role=app)
    expect_error(pg, db, "TRUNCATE order_audit_logs", "permission denied", role=app)
    expect_error(pg, db, "UPDATE order_audit_logs SET reason = 'x' WHERE audit_id = 1", "append-only", role=mig)
    expect_rows(pg, db, "SELECT reloptions::text FROM pg_class WHERE relname = 'v_active_staff_permissions'",
                ["{security_barrier=true}"], "v_active_staff_permissions 設有 security_barrier")
    # 跨引擎差異：SELECT 別名不能用在 WHERE（S2-01）、非分組欄位（S5-03 opt_bad_group_by）
    expect_error(pg, db, "SELECT order_item_id, quantity * unit_price AS line_total FROM order_items WHERE line_total > 500",
                 "does not exist")
    expect_error(pg, db, "SELECT book_id, price, AVG(price) FROM books WHERE is_active = 1 GROUP BY category_id HAVING price > AVG(price)",
                 "must appear in the GROUP BY")


def verify_cloud_academy(pg: Pg, db: str) -> None:
    app, bi = "academy_app_login", "academy_bi_login"
    sql = "SELECT sub_id FROM subscriptions ORDER BY sub_id"
    expect_rows(pg, db, sql, ["2001", "2002"], "學員 1 只看到自己的訂閱", role=app, settings={"app.current_user_id": "1"})
    expect_rows(pg, db, sql, ["2002", "2003"], "學員 2 在組織 501 下另看到企業訂閱 2002",
                role=app, settings={"app.current_user_id": "2", "app.current_org_id": "501"})
    expect_rows(pg, db, "SELECT user_id FROM org_memberships ORDER BY user_id", ["1", "2"], "組織 501 的成員",
                role=app, settings={"app.current_org_id": "501"})
    expect_rows(pg, db, "SELECT count(*) FROM subscriptions", ["6"], "BI 靠顯式唯讀政策讀到全部訂閱", role=bi)
    expect_rows(pg, db, "SELECT count(*) FROM v_learner_analytics", ["6"], "BI 透過檢視表讀到全部學員", role=bi)
    expect_error(pg, db, "SELECT email FROM users", "permission denied", role=bi)
    expect_rows(pg, db, "SELECT session_id FROM v_valid_sessions WHERE expires_at > '2026-03-15 10:00:00+00' ORDER BY 1",
                ["702"], "有效 session 只剩 702", role=app)
    expect_error(pg, db, "DELETE FROM permission_audit_logs WHERE audit_id = 1", "permission denied", role=app)


def verify_swift_logistics(pg: Pg, db: str) -> None:
    app, bi = "logistics_app_login", "logistics_bi_login"
    m1002 = {"app.current_merchant_id": "1002"}
    expect_rows(pg, db, "SELECT shipment_id FROM shipments ORDER BY 1", ["7004", "7006"], "商家 1002 的運單", role=app, settings=m1002)
    expect_rows(pg, db, "SELECT package_id FROM shipment_packages ORDER BY 1", ["7105", "7107"], "商家 1002 的包裹", role=app, settings=m1002)
    expect_rows(pg, db, "SELECT count(*) FROM shipment_events", ["0"], "商家 1002 沒有掃描事件，孤兒事件也不可見", role=app, settings=m1002)
    expect_rows(pg, db, "SELECT task_id FROM dispatch_tasks ORDER BY 1", ["9505"], "商家 1002 的調度任務", role=app, settings=m1002)
    expect_rows(pg, db, "SELECT statement_id FROM billing_statements ORDER BY 1", ["9803", "9804"], "商家 1002 的帳單", role=app, settings=m1002)
    expect_rows(pg, db, "SELECT count(*) FROM merchant_users", ["2"], "商家 1002 的商家帳號", role=app, settings=m1002)
    expect_rows(pg, db, "SELECT count(*) FROM shipments", ["0"], "漏設租戶上下文時 fail-closed", role=app)
    # BOLA：商家 1002 直接查 7001 拿不到
    expect_rows(pg, db, "SELECT shipment_id FROM shipments WHERE shipment_id = 7001", [], "跨租戶 ID 直查被 RLS 擋下", role=app, settings=m1002)
    expect_error(pg, db, "INSERT INTO shipment_packages (package_id, shipment_id, merchant_id, weight_grams) VALUES (99901, 7001, 1001, 100)",
                 "row-level security", role=app, settings=m1002)
    expect_error(pg, db, "INSERT INTO shipment_packages (package_id, shipment_id, merchant_id, weight_grams) VALUES (99902, 7001, 1002, 100)",
                 "foreign key")
    expect_rows(pg, db, "SELECT count(*) FROM v_shipment_analytics", ["8"], "BI 透過檢視表讀到全部運單", role=bi)
    expect_rows(pg, db, "SELECT count(*) FROM billing_statements", ["5"], "BI 靠顯式唯讀政策讀到全部帳單", role=bi)
    expect_error(pg, db, "SELECT * FROM shipment_recipient_pii", "permission denied", role=bi)
    expect_error(pg, db, "UPDATE billing_audit_logs SET before_status = 'x' WHERE audit_id = 1", "permission denied",
                 role=app, settings={"app.current_merchant_id": "1001"})
    # 跨引擎差異（C03）：PostgreSQL 的 DESC 預設把 NULL 排在最前，SQLite 排在最後
    expect_rows(pg, db,
                "SELECT event_type FROM (SELECT event_type, ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY recorded_at DESC) AS rn "
                "FROM shipment_events WHERE shipment_id = 7002) t WHERE rn = 1",
                ["exception"], "C03：PostgreSQL 未寫 NULLS LAST 時取到 NULL 時間的 exception")


def start_tmp_cluster() -> tuple[str, int, str, str]:
    for tool in ("initdb", "pg_ctl", "psql"):
        assert shutil.which(tool), f"找不到 {tool}，請安裝 PostgreSQL 用戶端與伺服器工具"
    tmp = tempfile.mkdtemp(prefix="sqlpractice-pg-")
    data = str(Path(tmp) / "data")
    try:
        subprocess.run(["initdb", "-D", data, "-U", "postgres", "-A", "trust", "-E", "UTF8", "--no-locale"],
                       check=True, capture_output=True)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        # 只走 TCP：Unix socket 路徑上限約 103 位元組，暫存目錄路徑過長時伺服器會拒絕啟動
        subprocess.run(["pg_ctl", "-D", data, "-o", f"-p {port} -c listen_addresses=127.0.0.1 -c unix_socket_directories=''",
                        "-l", str(Path(tmp) / "server.log"), "-w", "start"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        log = Path(tmp) / "server.log"
        detail = log.read_text(encoding="utf-8")[-800:] if log.exists() else ""
        shutil.rmtree(tmp, ignore_errors=True)  # 本函式自己以 mkdtemp 建立的目錄
        raise AssertionError(f"暫存 PostgreSQL 叢集啟動失敗：\n{detail}")
    time.sleep(0.5)
    return "127.0.0.1", port, data, tmp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn-host")
    ap.add_argument("--dsn-port", type=int)
    ap.add_argument("--dsn-user", default="postgres")
    args = ap.parse_args()

    tmp = data = None
    if args.dsn_host:
        host, port = args.dsn_host, args.dsn_port or 5432
    else:
        host, port, data, tmp = start_tmp_cluster()
    pg = Pg(host, port, args.dsn_user)
    try:
        ok, version = pg.query("postgres", "SHOW server_version")
        assert ok, version
        verifiers = {
            "bookstore": verify_bookstore,
            "cloud-academy": verify_cloud_academy,
            "swift-logistics": verify_swift_logistics,
        }
        for name in DOMAINS:
            db = load_domain(pg, name)
            verifiers[name](pg, db)
            print(f"OK  {name}: schema_pg + seed + security_pg loaded, RLS / GRANT / audit / cross-engine assertions passed")
        print(f"verify_pg: {len(DOMAINS)} domain(s) verified on PostgreSQL {version}")
        return 0
    finally:
        if data:
            subprocess.run(["pg_ctl", "-D", data, "-m", "fast", "stop"], capture_output=True)
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)  # 本腳本自己以 mkdtemp 建立的拋棄式叢集目錄


if __name__ == "__main__":
    sys.exit(main())
