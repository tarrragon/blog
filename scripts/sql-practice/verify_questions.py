#!/usr/bin/env python3
"""驗證 scripts/sql-practice/questions/ 全部題庫 JSON：
1. 結構欄位完整性、variantId 唯一性、tablePath 表名存在於對應領域 schema.sql，
   以及碰到生命週期狀態表的題目宣告 population 並與需求文字、推薦查詢一致（check_population）
2. relatedDocs 路徑實際存在於 content/
3. benchmarkRef 實際存在於 benchmarks/*.json
4. 所有 execMode == "sqlite" 的選項在獨立記憶體 SQLite 資料庫實跑驗證：
   - expectedExec == "ok" 必須成功執行；expectedExec == "error" 必須拋出 sqlite3.Error
   - sqliteAssertions（optionRowCounts / optionFirstColumnOrder / optionExactRows / optionExplainMustContain）全數吻合
"""

import json
from pathlib import Path
import sqlite3
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONTENT_DIR = REPO_ROOT / "content"
QUESTIONS_DIR = SCRIPT_DIR / "questions"

sys.path.insert(0, str(SCRIPT_DIR))
from verify_domains import explain_text, load_domain  # noqa: E402

REQUIRED_Q_FIELDS = {
    "conceptId",
    "variantId",
    "domain",
    "stage",
    "tablePath",
    "perspective",
    "difficulty",
    "premiseFlip",
    "designDimension",
    "traps",
    "title",
    "businessRequirement",
    "workloadProfile",
    "options",
    "recommendedKeys",
    "alternativeNote",
    "relatedDocs",
}

REQUIRED_OPT_FIELDS = {
    "key",
    "sql",
    "execMode",
    "expectedExec",
    "normalResult",
    "edgeCaseResult",
    "pros",
    "cons",
    "validWhen",
    "failsWhen",
}

VALID_PERSPECTIVES = {"choose-query", "pick-counterexample", "diagnose-plan", "tradeoff-design"}

# 母體約定（seed.sql 檔頭）：帶生命週期狀態的表同時存放有效列與已註銷／停權／離職列。
# tablePath 碰到這些表的題目必須宣告 population，讓需求文字與正解對「查誰」的判斷一致：
# - all-records：母體含任何狀態的列，需求文字必須寫明（ALL_RECORDS_PHRASES 之一）
# - active-only：只算目前有效的列，推薦的 SELECT 選項必須同時過濾 status 與 deleted_at
# - specific-ids：需求以明確 ID 指定對象，母體與狀態無關
# - not-applicable：概念題或設計題，不產生查詢結果集
LIFECYCLE_TABLES = {
    "bookstore": {"customers", "staff_accounts"},
    "cloud-academy": {"users"},
    "swift-logistics": {"merchants", "merchant_users", "staff_accounts"},
}
VALID_POPULATIONS = {"all-records", "active-only", "specific-ids", "not-applicable"}
ALL_RECORDS_PHRASES = ("不論帳號狀態", "含已註銷", "含已抹除", "含停權", "含已刪除", "含離職")


def check_population(q: dict) -> None:
    vid = q["variantId"]
    touched = set(q["tablePath"]) & LIFECYCLE_TABLES[q["domain"]]
    if not touched:
        return
    pop = q.get("population")
    assert pop in VALID_POPULATIONS, f"{vid}: tablePath 含生命週期表 {sorted(touched)}，須宣告 population（{sorted(VALID_POPULATIONS)}），實得 {pop!r}"
    if pop == "all-records":
        assert any(p in q["businessRequirement"] for p in ALL_RECORDS_PHRASES), (
            f"{vid}: population=all-records，需求文字須寫明母體（{'、'.join(ALL_RECORDS_PHRASES)} 之一）"
        )
    if pop == "active-only":
        for o in q["options"]:
            if o["key"] not in q["recommendedKeys"] or o["execMode"] != "sqlite":
                continue
            sql = o["sql"].lstrip().upper()
            if not sql.startswith(("SELECT", "WITH")):
                continue
            assert "STATUS" in sql and "DELETED_AT" in sql, (
                f"{vid}/{o['key']}: population=active-only，推薦的查詢須同時過濾 status 與 deleted_at"
            )


def doc_path_exists(url_path: str) -> bool:
    rel = url_path.strip("/")
    return (CONTENT_DIR / f"{rel}.md").is_file() or (CONTENT_DIR / rel / "_index.md").is_file()


def get_domain_tables(domain_id: str) -> set[str]:
    conn = load_domain(domain_id, with_scale=False)
    try:
        return {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
        }
    finally:
        conn.close()


def run_sqlite_option(domain_id: str, with_scale: bool, sql: str) -> tuple[bool, list | str, str]:
    conn = load_domain(domain_id, with_scale=with_scale)
    try:
        plan = ""
        try:
            plan = explain_text(conn, sql)
        except sqlite3.Error:
            plan = ""
        cur = conn.execute(sql)
        rows = [list(r) for r in cur.fetchall()]
        return True, rows, plan
    except sqlite3.Error as exc:
        return False, str(exc), ""
    finally:
        conn.close()


