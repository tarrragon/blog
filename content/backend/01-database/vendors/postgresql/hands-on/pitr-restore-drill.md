---
title: "PostgreSQL PITR Restore Drill"
date: 2026-05-22
description: "PostgreSQL base backup、WAL archive、target time restore、validation query 與 RPO / RTO evidence 的操作說明"
tags: ["backend", "database", "postgresql", "hands-on", "pitr"]
---

PostgreSQL PITR restore drill 的核心責任是證明 backup 可以還原到指定時間點。這篇承接 [PITR + WAL Archiving](../../pitr-wal-archiving/)，把備份從存在狀態推進到可恢復證據。

本文的驗收標準是：你能記錄 base backup 時間、target time、restore duration、validation query 與 RPO / RTO note。實際命令會依 pgBackRest、Barman、cloud snapshot 或 managed service 而變；本文提供 vendor-neutral drill frame。

## Prepare Recovery Point

Prepare recovery point 的核心責任是建立可辨識 transaction。先寫入一筆 marker，記錄時間。

```bash
psql "$DATABASE_URL" <<'SQL'
CREATE TABLE IF NOT EXISTS restore_markers (
  id bigserial PRIMARY KEY,
  marker text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO restore_markers(marker) VALUES ('before-bad-change');
SELECT id, marker, created_at FROM restore_markers ORDER BY id DESC LIMIT 1;
SQL
```

把 `created_at` 記為 target time。正式 drill 要用 UTC，並記錄 timezone、operator、backup set 與 WAL archive status。

## Create Bad Change

Create bad change 的核心責任是模擬需要 PITR 的錯誤。

```bash
psql "$DATABASE_URL" <<'SQL'
INSERT INTO restore_markers(marker) VALUES ('bad-change-after-target');
UPDATE accounts SET status = 'closed';
SELECT status, count(*) FROM accounts GROUP BY status;
SQL
```

這一步在 lab 中代表誤操作。Production 事故中，bad change 可能是誤刪、錯誤 batch、壞 migration 或 application bug。

## Restore Workflow

Restore workflow 的核心責任是把 backup tool 的操作轉成固定 evidence。不同工具命令不同，但流程一致：

1. 選定 base backup。
2. 設定 recovery target time。
3. 套用 WAL 到 target time。
4. Promote restored instance。
5. 跑 validation query。
6. 啟動 application smoke test。

Example pseudo-runbook：

```text
restore_target_time = 2026-05-21T10:15:30Z
base_backup = latest backup before target
wal_archive = available through target
restore_path = isolated environment
```

Restore 必須在隔離環境先完成。直接覆蓋 production 會讓 evidence 與 rollback 空間消失。

## Validation Query

Validation query 的核心責任是確認 restore 到正確時間點。

```bash
psql "$RESTORED_DATABASE_URL" <<'SQL'
SELECT marker, created_at
FROM restore_markers
ORDER BY id;

SELECT status, count(*)
FROM accounts
GROUP BY status;
SQL
```

預期結果是存在 `before-bad-change`，且 `bad-change-after-target` 尚未出現。`accounts` 狀態應維持 target time 前的分布。

## RPO / RTO Evidence

RPO / RTO evidence 的核心責任是把 drill 結果轉成服務語言。

| Evidence         | 記錄內容                           |
| ---------------- | ---------------------------------- |
| Backup timestamp | 使用哪份 base backup               |
| Target time      | 要恢復到哪一秒                     |
| WAL availability | target time 前後 WAL 是否完整      |
| Restore duration | 從開始 restore 到 validation 成功  |
| Data gap         | target time 後需補償的 transaction |
| Smoke test       | application 核心 workflow 是否可用 |

PITR 的成功標準是資料與 application 都可用。只讓 PostgreSQL 啟動成功，還不足以交付服務。

## Drill Retrospective

Drill retrospective 的核心責任是把演練缺口轉成下一步。

常見缺口：

1. 找不到正確 base backup。
2. WAL archive 缺段。
3. target time timezone 混亂。
4. Restore 太慢，超過 RTO。
5. Application secret / config 指不到 restored DB。
6. Validation query 缺少 business invariant。

完成本篇後，跨區恢復讀 [Cross-region DR](../../cross-region-dr/)；備份策略讀 [PITR + WAL Archiving](../../pitr-wal-archiving/)。
