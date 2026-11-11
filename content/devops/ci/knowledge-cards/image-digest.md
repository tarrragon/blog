---
title: "Image Digest"
date: 2026-05-21
description: "說明 container image digest 如何作為不可變產物身分，支撐掃描、推進與 runtime 追溯"
tags: ["CD", "container", "image", "digest", "knowledge-card"]
weight: 19
aliases: ["/ci/knowledge-cards/image-digest/"]
---

Image Digest 的核心概念是「用內容雜湊識別不可變 image」。它補足 [Container Registry](/devops/ci/knowledge-cards/container-registry/) 的命名治理，讓 [Artifact Handoff](/devops/ci/knowledge-cards/artifact-handoff/) 可以鎖定精準產物。

## 跟其他概念的關係

Image Digest 位在 image build、scan、[registry](/devops/ci/knowledge-cards/container-registry/) promotion 與 runtime deploy 之間，通常以 `sha256:...` 形式標識 image manifest 或 image index。

## 可觀察訊號

- `latest` 或 mutable tag 造成 staging 與 production 內容分叉。
- production runtime 需要反查實際跑的 image。
- 掃描結果需要和部署內容精準對齊。

## 接近真實服務的例子

CI build image 後推到 registry，scan 報告綁定 digest。Kubernetes manifest 在 production 使用同一個 digest，事故時可從 running pod 反查 workflow run 與 source commit。

## 判斷條件與後果

Image Digest 只在部署鏈的每一份紀錄都用它指涉 image 時，才讓這些紀錄對到同一個產物，原因是 tag 是可以改指向的名字，digest 是內容的雜湊，內容一變它就跟著變。deployment manifest 用 mutable tag 時，同一個 tag 在 staging 與 production 可以指向不同內容，production 實際跑的 image 無法從 manifest 反查；scan report 綁的是 tag 時，掃描過的那一份跟後來部署的那一份可能已經不同；release note 與 rollback 記錄只寫 tag 時，回退到的「上一版」取決於那個 tag 現在指向什麼。
