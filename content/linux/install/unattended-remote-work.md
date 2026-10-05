---
title: "讓機器跑無人值守的長任務"
date: 2026-07-01
description: "要讓一台遠端機器在你不盯著時自己跑完一個長任務或 agent、卻被 sudo 密碼 / 斷線就死 / 推不出結果擋住時讀"
weight: 7
tags: ["dotfile", "linux", "ssh", "automation"]
---

一台機器能被連入、能跑 bootstrap（把它從空機器設定成可用環境的安裝流程）之後，下一個層次是讓它在你不盯著的時候自己跑完一個長任務——一次耗時的編譯、一個批次作業、一個無人值守的 agent。能不能放著走人，取決於有沒有把三件會中斷無人值守執行的事先解決掉：互動提示、斷線即死、結果出不去。這三件是「讓任務能在無人時順利啟動並交付」的障礙；任務跑起來之後的資源耗盡、OOM、額度或憑證到期是另一條軸（執行期的持久性），最後一段會接到那裡。這篇逐一拆解這三個障礙與對應的解法，並說明它們共同的代價判讀——這些便利大多拿安全性換自主性，該不該開要看這台機器的爆炸半徑。

底下用一個具體情境當例子：在一台用完即丟的測試 VM 上，讓 Claude Code 這類 agent 自己跑完一段工作、把成果推回 GitHub 給你早上 review。同一組障礙換成 overnight 編譯或 cron 批次也成立。

## 障礙一：互動提示擋住自動執行

無人值守的程序沒有人在鍵盤前，所以任何「停下來等你輸入」的提示都會讓它卡死，其中最常見的是 sudo 密碼。一個要裝套件、改系統設定的任務，跑到 `sudo` 那行就停在密碼提示、永遠等不到輸入，整個任務卡在那裡直到你回來。

解法是讓這台機器的 sudo 免密碼（NOPASSWD），但這是一個明確的安全取捨、不是預設該開的東西。設定方式是給 sudoers 加一條 NOPASSWD 規則：

```bash
echo "$(whoami) ALL=(ALL:ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/20-nopasswd  # $(whoami) 會填入你的登入帳號
sudo chmod 440 /etc/sudoers.d/20-nopasswd
```

開了 NOPASSWD，等於放棄「sudo 密碼」這道在你被入侵或程序失控時的最後防線。判讀軸是這台機器的爆炸半徑——它持有哪些憑證、能觸及哪些系統，也就是最壞情況下會波及多大範圍。一台範圍受限、沒有任何真實憑證、出事就重建的測試 VM，放棄這道防線換取自動執行是划算的；一台共享主機、生產伺服器、或裝著真實憑證與資料的機器，不該為了方便開 NOPASSWD。關鍵是「可不可丟」不等於「爆炸半徑小」：一台用完即丟的 VM，一旦塞進能碰到生產系統或你帳號的憑證，爆炸半徑就不小了——看的不是機器本身，是它最壞情況能波及什麼。

### 兩種自動化環境的 sudo 設計：GitHub Actions runner 與 Ansible

同一個爆炸半徑的判讀，也解釋了兩種常見的自動化環境為什麼對 sudo 採取相反的設計。GitHub Actions 是 GitHub 的 CI 服務：一份 workflow 檔描述要自動執行的工作，其中每個 job 分派到一台 runner（執行 job 的機器）上跑；runner 可以用 GitHub 提供的（GitHub-hosted runner），也可以用自己架設的機器（self-hosted runner）。Ansible 是設定管理工具：用 playbook（描述要對哪些機器做哪些設定的 YAML 檔）把設定推到遠端機器，每一步由一個 module（執行單一工作的程式，例如安裝套件、改寫設定檔）完成，需要 root 權限的步驟由 become 機制做權限提升，預設透過 sudo。

**GitHub Actions 的 GitHub-hosted runner 預設就是無密碼 sudo。** GitHub 官方文件寫明 Linux 與 macOS 的 runner 以無密碼 sudo 執行，job 裡要裝套件或改系統設定時直接 `sudo` 就行。這個設計成立的前提是執行環境用完即丟：官方的安全強化文件說明 GitHub-hosted runner 在每次都是乾淨、隔離、用完即丟的虛擬機上執行，所以沒有辦法在這個環境裡留下持續性的入侵（見 [Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)）。一個 job 結束，那台虛擬機連同 job 裡做過的任何改動一起消失，sudo 密碼這道防線要保護的「留在機器上的改動」在這裡不存在，所以拿掉它只換到方便。這個環境的爆炸半徑由 job 拿到的權限與資料決定：workflow 注入的 secrets、`GITHUB_TOKEN` 的權限，以及 job 執行的是誰寫的程式碼（例如來自外部 fork 的 pull request）。

