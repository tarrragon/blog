---
title: "Token Revocation"
tags: ["權杖撤銷", "Token Revocation"]
date: 2026-04-24
description: "說明事件中如何撤銷 token，縮短可利用窗口"
weight: 266
---

Token revocation 的核心概念是「在事件節奏內讓既有 token 失去授權效力」。它是第三方事件與身分事件中的關鍵收斂能力。

## 概念位置

Token revocation 位在 [authorization](../authorization/)、[secret-management](../secret-management/)、[incident-severity](../incident-severity/) 與 [runbook](../runbook/) 之間。它常與 token 分域策略一起使用。

## 可觀察訊號與例子

系統需要 token 撤銷能力的訊號是供應商事件後 token 仍可存取敏感資產，或可疑 token 在事件後持續被使用。OAuth token、API token 與 service token 都屬於常見對象。

## 設計責任

token 撤銷要定義分域、優先級、批次策略與可回查紀錄。事件中要能先撤銷高風險 token，再依業務優先級逐步恢復必要授權。

