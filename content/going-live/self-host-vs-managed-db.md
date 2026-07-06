---
title: "自架還是託管：以資料庫為例"
date: 2026-07-06
description: "在 VPS 上自己跑一個 DB container 很便宜、看到 RDS / Cloud SQL 一個月要幾十鎂而猶豫時回來讀 — 成本差在哪、差價其實在買什麼"
weight: 5
tags: ["going-live", "deployment", "cost", "database", "foundations"]
---

自己在 VPS 上跑資料庫，跟租一個託管資料庫（AWS RDS、Google Cloud SQL），帳面成本差很多——但那個差價買的是「你不用自己做的維運工作」，不是單純被多收錢。用資料庫當例子最清楚，因為 DB 是最不能出事、也最花維運的一塊。

## 成本結構為什麼差

|              | VPS 自己跑 DB                              | 託管 RDS / Cloud SQL                                |
| ------------ | ------------------------------------------ | --------------------------------------------------- |
| DB 的錢      | 不另計帳單——跟 app 共用 VPS（但吃 RAM/IO） | 獨立一筆——DB 自己一個 instance                      |
| 計價項       | 一台 VPS 月租、全包                        | instance + 儲存 + 備份儲存 + I/O + 對外流量，分開計 |
| 高可用（HA） | 要自己搞                                   | Multi-AZ（跨可用區）開下去大約 ×2                   |

關鍵差別：VPS 上「DB 成本」不另計一條帳單，它跟 app 共用你本來就要付的那台機器；託管是**另外一條帳單**，而且每單位 RAM/CPU 比裸 VPS 貴很多，因為價格裡包了維運層。純算 compute，同一個小 DB，託管常是自架的好幾倍到十幾倍。

但「共用 VPS」不是真的零成本：DB（Postgres/MySQL）常態要 1–2GB+ RAM，跟 app 擠同一台小 VPS 容易 OOM 或 IO 互搶，實務上你得把 VPS 從 2GB 升到 4–8GB——那筆錢藏進了 VPS 帳單，只是不叫「DB 費用」。所以「便宜」要扣掉這段升規格的成本。

> 以下是量級、不是報價，且雲端定價會變、看區域規格——決策前一定要去各家定價計算機用你的實際規格算。

小專案常見的量級感：一台 2-4GB 的 VPS 全包月費個位數到二十幾鎂、DB 不另計；託管 DB 一個小 instance 一個月幾十鎂起、加儲存/備份/HA 後常落在幾十到上百鎂，而且是**疊在 app 主機費用之上**。

## 那多付的錢在買什麼

差價買的是你**不做這些維運**的代價：

- 自動備份 + 時間點還原（point-in-time recovery）
- 自動故障切換 / HA（主掛了自動起備）
- 版本修補、監控、read replica 一鍵開
- 半夜 DB 主機磁碟滿、掛掉時，有別人 on-call

在 VPS 上，以上每一條都是你的工作：你設備份、你**測還原**（沒測過的備份等於沒有，見 [備份與還原的地基](/going-live/backup-restore-basics/)）、你修補、你處理 3am 事故；而且 VPS 一死、資料跟著死，除非你自己做了冗餘。

## 看 TCO，不看標價

- **標價**：VPS 明顯便宜（DB 不另計帳單、頂多升一階規格 vs 託管一個月幾十上百）。
- **含你的時間 + 資料遺失風險 + 停機損失（總持有成本 TCO）**：一旦資料有價值（有營收、賠不起），託管常常反而划算——省下的是你不用當 DBA、不用扛半夜事故、不用賭「我的備份真的能還原嗎」。
- **分水嶺**：自用 / 早期 / 極度省錢 / 你享受搞維運 → 偏自架；有營收資料 / 小團隊時間值錢 / 賠不起資料遺失 / 沒人顧 DB → 偏託管。

這條「自架帳單便宜、但主要成本在帳單外的人力」跟 [DevOps 成本模型](/devops/05-capacity-planning/cost-model/) 講的「自建與託管人力差 3 到 10 倍」是同一件事；兩條成本曲線的交叉點怎麼算，見 [DevOps 自架 vs 雲端成本交叉點](/devops/08-cost-management/self-hosted-vs-cloud/)。

## 別掉進二選一

- **便宜 VPS**（如 Hetzner）把自架成本壓很低，省錢派很有吸引力。
- **託管也有便宜檔**：不是只有 RDS/Cloud SQL 這種貴的——DigitalOcean Managed DB、Supabase、Neon、PlanetScale 有便宜甚至免費方案，別把「託管」直接等於「昂貴」。
- **Serverless DB**（Aurora Serverless、Neon、PlanetScale）：流量低 / 尖峰型的按用量計費，離峰幾乎不花錢，小專案可能比固定 instance 更省。
- **折衷**：DB 自架但放另一台獨立小 VPS（跟 app 分開、但不託管），隔離性有了、成本仍低。

## 為什麼「以資料庫為例」特別代表性

同樣的「自架 vs 託管」問題也發生在 cache、queue、物件儲存，但 DB 是最尖銳的——因為它**有狀態、最怕資料遺失**。也因此，商業 prod 幾乎不會在 [container](/backend/knowledge-cards/container/) 裡跑正式 DB，而是用託管服務或獨立的資料節點（stateful 的保護與為何不隨手跑 DB container，見 [Backend 狀態儲存選型](/backend/00-service-selection/state-storage-selection/)）。無狀態的 app 可以隨便砍隨便開，有狀態的 DB 不行——這個差別決定了你多願意為「別人幫你顧它」付錢。

## 下一步

決定了哪些自己顧之後，凡是你自己顧的（尤其 DB），下一個必修是備份——見 [備份與還原的地基](/going-live/backup-restore-basics/)。自建 vs 託管的完整選型理論見 [Backend 模組零](/backend/00-service-selection/)。
