---
title: "git credential helper"
date: 2026-07-09
description: "要弄懂 git 怎麼不手打帳密就取得 HTTPS 認證、gh auth login 自動設定跟手動指到某程式是不是同一機制、或 clone/push 卡認證時回來讀"
weight: 50
tags: ["linux", "git", "auth", "knowledge-cards"]
---

git credential helper 是一個 git 用來取得 HTTPS 認證的**可替換外部程式**：git 自己不儲存也不硬編任何帳密，每次要對遠端認證時把要求交給設定好的 helper、由它回傳使用者名與密碼。這讓「認證從哪來、存在哪」跟 git 本身解耦——換一個 helper 就換一套憑證來源，git 的其餘行為不動。理解這一點，就看得出「`gh auth login` 幫你設好」跟「手動把 helper 指到某個程式」是同一個機制的兩種配置，而不是兩件不相關的事。

## 機制：git 把認證外包給一個程式

git 對 HTTPS 遠端操作（clone / fetch / push）需要憑證時，不自己去記，而是走一個標準協定呼叫 helper：git 把 `protocol=https`、`host=github.com` 這些欄位從 stdin 餵給 helper，helper 把 `username=...`、`password=...` 從 stdout 回傳，git 拿去組認證。整個過程不需要人打字，也不把憑證留在 git 的設定裡。

## helper 是可替換的：換 helper 就換憑證後端

`credential.helper` 設定值決定用哪個 helper，每個對應一種憑證儲存後端：

- `cache` 存在記憶體、限時；`store` 明文存 `~/.git-credentials`（方便但不安全）。
- 平台鑰匙圈：macOS 的 `osxkeychain`、Windows 的 `manager`。
- `!<command>`：驚嘆號開頭表示「把後面當 shell 命令執行」，可指到任意程式。例如 `!gh auth git-credential` 把認證外包給 GitHub CLI、由它現讀 `GH_TOKEN` 環境變數回傳。

因為 helper 可替換，同一個「git 怎麼拿到 GitHub 憑證」的問題可以用不同後端解：互動式 `gh auth login` 會自動幫你把 helper 設成 gh、憑證存進 gh 的登入檔；容器化無人值守則手動設 `!gh auth git-credential` 配注入的 `GH_TOKEN`，讓憑證每次現讀環境變數、不落任何檔（機密怎麼注入見 [機密 runtime 注入](/linux/dotfile/knowledge-cards/runtime-secret-injection/)）。兩者設定形式不同，但都是「配置 credential helper」這一件事。

## 為什麼認證不落在 git 本身

git 的設定檔（`.gitconfig`）只存「用哪個 helper」這個指標、不存憑證本身。這條分工讓憑證的儲存策略獨立於 git：要更安全就指到鑰匙圈或現讀環境變數的 helper、要方便就用 `store`，換策略只改一行 `credential.helper`、不動 git 的其他設定，也不會把 token 硬編進版控的檔案。HTTPS + token 走 credential helper，跟 SSH 走金鑰是兩條平行的 git 認證路（SSH 端的金鑰儲放見 [SSH 金鑰儲放與 authorized_keys](/linux/dotfile/knowledge-cards/ssh-key-storage/)）。

## 判讀訊號 / 邊界

- git 對私有 repo 要求輸入帳號密碼、或非互動下回 `could not read Username`，是「沒有 helper 回得出憑證」的訊號——不是網路問題，是認證來源沒設好。
- helper 可以疊：git 依序問每個設定的 helper、第一個回得出憑證的勝出。`gh auth setup-git` 產生的設定會先放一行空 `helper=` 清掉繼承的 helper、再指到 gh，避免別的 helper（如系統鑰匙圈）先攔。乾淨環境沒有繼承 helper 時單行就夠。
- helper 只管 HTTPS 這條路。git submodule 或 remote 走 SSH（`git@github.com:`）時不經 credential helper、走的是 SSH 金鑰那條路。
- helper 回傳的是「當下這次操作」的憑證，不改變遠端的授權範圍——token 本身權限不足（如只有讀權限卻要 push）不是 helper 的問題，helper 已經把 token 正確帶到了。
