---
title: "Container"
date: 2026-04-23
description: "說明容器如何包裝服務、隔離依賴與影響部署方式"
weight: 128
---

Container 的核心概念是「把應用程式與執行環境封裝成可交付單位」。它通常承載 application binary、runtime 依賴、config 與啟動命令。

## 概念位置

Container 位在 build、deploy、runtime 與 platform 之間，是服務交付與資源限制的基本單位。

## 可觀察訊號

系統需要 container 化的訊號是服務需要一致的啟動方式、相同的 runtime 環境、可複製的部署流程，或多個 instance 要共用同一套交付模型。

## 接近真實網路服務的例子

當服務要被放進 Kubernetes、CI pipeline 或 VM 上的標準化部署流程時，container 可以把 binary、system dependency 與啟動參數打包成固定形狀，降低環境差異。

## 設計責任

設計時要定義 image 內容、啟動命令、[resource limit](resource-limit/) 與環境變數來源。Container 本身不是目的，而是讓服務交付、擴容與回滾更一致的手段。

## 英文術語對照
- Container
- Application container
