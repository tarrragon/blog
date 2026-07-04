---
title: "11.C64 RFC 4918 207 Multi-Status：status line 降格為「請讀 body」"
date: 2026-07-04
description: "一個 status code 裝不下批次結果：WebDAV 把每資源狀態下放到 body、解析責任隨之轉給 consumer"
weight: 64
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供「status 表達力不足」的規範層正面承認：207 的設計本身就是承認單一 status 裝不下多個獨立結果。

## 觀察

RFC 4918 §11.1 定義：「The 207 (Multi-Status) status code provides status for multiple independent operations」。§13 明文：頂層雖回 207、「the recipient needs to consult the contents of the multistatus response body for further information about the success or failure of the method execution. The response MAY be used in success, partial success and also in failure situations.」body 是 XML `multistatus` root、每個 `response` 元素帶各自資源的 status。

## 判讀

207 是規範層對 status line 表達力不足的正面承認 —— 頂層 status 降格為「請去讀 body」的訊號、真正的成功失敗判定移進 payload。兩端張力落在 consumer：generic HTTP client 與中介層（retry、cache、監控）只看 status line、207 對它們一律是「成功」、部分失敗只有讀得懂 body schema 的 client 才看得到。provider 換到了表達力、代價是把解析責任整包轉給 consumer —— 跟 Google AIP 的反向立場（見 C65）形成兩條路線的正面對照。

## 對應大綱

11.11 status 表達力邊界章「部分成功」段（規範層先例、與 C65 對照）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [HTTP Extensions for WebDAV（RFC 4918）](https://www.rfc-editor.org/rfc/rfc4918.html) — 一手 IETF spec、Proposed Standard。已 WebFetch 驗證、逐字引文另以 rfc-editor 官方 .txt 取回核對。

## 二手來源與狀態標注

207 是 WebDAV 擴充 status、不在 RFC 9110 核心語意內 —— 一般 REST API 借用 207 等於引入 WebDAV 語意、引用時標明脈絡。
