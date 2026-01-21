---
title: "案例研究：元編程實戰"
date: 2026-01-21
description: "基於 Hook 系統的元編程實戰案例"
weight: 10
---

# 案例研究：元編程實戰

本系列案例基於 `.claude/lib` 的實際程式碼，展示如何用元編程技術解決實際問題。

## 案例列表

| 案例 | 素材 | 進階技術 | 難度 |
|------|------|----------|------|
| [宣告式驗證](declarative-validation/) | hook_validator.py | Descriptor Protocol | ⭐⭐ |
| [自動註冊機制](auto-registration/) | hook_validator.py | Metaclass | ⭐⭐⭐ |
| [類似 Django Field](field-descriptor/) | hook_io.py | Descriptor + dataclass | ⭐⭐⭐ |

## 學習路徑

```text
宣告式驗證（入門）
    ↓
自動註冊機制（進階）
    ↓
類似 Django Field（整合）
```

## 先備知識

建議先完成以下章節：

- [2.1 Descriptor Protocol 完整指南](../descriptors/)
- [2.2 Metaclass 設計與應用](../metaclasses/)

---

*返回：[模組二：元編程](../)*
