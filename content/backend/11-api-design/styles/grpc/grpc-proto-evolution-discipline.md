---
title: "gRPC proto 演進紀律：編碼層相容與 CI gate"
date: 2026-07-03
description: "要改 proto 又得保證 wire 相容、並想把相容檢查落成 merge 前 CI gate、選檢查等級時的判準"
weight: 1
tags: ["backend", "api-design", "grpc"]
---

proto 的演進紀律建立在一個跟其他風格不同的前提上：相容性是編碼格式的性質、不是 code review 的慣例。protobuf 用 field number 當 wire format 的欄位識別、所以「哪些變更安全」由編碼規則決定、而非團隊約定。這讓 gRPC 的契約演進可以做成機器可檢的 CI gate、也讓它的紀律比 JSON 硬。本文回答兩件使用層的事：proto 該怎麼改才安全、以及怎麼把這條紀律放進 CI。跨風格的變更紀律框架（格式層 / 工具層 / 流程層）主寫在 [11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)、本文是 gRPC 內部機制的深化。

## 安全的變更由編碼規則界定

protobuf 官方語言規範把 schema 變更分三類：wire-unsafe、wire-safe（加欄位、加 enum 值、刪欄位皆安全）、conditionally wire-compatible（見 [11.C28](/backend/11-api-design/cases/grpc-protobuf-field-number-discipline/)）。判準是 wire format 認不認得出差異、不是欄位語意變沒變。加欄位安全、因為舊 client 不認得新編號就跳過；刪欄位安全、因為對應編號的資料被當未知欄位忽略。

這條規則的硬核是 field number 不可重用。編號一旦投入使用即固定、因為它就是 wire 上的欄位身分；刪欄位後必須 `reserved` 該編號、擋住未來誤用。重用一個舊編號、wire 解碼會把新欄位的 bytes 當成舊欄位解、後果落在資料層 — 官方列舉的後果包含 parse / merge error、PII 洩漏、資料損毀；解碼報錯只是其中一種結局、多數情況是靜默的損毀。使用層的操作紀律因此只有兩條：只加不改、刪了就永久 reserve 編號。把相容性做進編碼層不是 protobuf 獨有 —— Thrift 的 field id、Avro 的 schema resolution 是同一類機制、演進判準類似；本文聚焦 protobuf 是因為它的生態成熟度（buf）與本模組的案例密度。

## 從自律升級成 CI gate

編碼規則界定了安全範圍、但「只加不改」靠人腦守不住 — 破壞發生在多層、改欄位名破壞 generated code、改型別破壞 wire format、人工 review 抓不全。`buf breaking` 把這條紀律做成 merge 前的自動檢查：對比歷史版本 schema、擋下如「Field 1 type int32 改 string」這類變更。官方文件對這個定位的措辭直接 —「Catching this before merge is the point」（見 [11.C29](/backend/11-api-design/cases/grpc-buf-breaking-detection/)、Buf 官方文件）。

使用層要做的判斷不是「要不要開這個檢查」、而是「檢查到哪一級」。buf 的規則分四級、嚴格程度遞增：WIRE（只保 wire 相容）、WIRE_JSON、PACKAGE、FILE。等級的選擇是產品決策、對應消費者實際依賴的形狀：消費者只透過 wire 通訊、選 WIRE 就夠；有外部程式碼直接 import 你的 generated package、就要 PACKAGE 擋住改套件路徑這種對 wire 無害、卻會炸掉別人 build 的變更。等級選太寬會放行破壞、選太嚴會擋住原本安全的重構 — 判準永遠是回到「誰在依賴這個 schema、依賴到哪一層」。

## 契約放哪裡：與 tRPC 的對照

proto 演進紀律的本質是把契約外置成一份 IDL（介面定義語言）檔、相容性檢查對這份檔做。這跟 [rpc-revival 的 tRPC 路線](/backend/11-api-design/styles/rpc-revival/rpc-revival-trpc-type-sharing/) 形成選型上的對照：tRPC 把契約放進 TypeScript 型別系統、靠推導同步、不產 IDL 檔。兩者都在解「契約怎麼跨 client/server 同步」、差別在契約放在哪 —— proto 外置換到跨語言與 CI 可檢、代價是要維護 IDL 與 codegen；型別內嵌換到零 codegen 的開發體驗、代價是鎖定單一語言。演進成本這條選型軸就是在問團隊承擔得起哪種紀律、判準見 [11.2](/backend/11-api-design/api-style-selection/)。

## 下一步路由

- 跨風格的變更紀律框架：[11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)
- 選了 gRPC 之後的部署約束：[streaming 與部署邊界](/backend/11-api-design/styles/grpc/grpc-streaming-deployment-boundary/)
- gRPC 值得選的組織前提：[內部 RPC 的選型位置](/backend/11-api-design/styles/grpc/grpc-internal-rpc-selection/)
- 契約放型別系統的對照路線：[tRPC 型別共享](/backend/11-api-design/styles/rpc-revival/rpc-revival-trpc-type-sharing/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
