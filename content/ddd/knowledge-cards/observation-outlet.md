---
title: "Observation Outlet（觀測出口）"
tags: ["observation-outlet", "repository", "reactive", "ddd"]
date: 2026-07-16
description: "repository 只有 pull 介面、衍生視圖靠補償刷新，考慮補「資料變了」的推送能力時使用。觀測出口是 pull 介面的 push 對應——能力橫跨三層、歸屬由各層的表達語言決定。"
weight: 17
---

觀測出口是 repository 對外提供的「資料變了」持續通知能力——pull 介面（`getAllBooks()` 回 `Future`）的 push 對應（`watchBooks()` 回 `Stream`）。它的載體是 [狀態流](/ddd/knowledge-cards/state-stream/)：通知的內容是資料當前值、不是業務事實。能力橫跨三層——契約（介面宣告）、機制（變更偵測）、組裝（框架訂閱），每一層的歸屬由該層產出的表達語言決定。

## 概念位置

觀測出口的契約層是一種 [port](/ddd/knowledge-cards/port/)：簽名只用語言標準庫與 domain entity、放 domain repository 介面，與 pull 方法形成對稱。機制層（broadcast controller、寫入點 emit）歸 [adapter](/ddd/knowledge-cards/adapter/)；組裝層（框架 provider 包裝）歸 DI／presentation。三層歸屬的完整判準與「需求來源不決定歸屬」的推導見 [觀測出口的職責三分](/ddd/observation-outlet-responsibility-split/)。

## 可觀察訊號

repository 缺觀測出口時，每個衍生視圖各自解「怎麼知道資料變了」：導航返回點補 reload、EventBus 橋接刷新、多個視圖各自維護 load 時機。補償策略的交叉與涵蓋缺口是這個能力該補的訊號。

## 設計責任

觀測出口讓「資料變更」成為可訂閱的一級節點，涵蓋面等於寫入操作的集合——emit 掛在寫入方法尾端、新路徑自動涵蓋。它通知「現在是什麼」、不記錄「發生了什麼」——後者是 [domain event](/ddd/knowledge-cards/domain-event/) 的責任，兩者正交。落地的實作點（broadcast、初始值、dispose）見 [StreamProvider 包 repository watch stream](/work-log/flutter_streamprovider_wraps_repository_watch/)。
