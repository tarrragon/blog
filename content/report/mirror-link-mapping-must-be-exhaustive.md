---
title: "跨 surface 鏡像的連結轉換 mapping 要窮盡、不能靠猜"
date: 2026-06-26
weight: 196
description: "skill 鏡像從 .claude/skills/ 複製到 content/skills/ 時，references/principles/ 的相對連結要轉成 /report/ 的真實路徑。mapping table 不完整會讓 CI 反覆 broken link，每次修一批漏一批。窮盡 mapping 的方法是列出所有 principle 檔案再逐一找對應 report 卡，不是靠 slug 精確匹配碰運氣。"
tags: ["report", "事後檢討", "工程方法論", "原則", "工具鏈"]
---

## 論述基礎與限制

本卡抽自 compositional-writing skill 鏡像同步的連續三次 CI 失敗。每次都是 `mdtools cards` 報 broken link、每次都修幾個 mapping、每次都以為修完了、下次 push 又報新的。限制：evidence 來自單一 skill 的鏡像同步。

## 核心原則

跨 surface 鏡像（`.claude/skills/` → `content/skills/`）的連結轉換有一個結構性約束：原始檔用相對連結（`references/principles/xxx.md`，portable 設計），鏡像檔要用真實路徑（`/report/slug/`，blog 內連結）。兩者的 slug 不一定一致——principle 卡的檔名是 skill 內部命名，report 卡的檔名是 blog 內部命名，兩者獨立演化。

mapping 不完整時的失敗模式是**每次修一批漏一批**：第一次靠 slug 精確匹配轉了 20 個、漏了 5 個不匹配的；第二次手動補了 3 個已知的 mismatch、漏了 2 個不知道對應哪張 report 的；第三次才把最後 2 個找到。三次 CI 失敗、三次 commit、三次 push。

## 情境

compositional-writing 的 SKILL.md 有約 25 個 `references/principles/xxx.md` 連結。鏡像同步時：

- 第一輪：slug 精確匹配轉了 ~20 個，剩 5 個報 broken
- 修了 3 個已知的 slug mismatch（teaching-prose → teaching-register、cross-expertise-scenario → cross-expertise-communication 等）
- CI 仍報 3 個 broken：decorative-symbols-keyword-bank、risk-asymmetric-audit-standard
- 錯誤判斷「沒有對應 report 卡」→ 改成純文字
- 使用者指出「一定有對應的 report 卡，找的方式有問題」
- 重新用 rg 搜索 report 內容而非 slug 匹配，找到：decorative-symbols → visual-tool-error-layer-alignment、risk-asymmetric → security-teaching-rigor-asymmetry

根因是 mapping 的搜尋策略——只用 slug 精確匹配和少量已知 mismatch，沒有窮盡所有 principle 檔案。

## 理想做法

建立 mapping 時用窮盡策略，不靠碰運氣：

1. 列出所有 principle 檔案：`ls .claude/skills/<name>/references/principles/*.md`
2. 對每個 principle，讀它的標題和「來源」段，找出它從哪張 report 卡抽出
3. 用 report 卡的內容搜尋（`rg "關鍵詞" content/report/`）而非 slug 匹配
4. 把完整 mapping 寫進腳本的 case 語句

mapping 的維護：每次新增 principle 卡時，同步在腳本裡加一行 case。

自動化輔助：腳本跑完後如果有 WARN（unresolved），不要直接 commit——先確認這些 unresolved 是真的沒有 report 卡、還是 mapping 漏了。「沒有對應 report 卡」是需要證明的結論、不是搜尋失敗的預設。

## 沒這樣做的麻煩

- **三次 CI 失敗**：每次以為修完、push 後又報新的 broken link，因為每次只修當前報錯的、沒有窮盡檢查全部 mapping
- **錯誤結論「沒有 report 卡」**：slug 不匹配被誤判為「不存在」，實際是搜尋方式太窄（只靠檔名比對）。差點把有效連結改成純文字、損失 blog 內的導航
- **修法引入新問題**：改成純文字後 mdtools cards 不報錯了，但讀者在 blog 上看到的是不可點擊的文字、失去了導航功能

## 判讀徵兆

腳本輸出 WARN 時，問自己：「我用了什麼搜尋策略？只用 slug 比對、還是也搜了 report 卡的內容和標題？」如果只用 slug 比對，WARN 可能是 false negative（有對應卡但 slug 不同）。

## 跟其他抽象層原則的關係

- → [跨 surface 同主題內容要重新語境化、不是搬運](/report/cross-surface-recontextualize-not-transplant/)：鏡像連結轉換是跨 surface 語境化的一部分——portable skill 用相對連結、blog 用真實路徑、兩者的連結策略不同
- → [操作指引要帶環境專屬工具路徑](/report/operational-how-needs-environment-specific-tooling/)：同一個「搜尋 mapping」動作在不同條件下（slug 匹配 vs 內容搜尋）的工具路徑不同，跟操作步驟缺工具指引是同構問題
