---
title: "Hands-on：LLM 運行中 + 結束的資源管理"
date: 2026-05-12
description: "RAM / 磁碟 / port 三個 dimension 的觀察跟釋放、Ollama keep_alive 跟 ComfyUI 兩種 lifecycle 對比、實測釋放數字"
tags: ["llm", "hands-on", "resource", "lifecycle", "ollama", "comfyui"]
weight: 8
---

跑本地 LLM 的核心 invariant 跟雲端不一樣：**Mac 是 shared resource、不是 dedicated GPU**。雲端 inference server 跑進 dedicated container、結束 instance 自然回收所有資源；本地[推論伺服器](/llm/knowledge-cards/inference-server/)跑在你日常用的 Mac、忘記管理會 silently 吃光 RAM、磁碟、port、最後讓系統變慢甚至 swap。

本篇紀錄三個 dimension（RAM / 磁碟 / port）的觀察工具跟釋放姿勢、對比 Ollama 跟 ComfyUI 兩種典型 lifecycle、加上實測釋放數字。對應 [0.7 隱私資料流原理](/llm/00-foundations/privacy-data-flow/)「每個 hop 都要 audit」這條思維——資源管理也是 hop 級的 audit、不是「裝完就忘」。

> **驗證日期**：2026-05-12
> **環境**：macOS 14、Apple Silicon、Ollama 0.23.2、ComfyUI 0.21.0、SDXL base 1.0

## 為什麼這事重要

雲端 inference：

```text
Container start → load model → serve requests → container stop → 所有 RAM / 磁碟 / port 自動回收
```

本地 inference：

```text
brew services start → load model on demand → serve → ??? → 你忘記 stop
                                              → RAM / 磁碟一直被佔
                                              → 下次重開機才釋放
```

具體會踩到的問題：

- **RAM**：18 GB SDXL 模型載入後不會自動卸、即使 ComfyUI idle、Python process 仍占 RAM
- **磁碟**：`ollama pull` 累積、`~/.ollama/models/blobs` 半年可長到 50 GB+、不主動清不會減
- **Port**：上次 crash 的 `ollama serve` 進程沒乾淨清、port 11434 還占著、下次啟動報「address already in use」
- **GPU / Metal**：模型載入後 Metal context 佔住、跟其他 GPU-using app（影片剪輯、遊戲）競爭

## 三個 dimension + 觀察工具

| Dimension            | 觀察指令                                             | 看什麼                                    |
| -------------------- | ---------------------------------------------------- | ----------------------------------------- |
| RAM                  | `vm_stat \| head -5`                                 | Pages free（每 page 16 KB）、空閒越多越好 |
| RAM（per process）   | Activity Monitor 或 `ps aux \| sort -k6 -rn \| head` | 哪個 process 佔最多記憶體                 |
| 磁碟                 | `df -h ~ \| tail -1`                                 | 系統 volume 剩餘                          |
| 磁碟（per dir）      | `du -sh ~/.ollama/models/blobs`                      | LLM models 累積量                         |
| Port                 | `lsof -i :11434`                                     | 誰在 listen 該 port                       |
| Process              | `ps aux \| grep -i ollama \| grep -v grep`           | Ollama / ComfyUI / Python 跑哪幾個        |
| Ollama loaded models | `ollama ps`                                          | 哪些 model 在 RAM、size、idle timer       |

實測：剛 kill 完 ComfyUI（SDXL + Python venv）後、`vm_stat` 看到 free pages 從 619K 變 1090K（每 page 16 KB）、約 **+7.5 GB RAM 釋放**——這就是 SDXL + ComfyUI process 一直占的記憶體量。

## Ollama 的 lifecycle（auto-unload 模式）

Ollama 走「按需 load / idle unload」設計：

```text
brew services start ollama          → daemon 啟動、沒 model 載入、RAM 占用 ~200 MB
                                     port 11434 listening
ollama run gemma3:4b "hello"        → 把 model 載入 RAM (~4-5 GB)
                                     立刻 generate response
                                     model 留在 RAM
(idle 5 分鐘、無新 request)         → Ollama 自動 unload model
                                     RAM 釋放、daemon 仍跑著
ollama run gemma3:4b "next"         → 重新 load model（~5-10 秒）、generate
brew services stop ollama           → daemon 結束、port 釋放
```

**關鍵參數 `OLLAMA_KEEP_ALIVE`**（環境變數、預設 `5m`）：

