---
title: "Image Digest"
date: 2026-05-21
description: "說明 container image digest 如何作為不可變產物身分，支撐掃描、推進與 runtime 追溯"
tags: ["CD", "container", "image", "digest", "knowledge-card"]
weight: 19
---

Image Digest 的核心概念是「用內容雜湊識別不可變 image」。它補足 [Container Registry](/ci/knowledge-cards/container-registry/) 的命名治理，讓 [Artifact Handoff](/ci/knowledge-cards/artifact-handoff/) 可以鎖定精準產物。

## 概念位置

Image Digest 位在 image build、scan、registry promotion 與 runtime deploy 之間，通常以 `sha256:...` 形式標識 image manifest 或 image index。

## 可觀察訊號

- `latest` 或 mutable tag 造成 staging 與 production 內容分叉。
- production runtime 需要反查實際跑的 image。
- 掃描結果需要和部署內容精準對齊。

## 接近真實服務的例子

CI build image 後推到 registry，scan 報告綁定 digest。Kubernetes manifest 在 production 使用同一個 digest，事故時可從 running pod 反查 workflow run 與 source commit。

## 設計責任

Image Digest 要納入 deployment manifest、scan report、release note 與 rollback 記錄，讓 image 發布具備可追溯與可審計能力。