def main() -> int:
    manifest = json.loads((QUESTIONS_DIR / "manifest.json").read_text(encoding="utf-8"))
    domain_tables = {d["id"]: get_domain_tables(d["id"]) for d in manifest["domains"]}

    benchmark_ids: set[str] = set()
    for rel in manifest["benchmarks"]:
        bdata = json.loads((SCRIPT_DIR / rel).read_text(encoding="utf-8"))
        for b in bdata["benchmarks"]:
            benchmark_ids.add(b["benchmarkId"])

    seen_variants: set[str] = set()
    total_questions = 0
    total_sqlite_execs = 0
    total_assertions = 0

    for stage_entry in manifest["stages"]:
        qpath = QUESTIONS_DIR / stage_entry["file"]
        questions = json.loads(qpath.read_text(encoding="utf-8"))
        assert isinstance(questions, list) and len(questions) > 0, f"{qpath} 必須是非空陣列"

        for q in questions:
            total_questions += 1
            missing = REQUIRED_Q_FIELDS - set(q.keys())
            assert not missing, f"{qpath}: 缺少欄位 {missing}"

            vid = q["variantId"]
            assert vid not in seen_variants, f"重複 variantId: {vid}"
            seen_variants.add(vid)

            domain = q["domain"]
            assert domain in domain_tables, f"{vid}: 未知領域 {domain}"
            assert q["stage"] == stage_entry["stage"], f"{vid}: stage 不符"
            assert q["perspective"] in VALID_PERSPECTIVES, f"{vid}: 無效 perspective {q['perspective']}"
            assert q["difficulty"] in (1, 2, 3), f"{vid}: difficulty 應為 1..3"

            for tbl in q["tablePath"]:
                assert tbl in domain_tables[domain], f"{vid}: tablePath '{tbl}' 不存在於領域 {domain}"
            check_population(q)

            for doc in q["relatedDocs"]:
                assert doc_path_exists(doc), f"{vid}: relatedDocs 路徑不存在於 content/: {doc}"

            if q.get("benchmarkRef"):
                assert q["benchmarkRef"] in benchmark_ids, f"{vid}: benchmarkRef 不存在: {q['benchmarkRef']}"

            opts = q["options"]
            assert len(opts) == 4, f"{vid}: 應有 4 個選項，實得 {len(opts)}"
            opt_keys = [o["key"] for o in opts]
            assert len(set(opt_keys)) == 4, f"{vid}: 選項 key 重複"
            for rk in q["recommendedKeys"]:
                assert rk in opt_keys, f"{vid}: recommendedKey {rk} 不在 options"

            with_scale = bool(q.get("requiresScale", False))
            results_by_key: dict[str, list] = {}
            plans_by_key: dict[str, str] = {}

            for o in opts:
                omiss = REQUIRED_OPT_FIELDS - set(o.keys())
                assert not omiss, f"{vid}/{o.get('key')}: 選項缺少欄位 {omiss}"
                assert o["execMode"] in ("sqlite", "conceptual"), f"{vid}/{o['key']}: 無效 execMode"

                if o["execMode"] == "sqlite":
                    total_sqlite_execs += 1
                    ok, payload, plan = run_sqlite_option(domain, with_scale, o["sql"])
                    if o["expectedExec"] == "ok":
                        assert ok, f"{vid}/{o['key']}: 預期成功但 SQLite 報錯: {payload}"
                        results_by_key[o["key"]] = payload
                        plans_by_key[o["key"]] = plan
                    elif o["expectedExec"] == "error":
                        assert not ok, f"{vid}/{o['key']}: 預期報錯但 SQLite 竟然成功回傳 {payload}"
                    else:
                        raise AssertionError(f"{vid}/{o['key']}: 無效 expectedExec {o['expectedExec']}")

            assertions = q.get("sqliteAssertions", {})
            for key, expected_cnt in assertions.get("optionRowCounts", {}).items():
                total_assertions += 1
                actual_cnt = len(results_by_key[key])
                assert actual_cnt == expected_cnt, f"{vid}/{key}: 列數不符，預期 {expected_cnt}，實得 {actual_cnt}"

            for key, expected_col in assertions.get("optionFirstColumnOrder", {}).items():
                total_assertions += 1
                actual_col = [r[0] for r in results_by_key[key]]
                assert actual_col == expected_col, f"{vid}/{key}: 首欄序不符，預期 {expected_col}，實得 {actual_col}"

            for key, expected_rows in assertions.get("optionExactRows", {}).items():
                total_assertions += 1
                actual_rows = results_by_key[key]
                assert actual_rows == expected_rows, f"{vid}/{key}: 結果列不符，預期 {expected_rows}，實得 {actual_rows}"

            for key, expected_substr in assertions.get("optionExplainMustContain", {}).items():
                total_assertions += 1
                actual_plan = plans_by_key[key]
                assert expected_substr in actual_plan, f"{vid}/{key}: EXPLAIN 缺 '{expected_substr}'，實得:\n{actual_plan}"

        print(f"OK  {stage_entry['file']}: {len(questions)} question(s) verified")

    print(
        f"verify_questions: {total_questions} question(s), {total_sqlite_execs} live SQLite option run(s), {total_assertions} assertion(s) passed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
