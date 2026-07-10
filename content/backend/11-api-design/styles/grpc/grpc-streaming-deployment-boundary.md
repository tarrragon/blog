---
title: "gRPC streaming 與部署邊界：trailers、proxy 與 debug 可及性"
date: 2026-07-03
description: "選 gRPC 前要先確認的部署約束：瀏覽器過不了 trailers 需翻譯 proxy、on-call 徒手 debug 的可及性代價"
weight: 2
tags: ["backend", "api-design", "grpc"]
---

選 gRPC 之前要先確認一組部署約束、這組約束在協議能力表上通常缺席：協議要求端到端 HTTP/2 加 trailers、瀏覽器不能直接連、on-call 的人不能用 `curl` 徒手戳。這些是選型時要先算進去的成本，跟 gRPC 該不該存在無關。本文把這條「操作可及性」判準軸拆開、對應 [11.2 的操作可及性軸](/backend/11-api-design/api-style-selection/)。

## trailers 與瀏覽器：協議事實層面的約束

gRPC 用 HTTP/2 的 trailers（在 response body 之後才送的 metadata）傳狀態碼、這是協議規格、不是實作選擇。約束由此而來：瀏覽器的 fetch API 讀不到 trailers、所以瀏覽器不能直接當 gRPC client、要靠 gRPC-Web 加一個翻譯 proxy 把 trailers 搬進 body（見 [11.C32](/backend/11-api-design/cases/grpc-kmcd-bad-parts/)、獨立實踐者批評）。同樣的 trailers 依賴也讓中間層變挑剔 —— 不是每個 LB、proxy、防火牆規則都原樣放行 HTTP/2 trailers。

這條約束值得跟立場切開看。指出它最完整的一手清單來自 Buf 的 Connect 發布文（見 [11.C30](/backend/11-api-design/cases/grpc-buf-connect-critique/)）、而 Buf 是提供競品的利益相關方、它對 grpc-go 實作的批評（自帶 HTTP/2、不與其他 HTTP 流量共存）帶立場。但「瀏覽器讀不到 trailers、需要翻譯 proxy」是可獨立驗證的協議事實、跟誰在批評無關 —— C32 的獨立批評指向同一點、兩個來源互證後這條約束脫離 vendor 立場成立。使用層的判讀：如果介面要被瀏覽器直接消費、gRPC-Web 加 proxy 是必經的一層、選型時就要把這層 infra 算進成本。

這組約束有一條中間路線。同一份 C30 除了批評、也給了解方 Connect protocol：建在 `net/http` 上、以 HTTP/1.1 承載、同時支援 gRPC、gRPC-Web、Connect 三種協議、瀏覽器原生可連、JSON 版也能 `curl`。它放寬了「端到端 HTTP/2 加 trailers」這組約束、代價是離開純 gRPC 生態(Connect 是 Buf 自家協議)。所以部署邊界不是「要 proto 就得吞下整組 gRPC 約束」的二選一 —— 要 proto 契約與 codegen、但消費端有瀏覽器或過不了 HTTP/2 的中間層時、Connect 這格比硬架 gRPC-Web proxy 省事。

## debug 可及性：cURL 測試

介面上線後會被 on-call 的人徒手戳、這個場景在效率比較裡沒有位置、卻是 gRPC 收利息的地方。這位獨立實踐者提出一個可操作的判準 ——「傳一個 cURL 範例給朋友」測試：一個 HTTP+JSON endpoint 可以貼一行 `curl` 讓對方立刻重現、gRPC 的 binary protobuf over HTTP/2 做不到、要對方裝 client、載 proto、才能發一個請求。這個差距在正常運作時看不到、在半夜排查一個異常請求時變成實質成本。

判準要平衡地用。C32 同時承認生態已修補部分問題：Buf CLI、ConnectRPC、Postman 對 gRPC 的支援讓「徒手戳」不再完全不可行。所以這條軸的現況不是「gRPC 不能 debug」、而是「gRPC 的 debug 需要預先備好工具鏈、不像 HTTP+JSON 零準備可及」。選型判讀：團隊有沒有把這套工具鏈鋪到每個會碰介面的人手上、決定這條軸的實際權重。

## 這條軸的權重隨組織而變

部署邊界與 debug 可及性的成本不是固定值、跟組織能不能在框架層集中吸收它成反比。有平台團隊統一處理 proxy、觀測、client 工具鏈的組織、這些成本被平台吸收、個別服務作者感受不到；每個介面都要作者自己扛 proxy 與 debug 的小團隊、可及性差的代價會在 on-call 時逐次付還。這條「集中吸收 vs 逐次付還」的判讀、在 [內部 RPC 的選型位置](/backend/11-api-design/styles/grpc/grpc-internal-rpc-selection/) 用規模兩端展開。

## 下一步路由

- gRPC 值得選的組織前提：[內部 RPC 的選型位置](/backend/11-api-design/styles/grpc/grpc-internal-rpc-selection/)
- 三軸選型判準：[11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)
- proto 契約怎麼演進：[proto 演進紀律](/backend/11-api-design/styles/grpc/grpc-proto-evolution-discipline/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