**同一份 workflow 搬到自架的 runner 上，這個前提就消失了。** 同一份文件指出 self-hosted runner 沒有「乾淨、用完即丟」的保證，workflow 裡不受信任的程式碼可以在那台機器上留下持續性的入侵，也就是在下一個 job 開始時仍然存在的後門或被改過的檔案。這時在 runner 機器上開全機 NOPASSWD，爆炸半徑就是那台機器本身與它連得到的所有系統。要在自架環境重現 GitHub-hosted runner 的安全前提，做法是讓每個 job 都在新的虛擬機或容器裡跑、跑完就銷毀；只照搬無密碼 sudo 這一項，無密碼 sudo 成立的前提（用完即丟的環境）並沒有跟著搬過來。

**Ansible 這類設定管理工具的條件正好相反：它操作的是長期運作、不會被丟掉的機器。** 所以常見做法是讓目標機器維持需要密碼的 sudo，把密碼交給工具。執行時加 `--ask-become-pass`（縮寫 `-K`）讓人輸入一次 sudo 密碼，或用 `ansible_become_password` 變數從 Ansible Vault（Ansible 內建的檔案加密功能）加密的檔案讀取。後者沒有人在場也能跑，代價是 sudo 密碼以加密形式跟著 playbook 存放，拿得到 Vault 密碼的人或程序就拿得到每台目標機器的 sudo。

另一種常見的限縮是只對特定指令開 NOPASSWD，適合固定腳本呼叫固定指令的自動化：

```bash
# sudoers 規則：帳號 deploy 只能免密碼以 root 執行 /usr/local/bin/restart-app 這一支腳本
# deploy 與腳本路徑是示範用的佔位值，換成自己的帳號與要放行的指令
deploy ALL=(root) NOPASSWD: /usr/local/bin/restart-app
```

這條限縮成立的條件是被放行的指令本身不能讓呼叫者執行任意程式：能開 shell 的編輯器與分頁程式（例如 vim、less 都能在程式裡執行任意指令，以 root 身分開啟時就是一個 root shell）、接受任意參數的指令、一般使用者寫得進去的腳本，放行之後等於放行全部。這種限縮對 Ansible 不適用：[Ansible 官方文件](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_privilege_escalation.html)說明它不一定用固定的指令做事，而是把模組寫成檔名每次都不同的暫存檔再執行，寫死指令路徑的 sudoers 規則對不上。所以 Ansible 需要一個不限指令的權限提升帳號，密碼由 `-K` 在執行時輸入，或由 Ansible Vault 提供。

## 障礙二：SSH 斷線就把任務一起殺掉

直接在 SSH session 裡跑的程序，會隨著 SSH 連線中斷而一起死掉——你闔上筆電、網路斷一下、或單純關掉終端機，正在跑的任務就沒了（連線掛斷送 SIGHUP、預設終止前景程序，機制見 [SIGHUP 與斷線即死](/linux/dotfile/knowledge-cards/sighup-hangup-signal/)）。對一個要跑好幾小時的無人值守任務，這條等於「你不能離開」，跟無人值守的目的矛盾。

把任務搬進終端機多工器（zellij、tmux 這類，配置見 [模組三](/linux/dotfile/03-terminal-ecosystem/multiplexer-tmux-zellij/)）就解決了。多工器的 session 活在那台機器上、獨立於你的 SSH 連線：你在多工器裡啟動任務、然後 detach（卸離），任務繼續在機器上跑，你這頭關掉 SSH 都不影響；之後再連回來 attach（接回）就能看它跑到哪。典型流程是連入機器、起多工器、在裡面啟動任務、detach、走人：

```bash
ssh user@host
zellij                       # 起多工器（tmux 同理）
./run-my-long-task.sh        # 在裡面啟動你的長任務（換成你的實際指令）
# 然後 detach：zellij 預設 Ctrl+o 再按 d（tmux 是 Ctrl+b 再按 d）
# 此時關掉 SSH 不影響任務，它在 host 上繼續跑

# 之後連回來看進度：再 ssh 進去，然後
zellij attach                # tmux 是 tmux attach
```

判讀訊號是「這個任務跑完前，我會不會斷線」。只要會（過夜、跨小時、不穩的網路），就把它放進多工器；幾秒鐘就結束的指令不需要這層。

## 障礙三：成果推不出去，等於沒做

無人值守任務的產出留在那台機器上，你看不到——除非它能把結果送出去。最常見的形式是把改動 commit 後 push 回 git 遠端，你在別處 pull 來看。但 push 需要認證，而一台剛連入的機器通常還沒設好推送的憑證，於是任務做完了、commit 也建了，卻卡在 push 那步推不出去，你隔天連回來才發現結果根本沒送出去。

