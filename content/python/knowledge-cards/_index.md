---
title: "Knowledge Cards"
tags: ["前置知識卡片", "Knowledge Cards"]
date: 2026-10-19
description: "Python 教學章節引用的語言與工具術語卡片；語言無關的設計原則在軟體設計原則模組"
weight: -1
---

本模組的知識卡片收錄 Python 語言與工具鏈特有的術語。語言無關的設計原則（單一職責、發散式變更、散彈式修改）放在[軟體設計原則](/design-principles/knowledge-cards/)，測試策略的通用術語（特徵測試、test double）放在 [Testing 知識卡片](/testing/knowledge-cards/)。

## 測試

| 卡片                                                                  | 核心問題                                                         |
| --------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [pytest fixture（測試夾具）](/python/knowledge-cards/pytest-fixture/) | 測試參數由 pytest 依名稱注入——準備與清理怎麼和斷言分開           |
| [monkeypatch（測試期間的替換）](/python/knowledge-cards/monkeypatch/) | 替換要對準程式執行時查找的那個名字——拆模組之後替換為什麼靜默失效 |
