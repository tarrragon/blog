---
title: "Serverless function 版本、事件來源與回復流程"
date: 2026-05-21
description: "說明 Lambda / Cloud Functions / Edge Functions CI/CD 如何管理 function artifact、alias、IAM、event source、retry 與 rollback"
tags: ["CI", "CD", "serverless", "function", "rollback"]
weight: 1
---

Serverless 發布流程的核心責任是把函式 artifact、[Function Alias](/ci/knowledge-cards/function-alias/)、權限與 [Event Source](/ci/knowledge-cards/event-source/) 一起推進。Serverless 部署看起來比長駐服務短，但每次 invocation 都依賴 runtime、IAM、event source、retry policy 與 observability；CI/CD 需要把這些條件視為發布契約。

## 流程定位

Serverless 的風險集中在觸發條件。函式部署成功只代表新版本存在，實際風險會在 HTTP request、queue message、topic event、scheduled job 或 edge request 觸發時出現。發布流程要能區分「版本建立成功」「alias 切流量成功」「事件來源行為正確」三件事。

| 階段                                              | 責任                                    | 判讀訊號                            |
| ------------------------------------------------- | --------------------------------------- | ----------------------------------- |
| Package                                           | 產生 function bundle / layer            | dependency、runtime target 是否固定 |
| Version                                           | 發布 immutable function version         | version 是否可追到 commit           |
| Alias / traffic                                   | 控制新舊版本流量                        | alias 權重、錯誤率、冷啟動          |
| Permission                                        | 限制 IAM、secret、resource policy       | 最小權限與環境隔離                  |
| [Event Source](/ci/knowledge-cards/event-source/) | 管理 trigger、retry、dead-letter        | 重試與毒訊息處理是否明確            |
| Recovery                                          | alias rollback、disable trigger、replay | 是否能止血與修補資料                |

Package 階段負責產生可執行 bundle。Serverless 常見失敗是本機 dependency 可用，但打包後缺檔、runtime target 不符、native extension 不相容或 layer 版本漂移；CI 應在接近目標 runtime 的環境做 smoke test。

Version 階段負責建立不可變版本。直接覆蓋 `$LATEST` 會讓事故追溯困難；正式流量應指向 version 或 [Function Alias](/ci/knowledge-cards/function-alias/)，讓 rollback 能把 alias 切回前一個已知版本。

[Function Alias](/ci/knowledge-cards/function-alias/) / traffic 階段負責控制流量切換。HTTP function 可以用少量權重 canary；queue trigger 則要觀察 batch failure、retry、dead-letter 與 downstream side effect，因為同一個錯誤 event 可能被重試多次。

Permission 階段負責限制 blast radius。Serverless 函式容易因部署方便而累積過大 IAM 權限；每個 function 應只拿到必要 resource、secret 與 network access，並把 production secret 與 preview / staging 隔離。

[Event Source](/ci/knowledge-cards/event-source/) 階段負責定義失敗重送語意。Queue、topic、object storage、HTTP 與 scheduler 的錯誤行為不同；CI/CD 文件要記錄 retry 次數、dead-letter destination、batch size、concurrency limit 與 replay 條件。

Recovery 階段負責止血。Serverless 常見止血方式是 alias rollback、停用 trigger、降低 concurrency、清理毒訊息、重放事件或 forward fix；只回退 code 版本不一定能處理已經排入 queue 的事件。

## 事件來源判讀

事件來源判讀的責任是找出失敗是否可重試。Serverless 常被誤判為「函式自己失敗」，但實際根因可能是 event schema、權限、上游重試或下游限流。

| Event source | 常見失敗                        | 下一步                                 |
| ------------ | ------------------------------- | -------------------------------------- |
| HTTP / API   | status code、timeout、冷啟動    | 看 latency、concurrency、alias         |
| Queue        | batch failure、毒訊息、重試風暴 | 看 DLQ、batch size、visibility timeout |
| Topic        | event schema 漂移               | 驗證 publisher / subscriber 契約       |
| Object store | 權限或路徑 pattern 錯誤         | 檢查 resource policy 與 filter         |
| Scheduler    | timezone、重入、上次執行未完成  | 檢查 idempotency 與 lock               |

這張表讓 release failure 能被導向正確 owner。若 event schema 變了，修 function 可能只是表面補丁；真正的 gate 要加在 publisher contract 或 sample event validation。

## 最小發布 gate

Serverless workflow 的最小 gate 應覆蓋 package、permission、event 與 alias。缺其中一段，部署成功就可能只是建立了一個尚未被驗證的函式版本。

1. Package bundle，固定 runtime target 與 dependency。
2. 對 bundle 執行 unit / contract / sample event test。
3. 用 least privilege policy 做 deploy dry run 或 policy diff。
4. 發布 immutable function version。
5. 用 alias 將少量流量導向新版本。
6. 觀察 error、latency、retry、DLQ 與 downstream 指標。
7. 指標穩定後提高 alias 權重或完成切換。
8. 指標觸發 tripwire 時切回 alias、停用 trigger 或啟動 repair。

這個流程把 Serverless 發布從「上傳函式」提升成可回復流程。對事件驅動函式而言，trigger 與 retry policy 是發布契約的一部分。

## 下一步路由

- Serverless 部署總覽：回 [Serverless 部署 CI/CD](../)。
- Rollout 概念：讀 [Rollout Strategy](/ci/knowledge-cards/rollout-strategy/)。
- 失敗處理：讀 [CI 失敗到修復發布流程](../../github-actions-failure-flow/)。
