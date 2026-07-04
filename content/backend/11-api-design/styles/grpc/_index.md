---
title: "gRPC 流派：proto 演進、部署邊界、內部 RPC 選型"
date: 2026-07-03
description: "gRPC 適合放在哪個選型位置、選了要扛什麼：proto 演進的編碼層紀律、trailers 與 proxy 的部署約束、框架層集中的組織前提"
weight: 3
tags: ["backend", "api-design", "grpc"]
---

gRPC 的選型判讀分三層、對應三篇：契約怎麼安全演進（編碼層紀律 + CI gate）、上線前要知道哪些部署約束（trailers、瀏覽器、debug 可及性）、值得選的組織前提是什麼（框架層集中而非序列化效能）。本目錄不追 gRPC 的技術史、只回答「什麼情境該選、選了怎麼用、什麼時候別選」。中性選型判準見 [11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)。

| 文章                                                                                           | 主題                                             | 案例支撐 |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------ | -------- |
| [proto 演進紀律](/backend/11-api-design/styles/grpc/grpc-proto-evolution-discipline/)          | field number 不可重用、buf 四級 breaking CI gate | C28、C29 |
| [streaming 與部署邊界](/backend/11-api-design/styles/grpc/grpc-streaming-deployment-boundary/) | trailers 與瀏覽器、翻譯 proxy、debug 可及性判準  | C30、C32 |
| [內部 RPC 的選型位置](/backend/11-api-design/styles/grpc/grpc-internal-rpc-selection/)         | 框架層集中的組織前提、規模判讀兩端               | C31、C32 |
