---
title: "不可變 Image"
date: 2026-07-06
description: "想「修改 / 升級一個已經 build 好的 image」、或搞不懂為什麼同一個 tag 隔天內容變了時回來讀 — image 是不可變的 build 產物、改了就是新 image"
weight: 131
tags: ["backend", "deployment", "docker", "container", "knowledge-cards"]
---

不可變 image 是「一個 build 出來的 image 內容固定、無法就地修改」的性質。你不會「改一個 image」——你改 [Dockerfile](/backend/05-deployment-platform/vendors/docker/dockerfile-design/) 再 build，得到的是一個**全新的 image、新的身分**。這個性質是 [container](/backend/knowledge-cards/container/) 化能提供可重現、可回滾、可稽核的根本原因，也解釋了一個最常見的誤解：「怎麼升級這個 image」這個動作根本不存在。

## 概念位置

不可變 image 位在 [Dockerfile](/backend/05-deployment-platform/vendors/docker/dockerfile-design/)（定義）與 [container](/backend/knowledge-cards/container/)（執行實例）之間：image 是 build 這個動作的凍結輸出。Dockerfile 是可變的原始碼、container 是可讀寫的執行實例，中間的 image 是不可變的交付單位——它的身分由內容的雜湊（digest）決定，內容一變、digest 就是另一個 image。

## tag 是可變指標，digest 是不可變身分

同一個 image 有兩種指涉方式，一個會動、一個不會：

- **tag**（`app:1.0`、`php:8.2`）是**可變的指標**：可以重新指到不同的 image，所以「同一個 tag 隔天內容不同」是正常的（浮動 tag 就是這樣，見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)）。
- **digest**（`@sha256:...`）是**不可變的身分**：它就是內容的雜湊，指向 digest 一定拿到同一個 image。要真正釘死一個 image，用 digest。

## 可觀察訊號

當你想「進去改一個已 build 的 image」時，就是這個性質在提醒你方向錯了——正確做法是改 Dockerfile 重 build。相對地，`docker exec` 進一個**執行中的 container** 改東西是可以的，但那些改動活在 container 的可寫層、不寫回 image；container 一重建就沒了。「改 container 有效、改 image 無效」正是可變 / 不可變的邊界。

## 設計責任

不可變帶來三個能用的性質：**可重現**（同一個 image 到哪都一樣）、**可回滾**（把 tag 指回舊 image 就退版，舊 image 一直在）、**可稽核**（digest 唯一對應一份內容，能證明線上跑的到底是哪一版）。代價是「要改就得重 build」——不能熱修一個 image。所以升級的正確形態是**建新的、標清楚、留舊的定義**，見 [image 版本管理與升級](/backend/05-deployment-platform/vendors/docker/image-versioning-upgrade/)。
