---
title: "SBOM"
date: 2026-05-21
description: "說明 Software Bill of Materials 如何揭露 artifact 內含元件，支撐供應鏈掃描與例外治理"
tags: ["CD", "security", "supply-chain", "knowledge-card"]
weight: 20
aliases: ["/ci/knowledge-cards/sbom/"]
---

SBOM 的核心概念是「列出 artifact 內含軟體元件」。它把 [Artifact](/devops/ci/knowledge-cards/artifact/) 的依賴組成顯性化，並支援 image scan、license review 與 vulnerability exception。

## 跟其他概念的關係

SBOM 位在 build、scan、release 與 compliance review 之間，常見格式包含 SPDX、CycloneDX 或工具自訂輸出，並與 [Image Digest](/devops/ci/knowledge-cards/image-digest/) 綁定同一份 artifact。

## 可觀察訊號

- 團隊需要知道 image 或 package 包含哪些 dependency。
- 漏洞公告需要快速判斷受影響 artifact。
- 高治理環境要求 release 產物附帶供應鏈證據。

## 接近真實服務的例子

Container image 發布時同時產生 SBOM，scan gate 依 SBOM 對照 CVE 與 license policy。若 base image 發現 critical vulnerability，團隊可查哪些 release digest 受影響。

## 判斷條件與後果

SBOM 派上用場的時機是漏洞公告發布之後：團隊要從 CVE 回查哪些 release 帶著受影響的元件。SBOM 沒有綁定 image digest 時，查得到某份 SBOM 含有那個元件，卻對不回是哪一個已發布的產物；SBOM 只在部分建置產出、或產出後沒有集中保存時，這次查詢有缺口，缺的那幾個 release 是否受影響要重新掃描才知道。格式採用 SPDX 或 CycloneDX 這類標準時，scan gate 與其他工具讀得懂同一份檔案；工具自訂的輸出只有產生它的那套工具讀得懂。核准過的漏洞例外沒有記錄核准者與到期條件時，下一次掃描分辨不出哪些命中已經審過。
