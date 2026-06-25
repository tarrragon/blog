---
title: "新增欄位忘記同步 reset — 跨測試狀態洩漏的系統性根因"
date: 2026-06-25
draft: false
description: "多個開發者（或 AI agent）各自在 class 中新增 private 欄位，但都沒更新 reset 方法。導致跨 test case 狀態洩漏，測試結果取決於執行順序。根因是「新增欄位時同步所有生命週期路徑」這個隱含契約沒有被顯性化。"
tags: ["testing", "state-management", "design-pattern", "ai-agent", "retrospective"]
---

## 事件

JS SDK 的 Monitor class 在一輪並行開發中，三個開發者各自新增了 private 欄位：`flushing`（flush 併發 guard）、`retryCount`（重試計數）、`lastHeartbeat`（心跳時間戳）。三個欄位各自在功能邏輯中被正確使用，但都沒有加進 `__reset()` 方法。

測試框架在每個 test case 之間呼叫 `__reset()` 清理狀態。因為 `retryCount` 沒被重置，第一個 test case 把 retryCount 遞增到 1，第二個 test case 繼承了這個值，retry 邏輯提前觸發，測試失敗。

失敗的測試看起來像是 retry 邏輯有 bug，但實際上 retry 邏輯完全正確——問題出在測試隔離。

## 根因：隱含契約沒有顯性化

Class 的每個 private 欄位都有一個隱含契約：「所有生命週期路徑都知道你的存在。」這包括初始化（constructor / init）、重置（reset / dispose）、序列化（toJSON，如適用）。

新增欄位時，開發者通常會先在功能邏輯中使用這個欄位——因為那是他加欄位的目的。但「同步到 reset」不是功能邏輯的一部分，它是一個跨切面的維護動作。遺漏的機率隨欄位數和開發者數增加而上升。

多人（或多 AI agent）並行開發時問題更嚴重——每個人只看自己加的欄位，沒有人有動機去檢查 reset 的完整性。

## 防護：State Registry Pattern

將所有 private 欄位的初始值集中宣告一次：

```typescript
function initialState() {
  return {
    config: null,
    buffer: [],
    flushing: false,
    retryCount: 0,
    lastHeartbeat: 0,
    // 新增欄位加在這裡——init 和 reset 自動包含
  };
}
```

reset 改用 `Object.assign(this, initialState())`。新增欄位只改一處，init 和 reset 自動同步。

配合一個 reset 完整性測試：reset 後 snapshot 比對 initialState 的所有 key——新增欄位但忘記加到 initialState 會因型別或 key 不一致而紅燈。

## 適用場景

任何有「重置到初始狀態」需求的 class：測試框架的 setUp/tearDown、物件池的回收、singleton 的 reinit。問題不在語言（TypeScript、Go、Dart 都會遇到），而在「新增欄位」和「同步 reset」是兩個分開的動作——只要是分開的，就有遺漏的可能。State Registry 把兩者合併成一個動作。
