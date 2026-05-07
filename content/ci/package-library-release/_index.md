---
title: "Package / Library Release CI/CD"
date: 2026-05-06
description: "整理 SDK / NPM / PyPI / 套件庫的版本發佈、相容性驗證與供應鏈安全流程"
tags: ["CI", "CD", "package", "library"]
weight: 18
---

Package / Library Release CI/CD 的核心責任是把可重用套件安全發佈到分發平台，並維持版本語意與相容承諾。它和應用部署不同，重點在版本管理、相容邊界、發佈簽章與撤版策略。

## 場域定位

套件發佈常見於 NPM、PyPI、Maven、Crates 等生態。發布後會被多個下游專案依賴，因此每次 release 都是公共契約變更。

| 面向       | Package release 常見責任                    | 判讀訊號                 |
| ---------- | ------------------------------------------- | ------------------------ |
| Build      | package artifact、metadata、lock input      | 產物是否可重現           |
| Validation | API/ABI 相容性、smoke test、publish dry-run | 破壞性變更是否被識別     |
| Versioning | semver、pre-release、changelog              | 版本語意是否與變更一致   |
| Publish    | registry token、scope、provenance           | 發版是否可追溯且權限正確 |
| Recovery   | yank/deprecate/hotfix release               | 事故時是否可快速止損     |

## Release 發布類型分類

「發版」在中文討論裡常被當成單一動作，但實際上有五條互不重疊的通道，每條的觸發條件、產物形式、下游取用方式都不一樣。下游使用者讀 README 時若沒分清楚自己在走哪條通道，很容易踩到「文件寫了安裝指令，但對應通道還沒被建立」的情況。

| 類型             | 產物形式                                | 下游取用方式                       | 典型觸發       | 代表生態                      |
| ---------------- | --------------------------------------- | ---------------------------------- | -------------- | ----------------------------- |
| Source release   | git tag + tarball                       | `git clone` 或 `go install` 後編譯 | tag push       | Go module、許多 OSS 函式庫    |
| Registry publish | 套件清單登錄                            | `npm install` / `pip install` 等   | `publish` 指令 | npm、PyPI、crates.io、Maven   |
| Binary release   | 預編譯多平台執行檔，掛在 GitHub Release | 下載 binary 或 installer script    | tag push       | cargo-dist、goreleaser 工具鏈 |
| Container image  | OCI image                               | `docker pull` / k8s manifest       | tag 或 commit  | Docker Hub、GHCR、ECR         |
| OS package       | `.deb` / `.rpm` / Homebrew formula      | 套件管理器 install                 | 上游同步       | apt、yum、Homebrew、winget    |

這五類常常組合出現（例如同時推 source、registry、binary release）。組合愈多、上游維護成本愈高，但下游能用的入口也愈廣。判讀訊號：

- README 寫的是 `pip install x` → 屬 registry，去 PyPI 確認版本
- README 寫的是 `curl ... /releases/latest/download/...sh | sh` → 屬 binary release + installer，去 GitHub Releases 確認 asset 存在
- README 寫的是 `git clone` 後 `make` → 只走 source，沒任何打包通道
- README 寫的是 `docker pull ghcr.io/...` → 屬 container image，去 registry 確認 tag

## 常見注意事項

- 發版前要明確區分 breaking / feature / fix，避免版本語意錯置。
- 發版流程應固定化（tag 規則、changelog 來源、artifact provenance）。
- 對外 SDK 要維持 contract 測試，避免下游升級破壞。
- 套件來源與 token 權限要最小化，並定期輪替。
- README 安裝段落寫的通道，發版前要實際跑過一次 — 「workflow 寫好」不代表「通道已上線」。

## 安裝路徑分層

Package release 的文件建議同時提供兩條安裝路徑，讓不同風險場景有對應入口。

| 路徑類型   | 目標讀者                     | 流程                                       | 風險控制               |                            |
| ---------- | ---------------------------- | ------------------------------------------ | ---------------------- | -------------------------- |
| 快速路徑   | 本機快速試用、低風險場景     | 一行安裝命令（例如 `curl ...               | sh`）                  | 速度優先，依賴上游發布品質 |
| 可審計路徑 | 生產環境、受管設備、合規場景 | 下載產物 → 驗證 checksum/provenance → 執行 | 可追溯、可驗證、可稽核 |                            |

這個分層能避免單一路徑綁死全部使用者。上游維護者要確保兩條路徑都可用，且文件清楚標示使用時機。可審計路徑的具體範例可直接沿用 [Binary release 與 installer 模式](binary-release-and-installer/) 的最小安全基線。

## 學習路線

| 章節                                                              | 主題                      | 核心責任                                            |
| ----------------------------------------------------------------- | ------------------------- | --------------------------------------------------- |
| [Binary release 與 installer 模式](binary-release-and-installer/) | Tag-driven binary release | GitHub Release + cargo-dist / goreleaser 的發版鏈路 |

## 下一步路由

- 想理解 binary release + installer 模式（curl ... | sh）：讀 [Binary release 與 installer 模式](binary-release-and-installer/)。
- 供應鏈與產物可信度：讀 [Artifact Provenance](/backend/knowledge-cards/artifact-provenance/)。
- 版本契約：讀 [API Contract](/backend/knowledge-cards/api-contract/) 與 [Contract](/backend/knowledge-cards/contract/)。
- 失敗處理：讀 [CI 失敗到修復發布流程](../github-actions-failure-flow/)。
