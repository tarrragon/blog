---
title: "NIST SP 800-61r3：事故回應作為風險管理能力"
tags: ["NIST", "Incident Response", "CSF"]
date: 2026-04-30
description: "把 NIST SP 800-61r3 轉成藍隊事故回應與風險治理素材"
weight: 72511
---

NIST SP 800-61r3 的素材責任是把事故回應放進整體資安風險管理。NIST 在 2025 年 4 月發布 Rev. 3，並說明它取代 2012 年的 Rev. 2，定位為 CSF 2.0 community profile。

## 來源定位

[NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) 適合支撐「事故回應需要跨 Identify、Protect、Detect、Respond、Recover、Govern」的論點。它把 incident response 從單一救火流程，轉成涵蓋治理、偵測、回應與復原的風險管理能力。

## 可引用論點

| 可引用論點             | 藍隊轉譯                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------- |
| 事故回應屬於風險管理   | 7.B 可把 incident routing 接到治理例外與 [tripwire](/backend/knowledge-cards/tripwire/) |
| CSF 2.0 六大功能都參與 | 控制面地圖需要同時包含偵測、回應、復原與治理                                            |
| 回應效率需要前置準備   | [runbook](/backend/knowledge-cards/runbook/)、owner、evidence chain 要在事故前建立      |

## 後端服務轉譯

後端服務引用這張卡時，重點是把事故回應拆成工程欄位。常見欄位包含 signal、[severity](/backend/knowledge-cards/incident-severity/)、owner、[containment](/backend/knowledge-cards/containment/) action、[rollback](/backend/knowledge-cards/rollback-strategy/) route、evidence target 與 post-incident write-back。

## 引用限制

NIST 適合提供流程與治理基準，具體控制項仍要回到服務架構轉譯。若文章要討論 API gateway、queue、[artifact](/backend/knowledge-cards/artifact-provenance/) registry 或 database 的細節，需搭配 05/06/08 實作章節補足。
