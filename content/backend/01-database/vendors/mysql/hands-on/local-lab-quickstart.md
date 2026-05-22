---
title: "MySQL Local Lab Quickstart"
date: 2026-05-22
description: "MySQL local lab 的 Docker Compose、schema seed、sample workload、basic metric 與 teardown"
tags: ["backend", "database", "mysql", "hands-on"]
---

MySQL local lab quickstart 的核心責任是建立後續 ProxySQL、OSC、replication、backup 與 Vitess sandbox 共用的本地環境。這個 lab 提供可重建 MySQL instance、baseline schema、seed data 與 basic evidence。

本文的驗收標準是：你能啟動 MySQL、套用 schema、跑 sample workload、取得 processlist / InnoDB status / table count，並能 teardown 重建。

## Docker Compose

Docker Compose 的核心責任是讓 lab 環境可重建。

```yaml
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: root_pw
      MYSQL_DATABASE: appdb
      MYSQL_USER: app_user
      MYSQL_PASSWORD: app_pw
    ports:
      - "33069:3306"
    command:
      - "--performance-schema=ON"
      - "--log-bin=mysql-bin"
      - "--server-id=1"
```

啟動：

```bash
docker compose up -d
export MYSQL_PWD=app_pw
mysql -h 127.0.0.1 -P 33069 -u app_user appdb -e "SELECT VERSION();"
```

## Baseline Schema

Baseline schema 的核心責任是建立可測 transaction、index、binlog 與 OSC 的模型。

```bash
mysql -h 127.0.0.1 -P 33069 -u app_user appdb <<'SQL'
CREATE TABLE accounts (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id CHAR(36) NOT NULL,
  owner_name VARCHAR(128) NOT NULL,
  status ENUM('active', 'closed') NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_accounts_tenant (tenant_id)
) ENGINE=InnoDB;

CREATE TABLE ledger_entries (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  account_id BIGINT NOT NULL,
  amount_cents BIGINT NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ledger_idempotency (idempotency_key),
  KEY idx_ledger_account_created (account_id, created_at),
  CONSTRAINT fk_ledger_account FOREIGN KEY (account_id) REFERENCES accounts(id)
) ENGINE=InnoDB;
SQL
```

## Seed and Evidence

Seed and evidence 的核心責任是產生可重跑資料與 baseline。

```bash
mysql -h 127.0.0.1 -P 33069 -u app_user appdb <<'SQL'
INSERT INTO accounts(tenant_id, owner_name, status)
VALUES ('tenant-a', 'Ada', 'active'), ('tenant-b', 'Lin', 'active');

INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key)
VALUES (1, 1000, 'seed-ada-1'), (1, -200, 'seed-ada-2'), (2, 500, 'seed-lin-1');

SELECT a.owner_name, SUM(l.amount_cents) AS balance_cents
FROM accounts a JOIN ledger_entries l ON l.account_id = a.id
GROUP BY a.owner_name;
SQL
```

Basic evidence：

```bash
mysql -h 127.0.0.1 -P 33069 -u app_user appdb -e "SHOW FULL PROCESSLIST;"
mysql -h 127.0.0.1 -P 33069 -u app_user appdb -e "SHOW TABLE STATUS;"
mysql -h 127.0.0.1 -P 33069 -u app_user appdb -e "SHOW ENGINE INNODB STATUS\\G"
```

## Teardown

Teardown 的核心責任是讓 lab 可重跑。

```bash
docker compose down -v
```

完成本篇後，backup 進入 [Backup Restore Drill](../backup-restore-drill/)；schema change 進入 [Online Schema Change Lab](../online-schema-change-lab/)；routing 進入 [ProxySQL Routing Lab](../proxysql-routing-lab/)。
