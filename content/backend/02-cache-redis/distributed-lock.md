---
title: "2.4 distributed lock 與租約"
date: 2026-04-23
description: "整理鎖語意、租約風險與適用場景"
weight: 4
tags: ["backend", "cache", "distributed-lock"]
---

分散式鎖（distributed lock）的核心責任是協調跨節點互斥，避免同一資源被重複處理。它解的是協調一致性問題；正式狀態一致性仍由交易邊界或版本控制承擔。

## 鎖與租約

分散式鎖通常採租約語意：持鎖者在租約有效期內擁有操作權，租約到期後需重新競爭。租約模式適合處理節點失效，但也引入時鐘漂移、網路延遲與續租失敗風險。

續租策略要明確：何時續租、續租失敗如何降級、是否有 fencing token 保護。若只依賴「拿到鎖就安全」的假設，異常時容易產生重複副作用。

## split brain 與 fencing

split brain 常見於網路分割或暫停後恢復。兩個節點都認為自己持有鎖時，互斥語意失效。fencing token 的責任是讓下游只接受最新持鎖者操作，降低雙主寫入風險。

若下游無法驗證 fencing token，distributed lock 的保護能力會明顯下降。這時更穩定的做法通常是改成資料版本控制或條件更新。

## 何時使用、何時轉向

適合使用 distributed lock 的場景：排程任務避免重複執行、單資源批次工作協調、短期臨界區互斥。高價值交易資料更新，優先使用資料庫交易與唯一約束，將鎖作為輔助而非核心一致性機制。

當鎖競爭成為常態、租約續租頻繁失敗、鎖持有時間與業務耗時高度耦合時，代表模型需要轉向分片、隊列化或版本檢查。

## 判讀訊號

| 訊號                            | 判讀重點                       | 對應動作                         |
| ------------------------------- | ------------------------------ | -------------------------------- |
| 鎖等待時間持續拉長              | 臨界區過大或熱點資源集中       | 縮小臨界區、拆分資源粒度         |
| 續租失敗與重入衝突同時上升      | 租約時間與工作耗時不匹配       | 重設租約、加入 fencing token     |
| 相同任務重複執行率上升          | 鎖語意失效或持鎖者判定漂移     | 檢查時鐘與網路、補下游去重       |
| 網路抖動時 split brain 事件增加 | 鎖系統與下游防護未對位         | 補下游版本檢查、限制高風險操作   |
| 鎖系統穩定但業務仍不一致        | 問題層級在資料一致性而非協調層 | 回到 transaction/constraint 設計 |

## 常見誤區

把分散式鎖當作通用一致性解法，會讓錯誤責任落在錯誤層級。鎖負責互斥協調，資料正確性由資料模型與交易邊界保護。

把租約時間固定為常數，也會在流量波動下放大風險。租約策略需要和任務耗時分布與錯誤模型一起校準。

## 案例回寫

分散式鎖語意可用 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) 的控制面切換段落回寫。若切換期間同一任務被多節點同時執行，通常是租約續租與下游防重機制未對位。
這個案例主要支撐的是「互斥語意在切換期失效」判讀，不直接支撐快取命中率或 TTL 分布調整；若根因是回源尖峰，應回到 2.2/2.3。

回寫時先判讀鎖失效是否來自時序漂移、網路分割或續租策略，再把高風險路徑接到 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/) 做故障演練。

## 跨模組路由

1. 與 2.2 的交接：鎖搭配失效策略回到 [cache aside 與失效策略](/backend/02-cache-redis/cache-aside/)。
2. 與 1.3 的交接：高價值資料一致性回到 [transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。
3. 與 6.20 的交接：鎖失效演練與停損條件回到 [Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)。
4. 與 8.19 的交接：鎖衝突與回退判斷回到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

要看快取層一致性與容量壓力，接著讀 [2.3 TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)。要看鎖語意在事故裡的擴散方式，接著讀 [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)。
