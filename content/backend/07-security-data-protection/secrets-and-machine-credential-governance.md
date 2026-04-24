---
title: "7.6 秘密管理與機器憑證治理"
date: 2026-04-24
description: "整理 secret、token、key 與機器憑證治理的大綱與路由"
weight: 76
---

本章的責任是定義秘密管理與機器憑證的觀念邊界。核心輸出是憑證分域、生命週期與事件收斂路由，讓服務可以一致管理機器身份風險。

## 大綱

- 憑證分類：human credential、service credential、ephemeral token
- 分域策略：用途分域、環境分域、權限分域
- 生命周期治理：發放、更新、撤銷、淘汰
- 事件收斂：供應商事件後的輪替與盤點節奏
- 案例映射：GitHub OAuth、CircleCI、Cloudflare、Storm-0558
- 路由章節：05 部署、08 incident-response
