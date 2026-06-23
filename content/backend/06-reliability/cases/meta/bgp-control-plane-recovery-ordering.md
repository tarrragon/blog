---
title: "Meta：BGP 事故與控制面恢復順序"
date: 2026-06-23
description: "當回復工具依賴已故障的系統：2021-10 事故揭露控制面恢復順序與 out-of-band 存取的設計約束。"
weight: 42
tags: ["backend", "reliability", "case-study"]
---

控制面恢復順序的責任是確保回復路徑不依賴已故障的系統。當 DNS、BGP、遠端存取工具與內部通訊都跑在同一個網路上，網路故障會同時切斷服務和回復手段。

## 問題場景

2021-10-04，Meta 的一次 BGP 配置變更導致骨幹網路撤回所有 route announcement。影響的範圍不只是對外服務：DNS 因為無法到達權威 DNS server 而失效，內部工具（包含遠端管理、通訊與身份驗證）也依賴同一個內部網路，因此同步不可用。

工程師無法透過遠端存取工具連線到設備，必須實體前往資料中心手動恢復 BGP 配置。資料中心的實體存取流程（門禁授權、安全人員協調、設備定位）進一步拉長恢復時間。整個事故從發生到服務恢復超過 6 小時。

這個事故的核心教訓是恢復工具必須獨立於被恢復的系統。當 out-of-band 路徑在設計上或認證上依賴 production 網路，它就不是真正的 out-of-band。

## 決策機制

| 機制                        | 核心問題                                | 交付結果                     |
| --------------------------- | --------------------------------------- | ---------------------------- |
| Out-of-band management      | 恢復路徑是否獨立於 production 網路      | 獨立連線與管理通道           |
| Recovery dependency mapping | 每個回復步驟的依賴是否有循環            | 依賴圖與循環偵測             |
| Staged recovery order       | 恢復順序是否先連通再服務                | 網路 → DNS → 控制面 → 資料面 |
| Physical access readiness   | remote 手段失效時實體存取是否可立即啟動 | 授權、存取卡、知識分佈       |

Out-of-band management 的設計約束是完全獨立於 production 路徑。這包含網路連線（獨立 ISP 或 cellular）、認證（不依賴 production identity service）與通訊（獨立通訊工具或電話樹）。任何一環依賴 production 系統，就不算真正的 out-of-band。

Recovery dependency mapping 的責任是在事故前畫出恢復步驟之間的依賴關係，找出循環依賴。Meta 事故中，DNS 恢復依賴網路連通，網路恢復依賴 BGP 設備存取，設備存取依賴 out-of-band 工具，而 out-of-band 工具的認證依賴 production identity service — 形成循環。事前的 dependency mapping 能暴露這類隱性路徑。

Staged recovery order 把恢復拆成明確的階段：先恢復物理網路連通，再恢復 DNS 與名稱解析，接著恢復控制面服務（監控、部署、配置管理），最後恢復資料面流量。每個階段有明確的完成條件，下一階段才啟動。

## 可觀測訊號

| 訊號                            | 判讀重點                     | 對應章節                                                            |
| ------------------------------- | ---------------------------- | ------------------------------------------------------------------- |
| out-of-band reachability        | 獨立管理通道是否可連線       | [6.7](/backend/06-reliability/dr-rollback-rehearsal/)               |
| recovery dependency cycle count | 恢復步驟之間是否存在循環依賴 | [6.14](/backend/06-reliability/dependency-reliability-budget/)      |
| DNS propagation lag             | 名稱解析恢復後多久全域生效   | [6.22](/backend/06-reliability/steady-state-definition/)            |
| physical access activation time | 從決策到實體接觸設備的時間   | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |

## 常見陷阱

最常見的錯誤是把 out-of-band 存取當成「有設定就好」而不定期驗證。Meta 事故暴露的問題是 out-of-band 工具的 authentication 依賴 production identity service — 名義上路徑獨立，實際上認證路徑共享。DR rehearsal 必須包含「假設 production 網路完全不可用」的場景，驗證 out-of-band 路徑的每一環（連線、認證、通訊、操作權限）都能獨立運作。

另一個常見問題是 recovery 知識集中在少數人。當實體恢復需要到場操作時，知識的地理分佈直接影響恢復時間。關鍵設備的恢復程序必須文件化，且分佈在多個地理位置的團隊成員手上。

## 下一步路由

- [6.7 DR rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)：out-of-band 路徑的定期驗證
- [6.14 dependency reliability budget](/backend/06-reliability/dependency-reliability-budget/)：恢復路徑的隱性依賴治理
- [6.22 steady state definition](/backend/06-reliability/steady-state-definition/)：DNS 與控制面恢復完成的判準
- [8.14 multi-incident coordination](/backend/08-incident-response/multi-incident-coordination/)：跨區域恢復的指揮協調

## 引用源

- [More details about the October 4 outage](https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/)
- [Update about the October 4th outage](https://engineering.fb.com/2021/10/04/networking-traffic/outage/)