```bash
# 看當前 loaded models
ollama ps
# NAME         ID              SIZE      PROCESSOR    UNTIL
# gemma3:4b    a2af6cc3eb7f    5.5 GB    100% Metal   4 minutes from now

# 啟動時調 keep_alive（持續佔 RAM 直到 ollama 重啟）
OLLAMA_KEEP_ALIVE=-1 brew services restart ollama

# 啟動時讓 model 用完立即 unload
OLLAMA_KEEP_ALIVE=0 brew services restart ollama
```

選 keep_alive 的 trade-off：

| 設定         | RAM 占用                          | 首字延遲              | 適合場景             |
| ------------ | --------------------------------- | --------------------- | -------------------- |
| `0`          | 最低（generate 完立即釋放）       | 高（每次都重 load）   | 偶爾用、RAM 緊張     |
| `5m`（預設） | 中（活躍用占住、閒 5 分鐘後釋放） | 低（活躍期不重 load） | 大多場景             |
| `-1`         | 高（永久占住）                    | 最低                  | 整天頻繁用、RAM 充裕 |

**主動 unload 指令**：

```bash
# 把 idle 的 model 立刻從 RAM 卸掉、但 daemon 仍跑
curl -s http://localhost:11434/api/generate \
  -d '{"model": "gemma3:4b", "keep_alive": 0}'

# 或關掉整個 daemon
brew services stop ollama
```

## ComfyUI 的 lifecycle（持續占用模式）

ComfyUI 走完全不同模式：**model 載入後一直在 RAM、直到 server process 結束**。沒有 auto-unload 機制。

```text
python main.py                      → ComfyUI server start、port 8188 listening
                                     RAM ~3 GB（Python venv + 框架）
第一次 Queue Prompt (用 SDXL)        → 載入 sd_xl_base_1.0.safetensors (~6 GB)
                                     RAM 跳到 ~9-10 GB
                                     generate 完成、model 留在 RAM
連續多張生成                          → 維持 ~9-10 GB、沒 unload
idle 1 小時                          → 仍 ~9-10 GB（沒 timer）
切到 ControlNet workflow             → 多載 ControlNet model (~2 GB)、ComfyUI 自動 swap
                                     RAM 暫升、SD 部分可能被 evict 到 disk
Ctrl+C / pkill                       → process 結束、RAM 完全釋放
```

要釋放 ComfyUI 占的 RAM、**唯一方法是結束 server**：

```bash
# 找 PID
ps aux | grep "ComfyUI/main.py" | grep -v grep

# 優雅關（讓它 cleanup）
pkill -INT -f "ComfyUI/main.py"

# 強制 kill（如果上面沒反應、最多等 5 秒再強制）
pkill -KILL -f "ComfyUI/main.py"

# 確認 port 釋放
lsof -i :8188 | head -3
```

實測：M4 Pro 32GB、SDXL base 載入後 ComfyUI process 占 ~8 GB RAM；`pkill -9` 後 `vm_stat` 顯示 free pages 增加 ~470K page（**7.5 GB 釋放**）。

### 為什麼 Ollama 跟 ComfyUI 設計不同

| 因素                | Ollama 設計                       | ComfyUI 設計                      |
| ------------------- | --------------------------------- | --------------------------------- |
| 主要使用模式        | API 服務、IDE plugin 透過 HTTP 用 | 互動 GUI、user 連續調 prompt      |
| Model 切換頻率      | 高（不同任務換不同 model）        | 低（一次 session 通常一個 model） |
| User 期待的 latency | 低首字延遲（IDE 補完場景）        | 高 throughput（連續生圖）         |
| 結論                | Auto-unload 釋 RAM 給其他 model   | 持續載入避免重複 load 浪費        |

兩種設計都 valid、適合不同使用模式。理解差異後就知道 ComfyUI 一直占 RAM「不是 bug」、是設計選擇。

## 跟其他本地 server 對比

| Server                   | Auto-unload                  | 主動 unload 指令               | 占 RAM 觀察              |
| ------------------------ | ---------------------------- | ------------------------------ | ------------------------ |
| Ollama                   | ✓（5 分鐘 idle）             | `keep_alive: 0` 或 stop daemon | `ollama ps`              |
| LM Studio                | ✗（GUI 主動關閉 model 才釋） | GUI Eject Model                | Activity Monitor         |
| llama.cpp `llama-server` | ✗                            | kill process                   | `lsof -i :8080`          |
| ComfyUI                  | ✗                            | kill process                   | `ps aux \| grep ComfyUI` |
| oMLX                     | ✓（per model 可配）          | API endpoint                   | server log               |

