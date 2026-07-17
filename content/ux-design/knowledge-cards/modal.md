---
title: "Modal（模態）"
date: 2026-07-16
description: "UI 元素阻斷背景互動、要求使用者回應後才能繼續 — 區分 Dialog 與 non-modal Bottom Sheet 的關鍵行為屬性"
weight: 7
slug: "modal"
tags: ["ux-design", "knowledge-card", "modal", "dialog", "interaction"]
---

Modal 的核心概念是「UI 元素阻斷背景互動，使用者必須回應（選擇、確認或 dismiss）後才能繼續操作其他內容」。半透明遮罩覆蓋背景、點擊遮罩或按鈕才能關閉 — 這些視覺特徵都服務同一個行為屬性：強制使用者的注意力停留在當前元素上。它是 UI 層的阻斷，與 [Gate](/ux-design/knowledge-cards/gate/) 的流程層阻斷分屬兩個層次。

## 概念位置

Modal 是跨元件的行為屬性，不是特定元件。Dialog 永遠是 modal — 它的設計目的就是阻斷流程、強制回應。Bottom Sheet 可以是 modal（有遮罩、阻斷背景）也可以是 non-modal（與背景內容並存、使用者可切換注意力）。Banner 和 SnackBar 永遠是 non-modal — 它們出現時使用者仍可操作其他功能。這個區分決定了通知形式的干擾程度（[通知模式選擇](/ux-design/06-interaction-feedback/notification-pattern-selection/)的二軸判準之一）。

和 [Gate](/ux-design/knowledge-cards/gate/) 互補：Gate 管流程層的阻斷（使用者必須通過關卡才能進入某個功能），Modal 管 UI 層的阻斷（使用者必須回應當前元素才能操作其他 UI）。Gate 失敗時的 fallback 設計可能用 modal Dialog 呈現（「認證失敗，請重試或返回」），兩者在這裡交會。

## 可觀察訊號與例子

需要 modal 的訊號是「使用者如果忽略這個通知或選項，會產生不可逆後果或遺漏關鍵資訊」。刪除確認、付款確認、匯出結果含檔案路徑 — 這些情境的共通點是「跳過等於錯過」。反過來，如果使用者忽略通知也不影響後續操作（「已複製到剪貼簿」），用 modal 就是過度干擾。

## 設計責任

Modal 元素的設計責任是確保阻斷有正當理由、且使用者能明確退出。每個 modal 至少提供一條退出路徑（關閉按鈕、取消操作、點擊遮罩 dismiss）。Dialog 之上再彈 Dialog 是 modal 堆疊的典型反模式 — 使用者的注意力分裂、dismiss 順序混亂。如果業務流程需要連續 modal 確認，改為多步驟的單一 Dialog 或全螢幕流程。
