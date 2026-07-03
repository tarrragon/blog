---
title: "Richardson 成熟度的實用讀法"
date: 2026-07-03
description: "RMM 四級當定位與溝通工具的用法、每一級的工程意義、以及把它當合規認證或升級路線圖的誤用邊界"
weight: 3
tags: ["backend", "api-design", "rest"]
---

Richardson 成熟度模型（RMM）是一把定位尺、而非一張認證考卷 — 這個定位出自一手來源自己的聲明：Fowler 在記述這個模型時明文標注、RMM 是理解 REST 元素的思考工具、不是 REST 的分級定義（見 [11.C3](/backend/11-api-design/cases/rest-fowler-richardson-maturity-model/)）。下面依序看四級各自解決什麼、以及常見誤用的邊界在哪。

## 四級的工程意義

| 級別    | 特徵                            | 這一級解決什麼                                   |
| ------- | ------------------------------- | ------------------------------------------------ |
| Level 0 | HTTP 當 RPC 隧道、單一 endpoint | 只把 HTTP 當傳輸、所有語意自己發明               |
| Level 1 | 資源化、逐資源 URI              | 介面有了名詞結構、權限與路由可以按資源切         |
| Level 2 | HTTP method 與 status 正確使用  | 中介層基礎設施（快取、重試、監控）開始能讀懂介面 |
| Level 3 | Hypermedia controls（HATEOAS）  | client 從回應習得可用操作、業務知識收回 server   |

表格是索引、每級的躍遷各有實質收益。Level 0 到 1 的收益是結構：橫切能力（權限、審計、快取鍵）有了掛載單位。Level 1 到 2 的收益是讓基礎設施當盟友：GET 的安全承諾讓 proxy 敢快取、status 的語意讓監控與重試鏈正確運作 — method 與 status 作為承諾的完整判準在 [11.3](/backend/11-api-design/resource-modeling-operation-semantics/)。Level 2 到 3 的收益是解耦 client 的業務知識 — 但這一級的收益前提（存在會跟連結走的 uniform client）在 machine-to-machine 場景多半不成立、完整交鋒見 [Hypermedia 與 HATEOAS 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)。

## 兩個立場事實

用 RMM 之前要知道它在爭論光譜上的位置。其一、Fielding 的立場被 Fowler 記錄在案：只有 Level 3 才算 REST — 依原義、RMM 的前三級都是「還不是 REST」的程度差異、把 Level 2 說成「基本 REST」與原始定義者的立場直接牴觸（定義權爭奪的全景見 [REST 語意學之爭](/backend/11-api-design/styles/rest/rest-semantics-dispute/)）。其二、業界實務多停在 Level 2 — 這是廣泛的觀察、C3 案例的判讀層也如此標注、Fowler 原文沒有這個統計主張、引用時分清楚。

## 誤用一：當合規檢查表

「我們的 API 要通過 Level 2 審查」這類用法把定位尺變成認證考卷、產生兩種浪費。輕的浪費是形式主義：為了「正確使用 PATCH」而在沒有部分更新需求的資源上硬加 PATCH、級別達標、介面多了沒人用的表面積。重的浪費是誤導優先序：Level 2 的實質收益是中介層能讀懂介面 — 檢查的對象該是「快取有沒有實際命中、重試鏈行為是否正確」、而非 method 使用的字面合規。合規檢查表要從自家的 breaking 清單與錯誤模型長出來（[11.6](/backend/11-api-design/backward-compatibility-discipline/)、[11.4](/backend/11-api-design/error-model-design/)）、RMM 的粒度撐不起這個角色。

## 誤用二：當升級路線圖

「今年 Level 2、明年 Level 3」把分級讀成演進方向、隱含「越高越好」— 但 Level 3 的收益前提跟前兩級不同質：前兩級的收益（結構、基礎設施相容）幾乎無條件成立、Level 3 的收益依賴 uniform client 的存在。machine-to-machine API 升到 Level 3、成本照付（回應膨脹、格式選型、server 端組裝 controls）、收益不兌現 — 停在 Level 2 對多數 API 是刻意且正確的終點、而非未完成狀態。

## 實用讀法

RMM 最好的用法是三種對話場景。**定位**：「我們的公開 API 在 Level 2、後台 HTML 介面實質上是 Level 3」— 一句話讓新成員理解兩套介面的設計差異。**驗傷**：接手遺留系統時、「這批 endpoint 在 Level 0（全部 POST 打一個 /api）」直接指出重構的第一刀在資源化、而非欄位微調。**止損**：design review 有人提議「往 Level 3 走」時、RMM 的級別語言讓討論快速聚焦到真正的問題 —「我們的 consumer 是誰、誰會跟連結走」— 而非在抽象的成熟度上表態。三種用法的共同點：RMM 出現在句子裡是為了描述現狀與差異、而非評分。

## 下一步路由

- Level 2 的承諾語意展開：[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)
- Level 3 的收益前提交鋒：[Hypermedia 與 HATEOAS 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)
- 定義權爭奪全景：[REST 語意學之爭](/backend/11-api-design/styles/rest/rest-semantics-dispute/)
- 案例原文：[模組十一案例庫](/backend/11-api-design/cases/)
