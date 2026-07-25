---
title: "Docker Named Volume Ownership（掛載點擁有者）"
date: 2026-07-08
description: "container 內非 root 使用者寫不進掛載的 named volume、出現 permission denied 時回來讀"
weight: 51
tags: ["linux", "container", "docker", "knowledge-cards"]
---

一個空的 Docker named volume 首次掛載時，它的 owner 由 image 內對應路徑的狀態決定：image 裡該路徑**已存在**時，Docker 用那個路徑的 owner 與內容初始化 volume；image 裡該路徑**不存在**時，Docker 直接建一個 root 擁有的空 volume 掛上去。這條規則決定了一個常踩的陷阱——要讓 container 內的非 root 使用者寫入掛載的 volume，該路徑必須先在 image 裡以對的 owner 存在。這條規則屬於 image build 期該決定什麼的範疇，跟 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/) 凍結 base image 形狀是同一層次的考量。

## 概念位置

這張卡跟 [機密 runtime 注入](/linux/dotfile/knowledge-cards/runtime-secret-injection/) 是同一類「image build 期決定什麼 vs container runtime 期決定什麼」問題的兩個面向：機密卡管什麼不該烤進 image，這張卡管 image 內路徑的既有狀態如何決定 runtime volume 的初始 owner。image 凍結到多細見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)。

## 空 volume 首次掛載的初始化規則

named volume 跟 bind mount 不同：bind mount 直接把 host 目錄接過去、owner 就是 host 上的；named volume 是 Docker 管理的儲存，第一次掛載且為空時，Docker 會做一次初始化——把 image 內該掛載路徑既有的內容與擁有權「複製」進 volume 當起始狀態。若 image 內根本沒有這個路徑，就沒有 owner 可沿用、Docker 以 root 建立。

## 為什麼非 root 寫不進

image 用非 root 使用者跑（`USER node` 之類）時，若把一個 named volume 掛到一個 image 內不存在的路徑（例如 `/home/node/.claude`），volume 會是 root 擁有的、掛在那裡。container 內的 `node` 對一個 root 擁有、且沒給它寫權限的目錄自然 `Permission denied`。症狀是「掛載點在、但寫進去被拒」，`ls -ld` 一看 owner 是 root 就對上了。

## 修法：image 內先建好並 chown

在 Dockerfile 裡（切到非 root `USER` 之前、還是 root 時）先把該路徑建好並改成目標使用者：

```dockerfile
RUN mkdir -p /home/node/.claude && chown -R node:node /home/node/.claude
USER node
```

這樣 image 內該路徑已存在且屬 `node`，空 named volume 首次掛載時就沿用這個 owner、`node` 寫得進去。這是「掛載點要先在 image 裡以對的 owner 存在」的通用作法，對任何要讓非 root 使用者寫入的 named volume 都適用。

## 判讀訊號 / 邊界

- container 內非 root 使用者對掛載路徑 `Permission denied` → 先 `ls -ld` 看 owner 是不是 root，是就往這條查。
- 只發生在 **named volume 且首次掛載為空**。bind mount 走 host owner、不適用此規則；volume 若已有內容（先前初始化過），後續掛載不會再改 owner——所以改了 Dockerfile 要記得砍掉舊的 root-owned volume 重建才生效。
- host / container 的 UID 對映另是一回事：即使 owner 對，host 與 container 的 UID 數字要一致，掛進來的檔在兩側才是同一個 owner（image tag 與可重現性見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)）。
