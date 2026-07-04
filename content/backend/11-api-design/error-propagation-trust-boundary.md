---
title: "錯誤傳播與信任邊界：中間服務的雙重身分"
date: 2026-07-04
description: "錯誤跨服務傳遞時誰該轉譯、收到的錯誤能信多少、對外暴露多少細節 — 服務鏈上每一跳同時是 consumer 與 provider 的責任判準"
weight: 23
tags: ["backend", "api-design", "error-contract"]
---

服務鏈上的錯誤處理有一個單服務視角看不到的結構：A 呼叫 B、B 呼叫 C、C 掛了 —— B 對 C 是 consumer、對 A 是 provider、**同一個服務在同一次失敗裡承擔兩份契約責任**。C 的錯誤怎麼變成 B 回給 A 的錯誤、是每個中間服務都要回答的設計題；答錯的形態是把上游錯誤原樣倒給下游（洩漏 + 語意錯位）、或把一切包成不可判讀的 500（資訊消滅）。三個判準依序展開：錯誤的哪一層能傳多遠、收到的錯誤能信多少、對外暴露多少。本文掛在 [11.11 雙向契約](/backend/11-api-design/error-bidirectional-contract/)；跨服務轉譯沒有單一規範明文、本文的責任推導從各規範的單跳條款出發、逐處標明。

## 錯誤契約有保證層與選配層、傳播能力不同

gRPC 的兩層錯誤模型把這件事講得最清楚：標準模型（status code 加 optional message）是所有語言 client 都拿得到的保證層；richer error model（`google.rpc.Status` 帶結構化 detail）是選配層 —— 官方自列它的三個傳播風險：語言支援不全、payload 撞 header 上限、以及最關鍵的一條：detail 走 trailing metadata（trailer 在回應串流結束後才送出、多數中介層只讀開頭的 header）、**proxy 與 logger 看不到**（見 [11.C73](/backend/11-api-design/cases/errorchain-grpc-two-layer-model/)）。

工程含義：錯誤資訊的可見範圍分層 —— status code 全鏈可見（每一跳、每個中介層都讀得到）、結構化 detail 只有端點可見（中間節點對它是盲的）。設計錯誤契約時要按這個分層放資訊：中介層要用的（可不可重試、要不要熔斷）必須放在全鏈可見層、放進 detail 就等於對整條鏈的基礎設施隱形。HTTP 系的對應是 status 全鏈可見、body 端到端 —— 同構的分層、同樣的設計判準。

## 收到的錯誤能信多少：產生者歧義

中間服務轉譯錯誤前、先要判斷收到的錯誤是誰說的。gRPC 的 status codes 文件給了一手根據：17 個 code 裡只有 7 個（INVALID_ARGUMENT、NOT_FOUND、ALREADY_EXISTS、FAILED_PRECONDITION、ABORTED、OUT_OF_RANGE、DATA_LOSS）保證來自 server 應用邏輯、library 從不自產；UNAVAILABLE、DEADLINE_EXCEEDED、INTERNAL 則可能是中間 channel 或 library 產生 —— consumer 單看 code 分不出來（見 [11.C74](/backend/11-api-design/cases/errorchain-grpc-code-producer-ambiguity/)）。

這對轉譯的含義（推導、標明）：錯誤的可信度不均質。收到「保證來自應用」的 code、語意可以直接轉譯（NOT_FOUND 就是資源不在）；收到產生者不明的 code、轉譯往「暫時性」收斂 —— 回自己的 UNAVAILABLE 或 502 並標可重試、不映射成上游的業務錯誤；要保留產生者線索、放進結構化 detail 而非原樣透傳。它可能只是網路層的一次抖動、不代表上游的業務判斷。中間服務原樣透傳 UNKNOWN 或 INTERNAL、等於把「產生者是誰」的資訊消滅掉、下游拿到的錯誤比你拿到的更不可判讀 —— 資訊只會在鏈上遞減、不會自己恢復。

## 轉譯的責任：對上游是誰的錯、對下游要換語意

中間服務回給下游的錯誤、語意主詞要換。C 掛了、對 B 是「我的依賴壞了」；但 B 回給 A 的錯誤要回答的是 A 的問題 ——「我的請求怎麼了」。判準（推導）：上游的 5xx 到你這裡、對下游是你的 502/503（你的服務暫時無法完成、可重試）、不是把 C 的 500 連 body 一起倒出去；上游的 4xx 要分辨 —— 是你組請求組錯了（你的 bug、對下游是你的 500）、還是下游的輸入真的非法（對下游還是 4xx、但錯誤內容要換成下游看得懂的欄位名與語彙）。原樣透傳最誘人的時刻是趕工期、它把三種成本外部化：下游拿到不知所云的錯誤（解析成本）、上游的內部細節穿透兩層信任邊界（安全成本）、除錯時分不清錯誤源頭（定位成本）。把轉譯責任制度化的常見做法是收斂到專職層 —— BFF 或 gateway 統一做錯誤轉譯、個別服務只處理自己直接依賴的錯誤（gateway 的執行面屬 [05 部署平台](/backend/05-deployment-platform/)）。

## 暴露多少：機器可讀與偵察面的對撞

錯誤內容該多詳細、有兩股方向相反的一手規範、對撞出中間路線。安全端要求少暴露：OWASP 的規則是非預期錯誤回 generic response、細節只留 server side log —— stack trace 洩漏框架版本、SQL error 幫攻擊者找 injection point、錯誤訊息是攻擊者的偵察面（見 [11.C77](/backend/11-api-design/cases/errorchain-owasp-error-handling/)、攻擊面思路同 [07 安全](/backend/07-security-data-protection/)）。可用性端要求夠機器可讀：全 generic 的錯誤讓 consumer 完全無法自助、每個錯誤都變成 support ticket。

Google 的 API 設計規範 AIP-193 用三層受眾設計走出中間路線（見 [11.C75](/backend/11-api-design/cases/errorchain-aip193-error-content/)）：機器層給 `ErrorInfo` 的 (reason, domain)、可程式化分支的穩定識別符 —— 但「error messages must not assume that the user will know anything about its underlying implementation」、識別符用 consumer 的語彙命名、不洩內部結構；開發者層給 message、人類可讀的 debug 訊息、可以變動、定位上不可當 API；使用者層給 LocalizedMessage —— 呈現給終端使用者的文案。三層各給對的受眾、既不是 generic 到無法自助、也不是把內部狀態倒出來。附帶一條反向條款：舊 API 沒給機器可讀欄位的、AIP 要求 message 內容必須穩定 —— consumer 已經在 parse 它、改字就是 breaking change；不給機器層、人類層就會被迫變成契約。

## 下一步路由

- 雙向契約的框架：[11.11 Status 與錯誤的雙向契約](/backend/11-api-design/error-bidirectional-contract/)
- 錯誤格式的 producer 側設計：[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)
- 回報時的定位鉤子：[錯誤回報的回饋迴路](/backend/11-api-design/error-feedback-loop/)
- 錯誤訊息的攻擊面：[07 安全與資料保護](/backend/07-security-data-protection/)
- dependency call 的診斷欄位（upstream、response class、circuit state）：[4.19 Debuggability by Design](/backend/04-observability/debuggability-by-design/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
