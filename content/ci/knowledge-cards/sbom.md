---
title: "SBOM"
date: 2026-05-21
description: "說明 Software Bill of Materials 如何揭露 artifact 內含元件，支撐供應鏈掃描與例外治理"
tags: ["CD", "security", "supply-chain", "knowledge-card"]
weight: 20
---

SBOM 的核心概念是「列出 artifact 內含軟體元件」。它把 [Artifact](/ci/knowledge-cards/artifact/) 的依賴組成顯性化，並支援 image scan、license review 與 vulnerability exception。

## 概念位置

SBOM 位在 build、scan、release 與 compliance review 之間，常見格式包含 SPDX、CycloneDX 或工具自訂輸出，並與 [Image Digest](/ci/knowledge-cards/image-digest/) 綁定同一份 artifact。

## 可觀察訊號

- 團隊需要知道 image 或 package 包含哪些 dependency。
- 漏洞公告需要快速判斷受影響 artifact。
- 高治理環境要求 release 產物附帶供應鏈證據。

## 接近真實服務的例子

Container image 發布時同時產生 SBOM，scan gate 依 SBOM 對照 CVE 與 license policy。若 base image 發現 critical vulnerability，團隊可查哪些 release digest 受影響。

## 設計責任

SBOM 要定義產出時機、格式、保存位置、artifact 對應關係與例外審核流程，讓供應鏈風險可以被查詢與治理。
