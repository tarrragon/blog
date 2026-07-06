---
title: "服務上線的業界常識地基"
date: 2026-07-06
description: "會寫 code、在 localhost 跑起來過、但第一次要把服務放上網際網路給真實使用者，不知道中間缺哪些「大家都當常識」的東西時回來讀 — 從本機到上線的地基串成一條線"
weight: 1
tags: ["going-live", "deployment", "foundations"]
---

這一層補的是「我會寫 code、也在 localhost 跑起來過，但從沒把服務真的放上網際網路」跟「服務在雲上穩定服務真實使用者」之間那段落差。這段落差裡有一批東西，每個從業者都當常識——服務跑在哪、域名怎麼指過去、HTTPS 哪來的、DB 要不要自己顧、備份能不能還原——但正因為是常識，很少被寫成教學，反而成了第一次上線最容易卡住的地方。

其他系列（[Infra](/infra/)、[DevOps](/devops/)、[Backend 服務選型](/backend/00-service-selection/)）把這些主題都講得很深，但都預設你已經懂這層地基、直接從進階講起。這一層刻意站在更低的高度、vendor 中立，把地基串成一條線，每一站在講清楚概念後往上路由到對應的深度內容——它是各獨立系列共同的 on-ramp，不取代它們，只把「第一次上線」該懂的順序理出來。

## 這一層的路徑

順序反映「第一次上線」實際會遇到的問題：

| 站  | 文章                                                               | 回答什麼問題                                         |
| --- | ------------------------------------------------------------------ | ---------------------------------------------------- |
| 1   | [部署到底是什麼](/going-live/what-is-deploy/)                      | 「上線」這個動作實際在做什麼、跟本機跑起來差在哪     |
| 2   | [主機形態光譜](/going-live/hosting-spectrum/)                      | 我的 code 到底跑在哪：VPS / PaaS / serverless 怎麼選 |
| 3   | [域名與 HTTPS 怎麼接上](/going-live/domain-and-https/)             | 買的域名怎麼指到伺服器、HTTPS 憑證哪來的             |
| 4   | [十二要素基線](/going-live/twelve-factor-baseline/)                | 一個服務要好部署、好搬家，該遵守哪些基本紀律         |
| 5   | [自架還是託管：以資料庫為例](/going-live/self-host-vs-managed-db/) | VPS 上自己跑 DB 跟租 RDS，成本差在哪、差價在買什麼   |
| 6   | [備份與還原的地基](/going-live/backup-restore-basics/)             | 為什麼「沒測過還原的備份等於沒有備份」               |

## 已經有深度專篇的地基（這裡不重寫、直接連過去）

有些地基概念已經有紮實的專篇，只是站在進階高度。走完上面的路徑後，這些是往上的下一步：

- **dev / staging / prod 多環境**：[Infra 環境分離](/infra/04-environment-separation/)、[一台機器到多環境](/infra/00-infra-mindset/one-machine-to-environments/)
- **stateless 設計**：[DevOps 無狀態設計](/devops/02-horizontal-scaling/stateless-design/)
- **負載平衡 / 反向代理**：[DevOps 反向代理職責](/devops/01-load-balancing/reverse-proxy-responsibilities/)
- **secret 管理**：[Backend secret 治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)
- **自架 vs 託管的成本曲線（進階）**：[DevOps 自架 vs 雲端成本交叉點](/devops/08-cost-management/self-hosted-vs-cloud/)

## 跨分類引用

這一層是各深度系列的共同 on-ramp，往上接四個方向：

- → [Backend 模組零：服務選型](/backend/00-service-selection/)：這一層講「上線要懂什麼」，模組零講「自建還是託管、什麼狀態放哪」的選型理論
- → [Infra 基礎設施建置指南](/infra/)：從「一台 VPS 手動上線」往上長成「用 IaC 管一整套雲端地基」
- → [DevOps 實務指南](/devops/)：服務上線後怎麼扛負載、擴展、控成本
- → [Dotfile 模組十：Prod Parity](/linux/dotfile/10-prod-parity/)：本機開發環境怎麼對齊線上的 runtime
