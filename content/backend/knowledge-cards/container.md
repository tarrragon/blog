---
title: "Container"
tags: ["容器", "Container"]
date: 2026-04-23
description: "說明容器如何包裝服務、隔離依賴與影響部署方式"
weight: 129
---

Container 的核心概念是「把應用程式與執行環境封裝成可交付單位」。它通常承載 application binary、runtime 依賴、config 與啟動命令。 可先對照 [Resource Limit](/backend/knowledge-cards/resource-limit/)。

## 跟其他概念的關係

Container 位在 build、deploy、runtime 與 platform 之間，是服務交付與資源限制的基本單位。 可先對照 [Resource Limit](/backend/knowledge-cards/resource-limit/)。

## 可觀察訊號

系統需要 container 化的訊號是服務需要一致的啟動方式、相同的 runtime 環境、可複製的部署流程，或多個 instance 要共用同一套交付模型。

## 接近真實網路服務的例子

當服務要被放進 Kubernetes、CI pipeline 或 VM 上的標準化部署流程時，container 可以把 binary、system dependency 與啟動參數打包成固定形狀，降低環境差異。

## 判斷條件與後果

Container 讓服務的交付、擴容與回滾一致，前提是 image 內容、啟動命令與環境變數來源都固定下來；其中任一項依啟動的環境而變時，同一個 image 在不同環境的行為就不同，回滾到同一個 image 也不保證回到同一個行為。image 內容由 Dockerfile 決定（指令與 layer 怎麼組見 [Dockerfile 設計](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)）；tag 沒有凍結時，同一個 tag 在不同時間指向不同的內容，凍結的方式見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)。沒有 [resource limit](/backend/knowledge-cards/resource-limit/) 時，一個 container 可以用掉主機的全部記憶體，同一台主機上的其他 container 跟著受影響。一個系統該切成幾個 container（一服務一個、還是全塞一個）見 [一容器一職責](/backend/knowledge-cards/container-per-service/)。
