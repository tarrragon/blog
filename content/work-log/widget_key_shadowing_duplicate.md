---
title: "Widget 子類重新宣告 key — 遮蔽父類屬性與 duplicate key 風險"
date: 2026-06-30
draft: false
description: "在 StatelessWidget 子類中重新宣告 final Key? key，會遮蔽 Widget 繼承的 key 屬性，產生兩份儲存槽。若再把同一個 key 往下傳給 child widget，同一棵子樹出現重複 key，rebuild 時 Flutter 可能拋錯。"
tags: ["flutter", "widget", "key", "dart", "inheritance"]
---

## 事件

測試用的 `TestRiveAnimation extends StatelessWidget` 裡宣告了 `final Key? key;`，constructor 中透過 `super(key: key)` 傳給父類。Dart analyzer 警告 `key` overrides an inherited member。

加了 `@override` 可以消除警告，但問題沒有解決——class 裡現在有兩個 `key` slot（子類自己的和 `Widget` 繼承的），而 `build` 方法裡又寫了 `Container(key: key)`，把同一個 key 同時掛在 parent widget 和 child widget 上。

## 根因

`Widget` 的 `key` 是 `final` 屬性，由 constructor 的 `super(key:)` 設定。子類重新宣告同名欄位會產生 shadowing：

- 子類的程式碼（包括 `build`）讀到的是子類自己的那份 `key`
- 父類 `Widget` 的框架程式碼讀到的是父類的那份 `key`

兩份值相同（因為 constructor 都有寫入），但語意上是兩個獨立的 slot。更危險的是，如果在 `build` 裡把 `key` 往下傳給 child，同一棵 widget 子樹會出現兩個相同的 `Key` 值，Flutter 在 diff 時可能拋出 duplicate key 錯誤。

## 修法

不要重新宣告 `key`，改用 `super.key`：

```dart
const TestRiveAnimation.asset(
  this.asset, {
  super.key,           // 直接傳給 Widget，不產生新 slot
  this.useArtboardSize = false,
});
```

`build` 裡也不要把 widget 自身的 key 再傳給 child——key 是給 framework 用來識別這個 widget 的，不該手動轉發。

## 判斷原則

在 Flutter 中，`key`、`hashCode`、`runtimeType` 這類從 `Widget` / `Object` 繼承的屬性，子類永遠不該用欄位覆蓋。如果需要自訂行為，覆寫 getter。