**結論**：只有 Ollama 跟 oMLX 內建 auto-unload、其他都要手動釋放。GUI server（LM Studio）通常給 user 一個「Eject」按鈕、CLI server 通常要 kill process。

## 標準釋放程序

寫 code 完一天結束、要釋放所有資源、按下表順序操作：

```bash
# 1. 確認當前狀態（記下要還回去多少 RAM）
vm_stat | head -3
df -h ~ | tail -1
ollama ps
ps aux | grep -E "ollama|ComfyUI|llama-server" | grep -v grep

# 2. 釋放當前載入的 LLM models（Ollama）
brew services stop ollama
# 或保留 daemon、只 unload model：
# curl -s http://localhost:11434/api/generate -d '{"model": "<your model>", "keep_alive": 0}'

# 3. 結束 ComfyUI / 其他 GUI server
pkill -INT -f "ComfyUI/main.py" 2>/dev/null
pkill -INT -f "llama-server" 2>/dev/null
sleep 5
# 強制（如果上面沒清乾淨）
pkill -KILL -f "ComfyUI/main.py" 2>/dev/null
pkill -KILL -f "llama-server" 2>/dev/null

# 4. 驗證所有 port 釋放
lsof -i :11434 -i :1234 -i :8080 -i :8188 -i :8000 2>&1 | head

# 5. 確認釋放量
vm_stat | head -3
# free pages 該明顯增加
```

### 不該做的「釋放方式」

- **`killall Python`**：會 kill 所有 Python process、包括其他 dev tool（如 jupyter、Django）。用 `pkill -f "ComfyUI/main.py"` 等明確 pattern。
- **`rm -rf ~/.ollama`**：會清掉所有 model registry、下次要重 pull 全部 model。Cleanup 用 `ollama rm <model>` 才精準。
- **`brew uninstall ollama`**：直接卸載 Ollama 本身、過 reinstall 麻煩。Stop service 就夠。
- **重開機釋放**：work 但太重、會中斷其他工作。用 process-level 操作即可。

## 磁碟長期累積管理

Models 一旦 `pull` 進 `~/.ollama/models/blobs`、不主動 `rm` 不會減少。半年累積可長到 50 GB+。

### 觀察累積

```bash
# Ollama models 總占用
du -sh ~/.ollama/models/blobs
# 4.1G    /Users/tarragon/.ollama/models/blobs

# 逐 model 看大小
ollama list
# NAME                       ID              SIZE      MODIFIED
# gemma4:e4b                 c6eb396dbd59    9.6 GB    Less than a second ago
# nomic-embed-text:latest    0a109f422b47    274 MB    3 hours ago

# ComfyUI checkpoints 累積
du -sh ~/.ollama ~/Projects/ComfyUI/models 2>/dev/null
# 4.2G    /Users/tarragon/.ollama
# 7.0G    /Users/tarragon/Projects/ComfyUI/models
```

### 清理策略

```bash
# 刪掉很久沒用的 model
ollama rm <model-tag>

# 一次清掉所有 Ollama models（保留 daemon）
ollama list | tail -n +2 | awk '{print $1}' | xargs -I {} ollama rm {}

# 看 ComfyUI checkpoints 哪些可清
ls -lh ~/Projects/ComfyUI/models/checkpoints/

# 手動刪不要的 .safetensors（小心、不能 undo）
rm ~/Projects/ComfyUI/models/checkpoints/<old-model>.safetensors
```

### 磁碟管理 idiom

定期（每月或磁碟剩 < 20% 時）做：

1. `du -sh ~/.ollama ~/Projects/ComfyUI/models` 看當前累積
2. `ollama list` 看哪些 model 沒在用（看 `MODIFIED` 欄、太舊的考慮刪）
3. 刪實驗用的 model、保留 daily-driver
4. ComfyUI checkpoints 同樣 review

## Port / Process 排錯

### 啟動報「address already in use」

```bash
# 找誰占
lsof -i :11434
# COMMAND  PID  USER   ...   NAME
# ollama   xxx  ...    ...   TCP localhost:11434 (LISTEN)

# 看是不是 zombie process
ps aux | grep $(lsof -ti :11434 | head -1)

# 清掉
kill -9 $(lsof -ti :11434)

# 或重啟 service（會自動清舊 instance）
brew services restart ollama
```

### Ollama daemon 掛了不知道

```bash
# 健康檢查
curl -s http://localhost:11434/api/version

# 沒回應、看 service 狀態
brew services list | grep ollama

# 沒在跑、重啟
brew services start ollama

# 看 log
tail -50 /opt/homebrew/var/log/ollama.log
```