先在這台機器上設好推送認證，這個障礙就消失。用 GitHub CLI 是直接的一條路，它認證後會一併把 git 的 [credential helper](/linux/dotfile/knowledge-cards/git-credential-helper/)（git 用來自動帶出認證、不必每次手打的機制）設好，後續 `git push` 就能用——但 `gh auth login` 本身是互動式的、要你在場完成一次，屬於離開前的人工前置：

```bash
gh auth login    # 選 HTTPS、完成認證、同意設定 git 認證
```

判讀軸是「這個任務的價值要怎麼回到你手上」。如果你打算從遠端（GitHub）看結果，那 push 認證就是必要前置——沒設好，整段工作就被困在機器裡。連帶的紀律是讓任務頻繁 commit 當檢查點、做完務必確認 push 成功：對一個你不在場的任務，「沒推出去」跟「沒做」對你是一樣的。機器若沒裝 `gh`，也可以用 PAT 走 HTTPS，見 [外部連入篇](../ssh-keyless-bootstrap/) 的私有 repo 段。若這台是容器化的 agent 工作機，還能更進一步繞掉這個人工前置：把 PAT 當 `GH_TOKEN` 在 `docker run` 時注入、git 用 `gh` 的 credential helper 現讀，`gh auth login` 的互動步驟整個省掉，見 [在 container 裡跑 Claude Code](../../tools/remote/claude-code-container-and-hooks/) 的 GitHub 認證段。

把 push 憑證設進這台機器，等於提高了它的爆炸半徑——它現在能動你的 repo 了。這會回頭讓障礙一的 NOPASSWD、以及下面 agent 段的權限放行更該謹慎：最壞情況從「弄壞這台機器」升級成「污染你的 repo」，而後者不是重建一台 VM 就能還原的。所以設了 push 憑證之後，要連帶重估前面那些「因為機器可丟所以放心」的取捨。

## 額外一層：宿主暫停會連帶停掉任務

當這台機器是跑在某個宿主上的虛擬機，還有一個容易忽略的中斷源：宿主睡著，VM 跟著暫停，裡面的無人值守任務也一起停。你以為它整夜在跑，回來發現它從你離開那刻就凍在那裡。判讀方式是想一下「這台機器的存在依賴什麼」——VM 依賴宿主醒著、雲端主機依賴帳單沒欠費。對 VM 的情況，離開前確保宿主不會自動睡眠（macOS 用 `caffeinate`、Linux 宿主用 `systemd-inhibit` 或停用 suspend、Windows 調電源設定，或直接關掉節能的自動睡眠）。

## 如果無人值守的工作者是 AI agent

當你放著跑的是一個 AI agent，除了上面三個障礙，還多一個它自己的互動提示要處理：agent 預設會在每個有風險的動作前停下來問你確認，而無人值守時沒人回答，它就卡住。對應的是 agent 的「跳過確認」模式（如 Claude Code 的權限放行旗標），讓它不停下來問。這跟 NOPASSWD 是同一類取捨、判讀軸也一樣：放給一個無人盯著的 agent 在一台範圍受限、用完即丟的機器上自主動作是可接受的；在一台有真實資料或共享的機器上不該這樣。降低風險的兩個做法是把 agent 的工作範圍用清楚的指引限定（只動哪些目錄、別碰系統其他地方），以及讓它在分支上做、產出交給你 review，而不是直接動到你會依賴的東西。

這一整套（連線層漫遊、session 層存活、容器隔離、憑證注入、hooks 通知）在一台 VM 上端到端架起來的實作記錄見 [遠端 agent 工作機實作記錄](/linux/tools/remote/agent-workstation-vm-handson/)；機器擺家用還是 VPS、隔離層的信任邊界與 skip-permissions 定位見 [遠端 agent 工作機選型](/linux/tools/remote/agent-workstation-home-vs-vps/) 與 [在 container 裡跑 Claude Code](/linux/tools/remote/claude-code-container-and-hooks/)；憑證怎麼注入而不進 image 或 repo 見 [機密 runtime 注入](/linux/dotfile/knowledge-cards/runtime-secret-injection/)。

## 下一步

把這三到四個障礙解決掉，一台機器就能在你離開後自己跑完工作、把成果送回你手上。這篇是 [外部連入](../ssh-keyless-bootstrap/)（怎麼連進去）的延伸——從「我連進去手動操作」進到「我設好讓它自己跑」。而要讓那個無人值守的任務在失敗時還留得下可診斷的痕跡，回到 [可除錯的 bootstrap](../observable-bootstrap/) 的原則：無人盯著的任務尤其需要把可觀測性內建進去，因為你不在場、只能事後從 log 重建發生了什麼。
