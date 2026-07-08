---
title: "在 container 裡跑 Claude Code：安裝、認證與 hooks 通知"
date: 2026-07-08
description: "要把 Claude Code 裝進 container 當遠端 agent、遇到重建後要重認證、或想讓任務結束自動推通知時回來讀"
weight: 6
tags: ["linux", "remote", "claude-code", "docker", "agent", "hooks"]
---

把 Claude Code 裝進 container 當遠端 agent 工作機時，真正要解的兩件事是：認證怎麼活過 container 重建、以及任務結束怎麼主動通知。這篇聚焦 Claude Code 本身在這個情境下的安裝、認證模型與 hooks 配置——[遠端 agent 工作機實作記錄](../agent-workstation-vm-handson/) 的 Step 6-8 是完整的端到端脈絡，這裡把其中 Claude Code 相關的機制單獨講清楚，因為它的認證模型跟直覺不同、踩過的人不少。

## 安裝：一個 npm 全域套件

Claude Code 是 npm 套件，需要 Node runtime。在 container 裡最省事的是用官方 node base image、直接全域安裝：

```dockerfile
FROM node:22-bookworm-slim
RUN npm install -g @anthropic-ai/claude-code
```

用 node base 而非在別的 base 上自己裝 Node，少一層版本漂移的風險。base image 的 tag 要釘住（見 [Image Tag Pinning](/linux/dotfile/knowledge-cards/image-tag-pinning/)），讓 image 可重現。

## 認證：setup-token 是 env-var 注入模型

對無人值守的容器化 agent，`claude setup-token` 給的認證形態是「長效 token 的環境變數注入」、而不是「一次登入、狀態存在本地之後都在」。這是最容易誤解的一點。

`setup-token` 走一次互動登入（需要真 TTY、`docker run -it`），完成後印出一個 `sk-ant-oat01-` 開頭的長效 token（實測有效約一年）。關鍵是：它**不會**把這顆 token 寫進 `~/.claude`、只把它印出來、明示你設成環境變數 `CLAUDE_CODE_OAUTH_TOKEN`。所以持久化的責任在你——把 token 存成 host 側的機密、在 `docker run` 時注入：

```bash
# 存成 host 的 gitignored 機密（不進 image 也不進 git）
printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$TOKEN" > ~/.env && chmod 600 ~/.env

# 每次 run 注入
docker run --rm --env-file ~/.env <image> claude -p "任務" --dangerously-skip-permissions
```

這個「認證走環境變數注入的機密、不烤進 image 也不進 repo」正是 [機密 runtime 注入](/linux/dotfile/knowledge-cards/runtime-secret-injection/) 的實例。好處是認證跟 image、container 生命週期完全解耦：rebuild image 幾次都不影響認證、換憑證只改注入的檔。

## 認證綁 token 注入、不綁 session

env-var 模型的直接後果是：**能不能認證，取決於這次 run 有沒有注入 token、跟 session 或登入態無關**。這解釋幾個會困惑的現象：

- 直接打 `claude`（沒注入 token）即使在一個還活著的多工器 session 裡，也會要求重新認證——因為它沒拿到憑證。
- 在一個 `--rm` 的臨時 container 裡真的走一次互動登入，憑證寫進容器的 `~/.claude`、容器一結束就蒸發（除非登入時掛了 volume 讓它落在持久儲存）。所以「在臨時容器裡登入」多半是白做、下次又被要求認證。

可靠的做法是不依賴任何登入態、每次用一個 helper 把 token 注入。要驗證認證確實純綁 token：不掛任何 volume（排除一切存檔登入）、只注入 token 即認證成功；不注入則回 `Not logged in`——這證明認證來源純粹是注入的 token。

## 狀態的兩個位置：~/.claude 與 .claude.json

Claude Code 的狀態分兩處放，持久化邊界不同：

- **`~/.claude/`**（目錄）：放設定 `settings.json`（含 hooks）等。掛成 named volume 就跨 container 重建持久化。
- **`$HOME/.claude.json`**（單一檔）：放專案信任、onboarding 狀態這類頂層設定。它**不在** `~/.claude/` 目錄裡，所以掛 `~/.claude` 的 volume 不會涵蓋它——重建後會出現「configuration file not found」的非致命警告。

判讀原則是分清缺的是「認證」還是「設定」：認證缺了（沒注入 token）agent 直接無法運作；`.claude.json` 缺了只是回到預設狀態、用 token + `--dangerously-skip-permissions` 的無人值守流程照跑。要保留專案級狀態（逐專案信任、MCP 設定）才需要額外把 `.claude.json` 也掛成持久檔。把 `~/.claude` 掛成 volume 時、還要注意掛載點 owner（見 [Docker named volume 掛載點 owner](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/)）——空 volume 預設 root-owned、非 root 使用者寫不進憑證與設定。

## hooks：任務結束推通知

Claude Code 的 hooks 讓你在特定事件觸發外部指令。把工作流從「掛在終端上等」翻成「離開、跑完被叫回來」的關鍵是 `Stop` hook——它在每次回應結束時觸發，對應「一輪任務跑完」這個要通知的時機。設定寫在 `~/.claude/settings.json`：

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [
        { "type": "command",
          "command": "curl -s -H 'Title: 任務完成' -d 'agent 跑完了' https://ntfy.sh/<你的-topic>" }
      ] }
    ]
  }
}
```

觸發事件的選擇有語意差別：`Stop` 是「這一輪跑完了」，另一個候選 `Notification` 是 agent 主動要求關注時觸發、語意是「需要你介入」。兩者可並存但對應不同時機。推播服務本身（ntfy topic 是機密、不進 git）見 [ntfy 推播通知服務](../../../debug/ntfy-push-notification-service/)。

hook 的第一個除錯檢查點是「hook 指令依賴的工具在 container 裡存不存在」：上面的 hook 用 `curl`，而多數 slim base image（`node:slim` 這類）不內建 curl——少了它、hook 的指令會找不到執行檔而靜默失效，表現為「手動 curl 通、hook 卻不發訊」。修法是把 curl 加進 image 的套件安裝。

## --dangerously-skip-permissions 在 container 下的定位

無人值守跑 `claude -p` 時通常要加 `--dangerously-skip-permissions`，在容器化這個架構下這是正確選擇、不是偷懶：container 邊界本身就是權限邊界。agent 只碰得到掛進去的工作目錄（掛載清單即授權清單）、爆了困在 cgroup 的資源上限內、看不到未掛載的 host 路徑。既然容器已經把 agent 圈在一個受限的沙盒裡，容器內再逐次確認檔案權限是重複的一層。把信任邊界劃在容器邊界（mount 清單 + 資源上限），而不是容器內的每次操作確認，才對得上這個架構。

## 下一步路由

- 完整的端到端脈絡（連線 / session / 隔離三層怎麼疊起來）：[遠端 agent 工作機實作記錄](../agent-workstation-vm-handson/)
- 機器該放家用還是 VPS、隔離層的信任邊界判讀：[遠端 agent 工作機選型](../agent-workstation-home-vs-vps/)
- 推播通知服務的架構與自架取捨：[ntfy 推播通知服務](../../../debug/ntfy-push-notification-service/)
- 相關術語卡：[機密 runtime 注入](/linux/dotfile/knowledge-cards/runtime-secret-injection/)、[Docker named volume 掛載點 owner](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/)
