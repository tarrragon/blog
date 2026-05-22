---
title: "MySQL Encryption / TLS / Key Management"
date: 2026-05-22
description: "MySQL at-rest encryption、TLS、keyring、certificate rotation、backup encryption 與 credential governance"
tags: ["backend", "database", "mysql", "security", "encryption", "tls"]
---

MySQL encryption / TLS / key management 的核心責任是把資料庫保護拆成儲存加密、傳輸加密、金鑰生命週期與連線憑證治理。Encryption 是多層保護設計；它涵蓋 InnoDB tablespace、redo / undo、binary log、backup artifact、client connection 與 keyring。

本文的判讀錨點是：加密要服務於 threat model。若風險是磁碟遺失，[at-rest encryption](/backend/knowledge-cards/at-rest-encryption/) 是重點；若風險是網路攔截，TLS 是重點；若風險是內部濫用，還需要 role、audit、masking 與 SIEM。

官方文件路由的核心責任是固定 MySQL 8.4 security claim。實作前先查 [InnoDB data-at-rest encryption](https://dev.mysql.com/doc/refman/8.2/en/innodb-data-encryption.html)、[MySQL keyring](https://dev.mysql.com/doc/refman/8.0/en/keyring.html) 與 [SHOW BINARY LOG STATUS](https://dev.mysql.com/doc/refman/8.4/en/show-binary-log-status.html)；本文最後檢查日是 2026-05-22。

## Protection Layers

Protection layers 的核心責任是把保護面分層。

| 層級                  | 主要責任                            | Evidence                           |
| --------------------- | ----------------------------------- | ---------------------------------- |
| At-rest encryption    | data file、redo、undo、temp         | encryption setting、keyring status |
| In-transit TLS        | client / replica / admin connection | TLS mode、certificate、cipher      |
| Backup encryption     | dump、snapshot、physical backup     | encrypted artifact、restore drill  |
| Key management        | key generation、rotation、access    | KMS / keyring log、rotation record |
| Credential governance | user password、secret、rotation     | grant review、secret age           |

這些層級要一起設計。資料檔加密後，backup 若以明文落到 object storage，保護鏈仍然破洞；TLS 開啟後，client 若允許 insecure fallback，也會失去網路保護。

## Keyring Boundary

Keyring boundary 的核心責任是定義 MySQL 如何取得與保護 encryption key。MySQL 支援 keyring component / plugin 與外部 KMS 整合；managed MySQL 可能由 provider 接管 key storage。

| 部署型態      | key 責任                            | 審查問題                              |
| ------------- | ----------------------------------- | ------------------------------------- |
| Self-managed  | 自行部署 keyring / KMS              | key file permission、backup、rotation |
| Managed MySQL | provider KMS / customer-managed key | region、rotation、audit、restore      |
| Container lab | dev-only keyring                    | 避免和 production policy 混用         |

Keyring 要進入 backup / restore drill。還原 database 時，只有 data file 而沒有對應 key，restore 會失敗；runbook 要保存 key dependency 與 emergency access。

## TLS Policy

TLS policy 的核心責任是讓 client connection、replication connection 與 admin connection 都有明確安全等級。

| 連線類型    | 建議檢查                             |
| ----------- | ------------------------------------ |
| Application | require SSL、verify CA / identity    |
| Replication | source / replica TLS、cert expiry    |
| Admin       | bastion / VPN / TLS、least privilege |
| Backup tool | encrypted transport、secret scope    |

TLS 驗證要包含 certificate rotation。過期憑證造成的 downtime 很常見；runbook 要記錄 CA、server cert、client cert、rotation window 與 reload / restart 條件。

```sql
SHOW VARIABLES LIKE 'require_secure_transport';
SHOW STATUS LIKE 'Ssl_cipher';
```

這些查詢只能提供 connection 層 evidence。正式驗證還要從 client 設定確認 `ssl-mode` 是否驗證 CA / identity。

## Backup and Binlog Encryption

Backup and binlog encryption 的核心責任是保護資料離開 primary 後的生命週期。MySQL backup、binlog、logical dump、object storage、replica seed 都可能含敏感資料。

| Artifact        | 保護方式                               |
| --------------- | -------------------------------------- |
| Logical dump    | client-side encryption、storage policy |
| Physical backup | backup tool encryption、KMS            |
| Binlog          | encrypted storage、restricted access   |
| Snapshot        | volume encryption、snapshot policy     |
| Restore copy    | isolated environment、secret scoping   |

Restore drill 要確認加密 artifact 可被解密並啟動。只有成功產出 encrypted backup，還不足以證明災難時能恢復。

## Rotation Runbook

Rotation runbook 的核心責任是讓 key、certificate、password 都可定期更換。

1. Inventory：列出 DB user、TLS cert、KMS key、backup key。
2. Impact：確認哪些 client / replica / backup job 使用它。
3. Staging：先在 staging 旋轉並跑 smoke test。
4. Rollout：使用雙憑證 / 雙 secret window。
5. Validation：查連線、replication、backup、restore。
6. Cleanup：移除舊 key / cert / secret。

Rotation 要設 calendar 與 owner。安全設定長期無人輪替時，incident 後會難以判斷 exposure window。

## Failure Modes

Failure modes 的核心責任是提前列出加密常見事故。

| Failure mode     | 判讀訊號                       | 修正方向                                |
| ---------------- | ------------------------------ | --------------------------------------- |
| TLS fallback     | client 仍可明文連線            | require secure transport、client verify |
| Cert expiry      | application connection failure | rotation alert、dual cert window        |
| Missing keyring  | restore / startup failure      | key backup、KMS access drill            |
| Plain backup     | storage artifact 未加密        | backup pipeline policy                  |
| Overbroad secret | admin / app 共用 credential    | role split、secret rotation             |

安全 runbook 要和 audit log 串接。Key rotation、failed TLS、privilege change、restore access 都應留下可追溯紀錄。

## 下一步路由

Encryption / TLS / key management 完成後，操作證據讀 [Audit Log + SIEM](../audit-log-siem/)；備份恢復讀 [PITR / Backup](../pitr-backup/)；資料保護治理讀 [Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)。