### ComfyUI 看似跑著但 Queue 不動

```bash
# 看 stdout / stderr log
tail -30 /tmp/comfyui.log  # 如果啟動時 redirect 到 log

# 看是不是 GPU / Metal stuck（極少見、但 SDXL 大量並發可能踩到）
# 解法：kill + 重啟
pkill -9 -f "ComfyUI/main.py"
```

完整排錯流程跟「先確認哪一層壞」見 [1.7 排錯方法論](/llm/01-local-llm-services/troubleshooting/)。

## 觀察記憶體佔用：實測對照

跑這幾步紀錄 baseline → load model → kill 的 RAM 變化：

```bash
# Baseline
vm_stat | grep "Pages free"
# Pages free:                              1090076.   ← ~17 GB free

# 啟動 Ollama + load 4B model
brew services start ollama
ollama run gemma3:4b "hello"
ollama ps
# NAME       SIZE     PROCESSOR    UNTIL
# gemma3:4b  5.5 GB   100% Metal   4 minutes from now

vm_stat | grep "Pages free"
# Pages free:                               750000.   ← 跌 ~5 GB（model 載入）

# 額外啟動 ComfyUI + load SDXL
nohup python main.py > /tmp/comfyui.log 2>&1 &
# 在 GUI 上 Queue Prompt 跑一次 SDXL generation
vm_stat | grep "Pages free"
# Pages free:                               280000.   ← 再跌 ~7.5 GB（SDXL 載入 + Python venv）

# kill 全部
brew services stop ollama
pkill -9 -f "ComfyUI/main.py"
sleep 3
vm_stat | grep "Pages free"
# Pages free:                              1090000.   ← 回到 baseline
```

每 page 16 KB、所以 free pages 數字 × 16 KB = 實際 free RAM bytes。

## 自動化釋放：launchd / shell alias

寫個 shell function 一鍵 cleanup：

```bash
# 加進 ~/.zshrc
llm-cleanup() {
  echo "[*] Stopping Ollama..."
  brew services stop ollama 2>/dev/null

  echo "[*] Killing ComfyUI..."
  pkill -INT -f "ComfyUI/main.py" 2>/dev/null
  sleep 3
  pkill -KILL -f "ComfyUI/main.py" 2>/dev/null

  echo "[*] Killing other model servers..."
  pkill -KILL -f "llama-server" 2>/dev/null
  pkill -KILL -f "lm-studio-server" 2>/dev/null

  echo "[*] Verifying ports..."
  for p in 11434 1234 8080 8188 8000; do
    lsof -i :$p 2>/dev/null | head -2
  done

  echo "[*] Free RAM:"
  vm_stat | grep "Pages free"
}
```

完事打 `llm-cleanup` 一鍵釋放、不用記每個 process 怎麼 kill。

## 何時這篇會過時

**不會過時的部分**：

- RAM / 磁碟 / port 三個 dimension 是長期 invariant、用什麼 LLM server 都成立。
- 「Mac 是 shared resource、需要主動管理」這個 framing。
- Ollama 跟 ComfyUI 兩種典型 lifecycle 對比（auto-unload vs persistent）。
- 觀察工具（`vm_stat`、`lsof`、`ps`、`du`、Activity Monitor）是 macOS 系統 API、不會 deprecate。
- 標準釋放程序、自動化 shell function 模式。

**會變的部分**：

- 具體 model size / RAM 占用數字（隨模型架構演化）。
- `OLLAMA_KEEP_ALIVE` 等具體環境變數名（Ollama API 演化）。
- ComfyUI 可能加 auto-unload feature（社群有 issue 在討論）。

讀的時候若指令跑不過、先 `--help` 看當前版本 flag；釋放 RAM 的「kill process」這個機制本身永遠成立。

## 跟其他 hands-on 章節的關係

- [Ollama 安裝](/llm/01-local-llm-services/hands-on/ollama-setup/)：介紹 `brew services start/stop`、本篇延伸 lifecycle 細節
- [ComfyUI 安裝](/llm/01-local-llm-services/hands-on/comfyui-setup/)：介紹 ComfyUI 啟動、本篇延伸 RAM 占用 + 釋放
- [1.7 排錯方法論](/llm/01-local-llm-services/troubleshooting/)：用三層架構定位故障、本篇是 lifecycle 視角的補完
- [0.7 隱私資料流原理](/llm/00-foundations/privacy-data-flow/)：「每個 hop 都要 audit」延伸到資源層

整體心法：本地 LLM 工作流跟雲端不一樣、要主動管理 lifecycle、不能裝完就忘。
