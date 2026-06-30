---
title: "late final 欄位不能用欄位覆蓋 — Dart 欄位的隱藏 getter/setter 機制"
date: 2026-06-30
draft: false
description: "Dart 的 late final 欄位在底層會生成 getter 和 setter。子類用另一個欄位覆蓋時，會產生兩個獨立的儲存槽，父類程式碼讀到的是未初始化的那份，導致 LateInitializationError。Dart analyzer 要求改用 getter 覆寫。"
tags: ["dart", "inheritance", "late", "override", "getter"]
---

## 事件

`AppService` 宣告了 `late final PackageInfo packageInfo;`，在 `init()` 中透過 `PackageInfo.fromPlatform()` 非同步初始化。測試用的 `TestAppService extends AppService` 想跳過平台呼叫，直接給一個固定值：

```dart
// ❌ analyzer 報錯：overridden_fields
@override
late final PackageInfo packageInfo = PackageInfo(...);
```

Dart analyzer 報 `overridden_fields`：欄位覆蓋了從 `AppService` 繼承的欄位。

## 根因：late final 欄位 = getter + setter

Dart 的每個 instance 欄位在底層都會生成對應的 getter（和非 final 的會生成 setter）。`late final` 更特殊——它生成的 getter 包含「是否已初始化」的檢查邏輯，setter 包含「只能寫入一次」的 guard。

當子類用另一個欄位覆蓋時，記憶體中會有兩個獨立的儲存槽：

| 存取來源                   | 讀到的 slot             |
| -------------------------- | ----------------------- |
| 子類自己的程式碼           | 子類的 slot（已初始化） |
| 父類的程式碼（繼承的方法） | 父類的 slot（未初始化） |

父類的 `init()` 或其他方法如果存取 `packageInfo`，會讀到父類那份未初始化的 slot，拋出 `LateInitializationError`。這就是為什麼 Dart 不允許用欄位覆蓋欄位。

## 修法：改用 getter 覆寫

```dart
@override
PackageInfo get packageInfo => PackageInfo(
  appName: 'UniPos Test',
  packageName: 'com.mxkj.unipos.test',
  version: '1.0.0',
  buildNumber: '1',
  buildSignature: 'test',
  installerStore: null,
);
```

Getter 覆寫只有一個讀取入口——不管父類還是子類的程式碼呼叫 `packageInfo`，都走子類的 getter。不會有兩份 slot 的問題。

## 通則

Dart 中覆寫父類的欄位，一律用 getter（必要時加 setter），不要用欄位。這不只適用於 `late final`——所有欄位覆蓋都有同樣的雙 slot 風險，只是 `late final` 的症狀最明顯（直接拋 `LateInitializationError`），普通欄位的症狀更隱蔽（值不同步）。
