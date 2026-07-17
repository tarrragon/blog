---
title: "模組五：導航模式"
date: 2026-06-19
description: "Push/pop stack、GoRouter 命名路由、tab bar、drawer — 導航方法選擇是設計決策"
weight: 5
tags: ["ux-design", "navigation", "router", "flutter", "mobile"]
---

回答「畫面之間怎麼跳」。

## 本模組回應的 UX 盲區

| Finding | 來源                                                     | 內容                                          |
| ------- | -------------------------------------------------------- | --------------------------------------------- |
| UF-10   | [U.C4](/ux-design/cases/missing-enrollment-entry-point/) | go vs push 語意差異影響 UX — 本模組的核心案例 |

## 章節

- [Mobile 導航模式分類](/ux-design/05-navigation-patterns/mobile-navigation-taxonomy/) — Push/pop stack / declarative router / tab bar / drawer 四種模式的適用場景
- [Flutter GoRouter 導航設計](/ux-design/05-navigation-patterns/flutter-gorouter/) — 路由定義、導航 API、redirect 機制和 ShellRoute 的使用場景
- [iOS HIG vs Material Design 導航差異](/ux-design/05-navigation-patterns/ios-vs-material-navigation/) — back 行為、手勢、tab bar 位置、modal 呈現的平台差異
- [Deep link 設計](/ux-design/05-navigation-patterns/deep-link-design/) — URL scheme / Universal Link / App Link，外部來源直接導航到 app 特定畫面
- [go vs push vs pushReplacement 的 UX 語意表](/ux-design/05-navigation-patterns/go-push-semantics/) — 三種導航方法對堆疊、back 行為、使用者心理模型的影響

## 跨分類引用

- ← [ux-design 模組一](/ux-design/01-screen-state-machine/)：狀態矩陣的「退出路徑」欄位決定用 go 還是 push
- → [testing 模組四](/testing/04-ui-automation/)：導航路徑需要 widget test 驗證
