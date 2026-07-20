---
title: "EventBus"
tags: ["event-bus", "domain-event", "pub-sub"]
date: 2026-07-20
description: "在同一個行程內把「發生了一件事」廣播給多個訂閱者、且要判斷該不該拿它兼職變更通知管道時使用。EventBus 是行程內的發布／訂閱事件匯流排——把事件的發布點與訂閱點解耦。"
weight: 20
---

需要在同一個行程內把「發生了一件事」廣播給多個訂閱者時，用的是 EventBus——行程內的發布／訂閱事件匯流排。發布端呼叫 publish、不需要知道誰在聽；訂閱端註冊監聽器、不需要知道是誰發的。這個解耦讓 [domain event](/ddd/knowledge-cards/domain-event/) 的發布點跟消費點可以獨立增減，不必逐一牽線。

## 概念位置

EventBus 是 [domain event](/ddd/knowledge-cards/domain-event/) 的傳輸機制、不是事件本身：event 是「發生了什麼」的事實記錄，EventBus 是讓這個事實從發布端跑到訂閱端的管道。EventBus 只解決「怎麼送達」，送達之後訂閱端該把事件當事實通知還是當變更信號來用，是另一個判準，見 [domain event 與狀態流](/ddd/domain-event-vs-state-stream/)。

## 可觀察訊號

訂閱端掛上「監聽全部事件、任何事件進來就重新查詢」這種全事件過濾器，是把 EventBus 兼職成變更通知管道的訊號——這條路徑上線初期有效，但涵蓋面等於「有沒有人記得發事件」，跟寫入操作的集合不天然相等，多個視圖各自解「怎麼知道資料變了」時容易補出交叉且不完整的補償策略。

## 設計責任

EventBus 只承擔「發布／訂閱」這一層機制、不承擔涵蓋保證——涵蓋是靠每個寫入路徑記得呼叫 publish 撐起來的，EventBus 本身不驗證有沒有漏發。需要涵蓋面天然等於寫入操作集合的場景，正確載體是 [observation outlet](/ddd/knowledge-cards/observation-outlet/) 的狀態流、不是把 EventBus 的監聽範圍擴大，完整案例見 [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)。
