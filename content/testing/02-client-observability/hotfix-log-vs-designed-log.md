---
title: "「事後補 log」vs「設計產物 log」的品質差異"
date: 2026-06-19
description: "事後補的 log 是救火工具、設計產物的 log 是可觀測性基礎設施 — 從 app_tunnel 的 W2 hotfix log 拆解兩者在格式、覆蓋率、維護成本上的差異"
weight: 4
tags: ["testing", "observability", "logging", "design", "quality"]
---

事後補 log 和設計產物 log 的差別在於產出時機和品質標準。事後補的 log 在 debug 壓力下產出，目的是「讓這次的問題能被定位」；設計產物的 log 在功能規格階段產出，目的是「讓未來任何問題都能被定位」。兩者的品質差異在格式統一性、覆蓋完整性和長期維護成本三個面向上表現明顯。

## 格式統一性

app_tunnel 在 W2 修復時補的 `developer.log` 格式不統一（[T.C4](/testing/cases/client-log-absent-debug-cost/)）。不同元件由不同時間點、不同 debug 需求補上的 log，各自有各自的風格：

有的帶 `name:` 參數讓 log 可以按元件過濾：

```dart
developer.log('WS connected', name: 'ConnectionManager');
```

有的不帶，混在全域 log 裡無法過濾：

```dart
developer.log('auth token sent');
```

有的帶 `// i18n-exempt` 標記（因為 linter 會對 hardcoded string 報警），有的忘了加。有的把錯誤訊息放在 `error:` 參數，有的用字串串接。

這些不一致來自事後補 log 的結構性原因：每條 log 是在解決當下問題時加的，沒有統一規範，也沒有 review。加完能定位問題就提交，下次遇到新問題再加新的 log — 格式隨機。

設計產物 log 在產出前就有命名規則和格式規範（見 [功能規格中的 log 點定義方法](/testing/02-client-observability/log-point-in-spec/)）。所有 log 點走同一個 `AppLogger` 介面，name、level、結構化欄位在規格階段就定義好，實作時照規格寫。

## 覆蓋完整性

事後補 log 的覆蓋範圍由「哪些問題已經發生過」決定。W2-002 auth token 問題觸發了 `ConnectionManager` 和 `TerminalScreen` 的 log 補充，但 `TtydProtocol`、`BiometricService`、`CredentialRepository`、`EnrollmentScreen` 四個元件仍然零 log — 因為這四個元件在 W2 的 debug 過程中不是瓶頸。

六個核心元件中四個零 log 的狀態意味著：下次如果問題出在 `BiometricService`（例如特定 iOS 版本的 biometric API 行為改變），debug 又會回到「手動加 log → 重新編譯 → 插拔裝置」的循環。事後補 log 只覆蓋已知問題的路徑，對未知問題沒有防護。

設計產物 log 的覆蓋範圍由功能流程的步驟數決定。每個功能規格列出所有步驟的 log 點，不管這些步驟是否曾經出過問題。`BiometricService.authenticate()` 在規格中就有 start/done/failed 三個 log 點，無論是否遇過 biometric 問題。

## 維護成本

事後補 log 隨 debug 過程累積，沒有統一管理。隨時間推移：

- 某些 log 的觸發條件已經不存在了（被修復的 bug 對應的 log），但沒人清理
- 某些 log 的格式和新加的 log 不一致，但沒人統一
- 某些 log 的 context 資訊不足（當時能定位問題是因為開發者記得 context，半年後換人接手就不夠了）
- 某些 log 在 release build 中不該出現但忘了加條件

設計產物 log 有規格文件作為 source of truth。功能變更時更新規格中的 log 點列表，刪除的步驟對應的 log 點一起刪除，新增的步驟對應的 log 點一起新增。Log 的生命週期和功能的生命週期綁定。

## 從事後補過渡到設計產物

已有的事後補 log 不需要全部重寫。過渡策略是：

**統一入口**：建立 `AppLogger` 封裝，把現有的 `developer.log` 呼叫改為走 `AppLogger`。這一步不改 log 內容，只改呼叫方式，讓後續的格式統一和功能切換有統一入口。

**補規格**：對每個功能寫出 log 點規格表（四類 log 點），比對現有 log 和規格的差距。規格中有但程式碼中沒有的 log 點 = 覆蓋缺口，補上。程式碼中有但規格中沒有的 log 點 = 可能是過時的 debug log，評估是否刪除。

**新功能走設計產物流程**：從下一個新功能開始，功能規格中包含可觀測性欄位。新功能的 log 從一開始就是設計產物品質。

## 下一步路由

- log 點規格的定義方法 → [功能規格中的 log 點定義方法](/testing/02-client-observability/log-point-in-spec/)
- 三層 log 的職責劃分 → [三層 log 設計](/testing/02-client-observability/three-layer-log-design/)
- Log 收集方案選擇 → [自架 log endpoint vs 商業方案](/testing/02-client-observability/log-endpoint-tradeoff/)
