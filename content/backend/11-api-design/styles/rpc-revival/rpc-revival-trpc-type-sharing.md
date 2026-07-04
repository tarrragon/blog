---
title: "tRPC 型別共享：型別即契約的前提與代價"
date: 2026-07-03
description: "tRPC 靠 TypeScript 型別推導同步契約、零 codegen；適用同倉 TS-only、公開第三方 API 不適用"
weight: 1
tags: ["backend", "api-design", "rpc"]
---

tRPC 的選型位置是「前後端同倉、且都是 TypeScript」這個消費者形狀 —— 在這個形狀裡它把契約同步的成本壓到最低、離開這個形狀它的前提就不成立。做法是把 API 契約放進 TypeScript 型別系統本身：server 定義 router、client 直接推導出型別、中間沒有 IDL 檔、沒有 codegen。官方對這個定位的措辭是「build & consume fully typesafe APIs without schemas or code generation」（見 [11.C33](/backend/11-api-design/cases/rpc-trpc-design-philosophy/)、tRPC 官方文件）。以下拆這個換法的前提、代價、與什麼時候別用。

## 前提：同倉 TS-only

型別推導能當契約、靠的是 client 與 server 在同一個 TypeScript 專案裡一起編譯 —— 這是 tRPC 官方 FAQ 自己標明的前提。脫離 monorepo、client 就失去「跟 server 型別一起運作」的保證；唯一的替代是把 backend 型別發成 private npm package 讓 client 依賴。這條前提直接鎖死兩個維度：語言鎖定 TypeScript（型別推導不跨語言）、部署形態鎖定同倉或私有套件。官方也自列一個能力邊界：動態型別輸出做不到、因為它需要 higher-kinded types（型別的型別、TypeScript 型別系統目前還沒到的能力上限）。

落到操作、判斷很乾脆：消費者是不是你自己團隊、跟 server 共用同一個 TS 倉。是 —— tRPC 的零 codegen 是真優勢；不是 —— 前提不成立、優勢歸零。作者社群把這條邊界說得很白：tRPC 無法有效服務公開的第三方 API（見 [11.C23](/backend/11-api-design/cases/graphql-echobind-trpc-retreat/) 作者自列）。公開 API 的消費者是你控制不了的匿名開發者、他們沒有你的型別、也不會為了呼叫你裝一個 TS 專案 —— 這個形狀要把答案推回 HTTP+JSON。

## 代價的另一面：契約中介層何時變純開銷

tRPC 的優勢反過來看、是「契約中介層」在單一團隊場景下的成本。一個真實團隊的量化帳可以把這個成本說清楚：Echobind 從 GraphQL 遷到 tRPC 前、同一份資料形狀要在 Prisma、Nexus、GraphQL operations、codegen types、client queries 五層各宣告一次；三層 codegen 產出 8,200 行型別檔、常需重啟編輯器的 language server；依賴體積 GraphQL 側 81.2kb、tRPC 側 23.7kb；遷移後淨減 1,608 行程式碼（見 [11.C23](/backend/11-api-design/cases/graphql-echobind-trpc-retreat/)）。

這些數字不是要證明 tRPC 比 GraphQL 好、而是劃出一條判準：schema 這個中介層、在「跨團隊、跨 client 的契約」場景是價值、在「單一團隊同時擁有前後端」場景變純開銷。同構 TypeScript 的單團隊、多維護一份 schema 換不到跨方協調的好處、只多出五層宣告要同步。判讀訊號因此是「這份 schema 在協調誰」：協調不同團隊或不同語言的 client、留著；只在協調你自己前後端、它是可以拿掉的中間層。但「單團隊」不直接等於「拿掉」—— 需要對外 API 文件、要跑 contract test、或預期未來出現非 TypeScript 消費者（mobile、第三方）時、schema 仍賺得回維護成本；拿掉的前提是這三者都不成立。同一份帳也出現在 [公開 API 的 GraphQL 進退](/backend/11-api-design/styles/graphql/graphql-public-api-tradeoffs/) 的適用邊界段、兩章從 GraphQL 與 tRPC 兩側看同一條界線。

## schema-first vs inference-first：契約放在相反的地方

tRPC 與 [gRPC 的 proto](/backend/11-api-design/styles/grpc/grpc-proto-evolution-discipline/) 都在解同一個問題 —— 契約怎麼跨 client 與 server 同步 —— 但把契約放在相反的地方。protobuf 走 schema-first：契約是一份外置的 IDL 檔、跨語言、可用 CI 做 breaking 檢查、代價是要維護檔案與 codegen。tRPC 走 inference-first：契約是型別推導的結果、零 codegen、代價是鎖定單一語言與同倉。這組對照是演進成本這條選型軸的具體兩極：團隊承擔得起「外置 schema 的維護」還是需要「零 codegen 的即時同步」、判準見 [11.2](/backend/11-api-design/api-style-selection/)。

## 下一步路由

- 契約外置的對照路線：[gRPC proto 演進紀律](/backend/11-api-design/styles/grpc/grpc-proto-evolution-discipline/)
- 另一種輕量 RPC 的適用條件：[JSON-RPC 的適用條件](/backend/11-api-design/styles/rpc-revival/rpc-revival-jsonrpc-conditions/)
- 同一條邊界的 GraphQL 側：[公開 API 的 GraphQL 進退](/backend/11-api-design/styles/graphql/graphql-public-api-tradeoffs/)
- 三軸選型判準：[11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
