---
title: "Hands-on：安裝 ComfyUI + SDXL base"
date: 2026-05-12
description: "git clone、venv、pip install requirements、SDXL safetensors 放哪、--listen 啟動 server、瀏覽器 workflow 驗證"
tags: ["llm", "hands-on", "comfyui", "stable-diffusion", "diffusion"]
weight: 1
---

本篇紀錄裝 ComfyUI 跟 Stable Diffusion XL base 模型、在 Apple Silicon Mac 上跑通最小 text-to-image 流程。ComfyUI 是 2026 年 Apple Silicon 跑 [Diffusion](/llm/knowledge-cards/diffusion/) 最主流的選擇——節點式工作流、跨平台、Python 環境、容易客製化。Draw Things（Mac 原生 GUI）更簡單、但 ComfyUI 接 workflow 跟 custom node 的能力強很多。

> **驗證日期**：2026-05-12
> **ComfyUI**：main branch、shallow clone
> **示範模型**：Stable Diffusion XL base 1.0（6.5 GB、`stabilityai/stable-diffusion-xl-base-1.0`）
> **Python**：3.14（venv 隔離、不污染系統）

## 前置設定

| 項目         | 檢查指令                                            | 預期                                             |
| ------------ | --------------------------------------------------- | ------------------------------------------------ |
| Git          | `which git`                                         | `/usr/bin/git` 或 brew 版                        |
| Python 3.10+ | `python3 --version`                                 | 3.10 ~ 3.14 都可、本 demo 用 3.14                |
| 磁碟空間     | `df -h ~`                                           | 至少 15 GB（runtime 3 GB + SDXL 6.5 GB + cache） |
| 統一記憶體   | `system_profiler SPHardwareDataType \| grep Memory` | 至少 16 GB、推薦 32 GB+                          |

ComfyUI 在 Apple Silicon 跑 Diffusion 用 MPS（Metal Performance Shaders）backend、不需要 NVIDIA CUDA。但跑 SDXL 至少要 12 GB 統一記憶體留給 model + activation、16 GB Mac 跟其他 app 一起會吃緊。

## Clone ComfyUI

放在 `~/Projects/` 下、跟其他 dev project 同層：

```bash
cd ~/Projects
git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

`--depth 1` 只拉最新 commit、不拉全部歷史、省幾百 MB。要追歷史 / submit PR 才需要 full clone。

ComfyUI 目錄結構（核心部分）：

```text
ComfyUI/
├── main.py              # 啟動 entry point
├── server.py            # HTTP server
├── nodes.py             # 內建節點實作
├── custom_nodes/        # 第三方 / 客製節點放這
├── models/
│   ├── checkpoints/     # SD / SDXL 主 model 檔放這
│   ├── loras/           # LoRA 微調權重
│   ├── vae/             # VAE 模型
│   ├── controlnet/      # ControlNet 模型
│   └── ...
├── output/              # 生成的圖
├── input/               # 拖進 ComfyUI 的圖片
└── requirements.txt
```

## 建 venv + 裝 dependencies

ComfyUI requirements 含 PyTorch、numpy、PIL、safetensors、einops 等、套件多、版本敏感。用 venv 隔離：

```bash
cd ~/Projects/ComfyUI
python3 -m venv venv
source venv/bin/activate
python --version  # 確認在 venv 內
pip install --upgrade pip
```

裝 dependencies：

```bash
pip install -r requirements.txt
```

實測時間：10-15 分鐘（torch + 各種 dep）、首次跑會編譯部分 C extension。完成後預期看到：

```text
Successfully installed Mako-... MarkupSafe-... Pillow-... PyOpenGL-... ...
  torch-... torchvision-... torchaudio-... ...
  safetensors-... transformers-... ...
```

驗證 PyTorch + MPS：

```bash
python -c "import torch; print('torch:', torch.__version__, 'mps:', torch.backends.mps.is_available())"
# torch: 2.x.x mps: True
```

`mps: True` 表示 Apple Silicon GPU 加速可用。

## 下載 SDXL base 模型

SDXL base 約 6.5 GB、是 Stable Diffusion XL 的基礎 model。從 Hugging Face 拉到 ComfyUI 的 `models/checkpoints/`：

```bash
mkdir -p ~/Projects/ComfyUI/models/checkpoints
cd ~/Projects/ComfyUI/models/checkpoints

curl -L -o sd_xl_base_1.0.safetensors \
  "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors?download=true"
```

下載時間視網速、10-30 分鐘 broadband 都正常。完成後：

```bash
ls -lh sd_xl_base_1.0.safetensors
# 6.5 GB
```

可選的進階模型：

| Model            | 大小   | 用途                          |
| ---------------- | ------ | ----------------------------- |
| SDXL base 1.0    | 6.5 GB | 基礎、本 demo 用              |
| SDXL refiner 1.0 | 6.1 GB | 跟 base 配對、提升細節        |
| SD 1.5           | 4.0 GB | 較小、生態最成熟（很多 LoRA） |
| Flux.1 schnell   | 12 GB  | 2024+ 最強開源 SD 級          |
| Flux.1 dev       | 24 GB  | Flux 完整版、品質最佳         |

SDXL 6.5 GB 是「能驗證 + 不過大」的甜蜜點。再小可以選 SD 1.5（4 GB）、跑 Flux 要 24 GB 磁碟 + 16 GB+ 統一記憶體。

## 啟動 ComfyUI Server

```bash
cd ~/Projects/ComfyUI
source venv/bin/activate
python main.py
```

預期輸出：

```text
[Prompt Server] Starting ComfyUI...
Total VRAM 32768 MB, total RAM 32768 MB
pytorch version: 2.x.x
Set vram state to: SHARED
Device: mps
Using sub quadratic attention for cross-attention
...
Starting server
To see the GUI go to: http://127.0.0.1:8188
```

關鍵驗證：

- `Device: mps` → Apple Silicon GPU 啟用 ✓
- `Starting server` + `http://127.0.0.1:8188` → server 跑了 ✓

開瀏覽器到 `http://127.0.0.1:8188`、看到節點式 UI 就成功。第一次開啟會載入預設 workflow（一個簡單 text-to-image）。

要對外暴露（讓 LAN 內其他機器連）：

```bash
python main.py --listen 0.0.0.0 --port 8188
```

跟 [0.7 隱私資料流](/llm/00-foundations/privacy-data-flow/) 提的一樣、`0.0.0.0` 等於暴露給整個區網、家用 OK 公共網路要小心。

## 跑第一張圖

ComfyUI 預設 workflow 是 text-to-image：

1. **CheckpointLoader 節點**：選 `sd_xl_base_1.0.safetensors`。
2. **CLIPTextEncode（Prompt）節點**：輸入 prompt、例如 `a photograph of a cat sitting on a wooden chair, natural lighting`。
3. **CLIPTextEncode（Negative）節點**：輸入 negative prompt、例如 `blurry, low quality, artifacts`。
4. **EmptyLatentImage 節點**：設定 1024×1024（SDXL 最佳尺寸）。
5. **KSampler 節點**：steps=20、cfg=7、sampler=`euler` 或 `dpmpp_2m`。
6. **VAEDecode 節點**：把 latent 轉成 RGB image。
7. **SaveImage 節點**：存到 `output/`。

點右側 panel 的 `Queue Prompt`、開始生成。

實測時間（M4 Pro 32GB、SDXL base、1024×1024、MPS backend）：

| Steps | 第一張（含 model 載入） | 後續同 model | 備註                      |
| ----- | ----------------------- | ------------ | ------------------------- |
| 15    | 約 100-110 秒           | 約 30-40 秒  | 本驗證實測 106s（含載入） |
| 20    | 約 130-150 秒           | 約 40-60 秒  | ComfyUI 預設值            |
| 30    | 約 200 秒               | 約 80 秒     | 品質更高、邊際效益小      |

16GB Mac 跑 SDXL：每張 60-180 秒、可能會降頻。

生成完成後在 `output/` 看到 PNG 檔（如 `comfyui-test_00001_.png`）。

## 用 REST API 直接生成（不開瀏覽器）

GUI 適合互動探索、自動化要走 REST API。完整 script 在 `scripts/comfyui-test/generate.py`、實際驗證指令：

```bash
cd ~/Projects/blog
python3 scripts/comfyui-test/generate.py --steps 15
```

腳本流程：

```python
def build_workflow(prompt_text, neg_text, steps):
    return {
        "3": {"inputs": {"seed": 42, "steps": steps, "cfg": 7.0, "sampler_name": "euler",
                         "scheduler": "normal", "denoise": 1.0,
                         "model": ["4", 0], "positive": ["6", 0],
                         "negative": ["7", 0], "latent_image": ["5", 0]},
              "class_type": "KSampler"},
        "4": {"inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
              "class_type": "CheckpointLoaderSimple"},
        "5": {"inputs": {"width": 1024, "height": 1024, "batch_size": 1},
              "class_type": "EmptyLatentImage"},
        "6": {"inputs": {"text": prompt_text, "clip": ["4", 1]},
              "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"text": neg_text, "clip": ["4", 1]},
              "class_type": "CLIPTextEncode"},
        "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]},
              "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": "comfyui-test", "images": ["8", 0]},
              "class_type": "SaveImage"},
    }
```

**workflow JSON 結構解釋**：

- **每個 key（"3"、"4"、…）是節點 ID**。任意整數字串、只要在 workflow 內唯一即可。
- **`class_type`**：節點類型（KSampler、CheckpointLoaderSimple、CLIPTextEncode 等）、ComfyUI 內建。
- **`inputs`**：節點參數。標量值（如 `1024`、`"euler"`）直接寫；連到別的節點輸出用 `[node_id, output_index]` 形式。
- **`["4", 0]`** 表示「節點 4 的第 0 個 output」。CheckpointLoaderSimple 有三個 output：`model`（0）、`clip`（1）、`vae`（2）、所以 `["4", 0]` 是 model、`["4", 1]` 是 clip、`["4", 2]` 是 vae。

**每個節點做什麼**：

- **4 CheckpointLoaderSimple**：載 SDXL safetensors、輸出 model / clip / vae 三個東西。是整條 graph 的根。
- **5 EmptyLatentImage**：建一張 1024×1024 的空白 latent tensor（不是 RGB 圖、是 4-channel latent space tensor）。SDXL 的 「畫布」。
- **6 CLIPTextEncode (positive)**：把 prompt 文字用 CLIP text encoder 轉成 conditioning vector。
- **7 CLIPTextEncode (negative)**：同上、但是 negative prompt（要 avoid 的特徵）。
- **3 KSampler**：核心 denoising loop。15-30 個 step、把 latent 從噪聲變成跟 conditioning 對齊的 latent。
- **8 VAEDecode**：把 latent 用 VAE 解碼成 RGB 圖（1024×1024×3）。
- **9 SaveImage**：寫 PNG 到 `output/` 目錄、檔名 prefix `comfyui-test`。

**為什麼 graph 結構這樣**：

- **為什麼 model / clip / vae 從同一個 checkpoint 拿**：SDXL 設計上三個元件互相 train、必須同源。從不同 checkpoint 拿會造成生成品質崩。
- **為什麼 EmptyLatentImage 不直接接 KSampler、要設 batch_size**：保留 batch 維度、未來要 batch generation（一次生 4 張）改 `batch_size: 4` 就好、其他節點不用改。
- **為什麼 sampler 用 `euler`、scheduler 用 `normal`**：最簡單的組合、SDXL base 上品質可預測。其他選項（`dpmpp_2m`、`karras` scheduler 等）品質可能更好但效果各模型不同。
- **為什麼 cfg=7.0**：classifier-free guidance scale。SDXL 的標準預設、太低（< 3）模型忽略 prompt、太高（> 12）過 saturated。
- **為什麼 seed=42**：固定 seed 讓結果可重現。每次跑同 prompt 同 seed 同 model 結果完全一樣——是調 prompt / 比較 model 的必要條件。

```python
def main():
    workflow = build_workflow(args.prompt, args.neg, args.steps)
    client_id = str(uuid.uuid4())
    resp = http_post_json("/prompt", {"prompt": workflow, "client_id": client_id})
    prompt_id = resp["prompt_id"]

    while True:
        time.sleep(2)
        history = http_get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            break

    img = outputs["9"]["images"][0]
    qs = urllib.parse.urlencode({"filename": img["filename"], "type": "output"})
    blob = http_get_bytes(f"/view?{qs}")
    Path(args.out).write_bytes(blob)
```

**每段做什麼**：

1. **`client_id = str(uuid.uuid4())`**：每個 client 識別碼。ComfyUI 用 client_id 把 progress events 路由給正確 WebSocket subscriber。本 demo 用 polling、client_id 隨意產生即可。
2. **`POST /prompt`**：送 workflow + client_id、server 回 `prompt_id`（這次 job 的 UUID）。Server 把 workflow 丟進 internal queue、立刻 return、不會等 generation。
3. **`while True: time.sleep(2); GET /history/{prompt_id}`**：polling 等 job 完成。完成的 job 才會出現在 `/history` 裡（執行中 / queued 都不算）。
4. **`if prompt_id in history`**：完成判讀——history 內出現該 prompt_id 表示 generation 結束。
5. **`outputs["9"]["images"][0]`**：節點 9 (SaveImage) 的輸出、含 `filename`、`subfolder`、`type` 等資訊。
6. **`/view?filename=...&type=output`**：拿生成的 PNG bytes。`type=output` 是 ComfyUI 的內部 dir 標記（區分 output / input / temp）。

**為什麼這樣設計**：

- **為什麼 polling 而不是 WebSocket**：WebSocket 要 subscribe events、處理 connection lifecycle、邏輯複雜。Polling 兩行解決、對教學 demo 夠用。Production 自動化系統建議用 WebSocket、知道每個 progress event。
- **為什麼 `time.sleep(2)`**：太短（< 1s）對 server 造成不必要 polling；太長（> 5s）感知延遲明顯。2 秒是 demo 友善平衡。
- **為什麼用 prompt_id 而不是 client_id 查 history**：一個 client 可能送多個 job、prompt_id 唯一識別 job。client_id 主要用 WebSocket 訂閱、不是 history query 主鍵。
- **為什麼 `Path(args.out).write_bytes(blob)`**：直接 binary 寫檔、不要 `open(...).write()` 因為 PNG 是 binary、text mode 會出錯。

**實測**：M4 Pro 32GB、prompt 「a photograph of an orange cat sitting on a wooden chair, soft natural lighting, detailed fur」、15 steps、cfg=7、euler+normal sampler、seed=42 → 106 秒生成 1024×1024 PNG、1.65 MB。

## 跟 ComfyUI 內部的 OpenAI 相容 API

ComfyUI 沒提供 OpenAI 相容 API、它的 API 是自己的 REST + WebSocket：

- `POST /prompt`：丟一個 workflow JSON、回傳 job id。
- `GET /history/{prompt_id}`：查看生成結果。
- `GET /view?filename=X`：拿生成的圖。
- WebSocket：訂閱 job progress events。

API 形狀跟 Diffusion 任務匹配、跟 LLM 的 `/chat/completions` 完全不同——這正是 [4.0 RAG 章節](/llm/04-applications/rag-principles/) 提到「Diffusion 跟 Transformer 工具鏈互不通用」的具體展現。Ollama / LM Studio 對接 Continue.dev 的 OpenAI 相容路徑、跟 ComfyUI 接 SDXL 是完全平行的兩條路。

## 常用 Custom Nodes

ComfyUI 的核心功能來自 custom nodes、社群維護。最常用：

| Custom Node            | 功能                              |
| ---------------------- | --------------------------------- |
| ComfyUI-Manager        | 管理其他 custom node、安裝 / 更新 |
| ComfyUI-Impact-Pack    | 物件偵測、masking、inpainting     |
| ComfyUI-AnimateDiff    | 影片動畫生成                      |
| ComfyUI-ControlNet-Aux | ControlNet preprocessor           |
| ComfyUI-IPAdapter-plus | 圖像 reference embedding          |

安裝方式（透過 ComfyUI-Manager）：

```bash
cd ~/Projects/ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
# 重啟 ComfyUI、UI 多一個 Manager 按鈕、之後用 Manager 裝其他 node
```

## 常見坑

### Python 版本太新、torch 沒 wheel

PyTorch 對最新 Python（3.13、3.14）的 wheel 發布有 lag、可能 `pip install -r requirements.txt` 跑 build from source 慢 + 失敗。退到 Python 3.11 / 3.12：

```bash
brew install python@3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### `mps: False`、跑在 CPU 上

確認 PyTorch 是 Apple Silicon 版本（不是 x86_64 emulation）：

```bash
python -c "import platform; print(platform.machine())"
# arm64 ← 正確；x86_64 ← 走 Rosetta、要重裝
```

如果是 x86_64、表示 venv 用了 Intel Python。重建 venv：

```bash
deactivate
rm -rf venv
arch -arm64 python3 -m venv venv
```

### 記憶體不夠、推論時 crash

SDXL 在 16 GB Mac 上吃緊、可能 swap 或 crash。緩解：

```bash
# 降解析度
python main.py --normalvram   # 預設、~12 GB
python main.py --lowvram      # 較省、~8 GB、慢
python main.py --novram       # 極省、~4 GB、極慢、實用上界
```

或換 SD 1.5（4 GB checkpoint）、記憶體需求 < SDXL 的一半。

### Workflow JSON 載入失敗

ComfyUI workflow 是 JSON 描述節點 + 連線。如果是別人分享的 workflow、可能用了你沒裝的 custom node。錯誤訊息會列出缺哪些 node、用 ComfyUI-Manager 補裝。

### Port 8188 被佔

```bash
lsof -i :8188
python main.py --port 8189  # 改 port
```

## 跟 LLM stack 並存

ComfyUI 用 port 8188、跟 Ollama (11434) / LM Studio (1234) 完全不撞、可同時跑。實務配置：

| 服務       | Port  | 用途                   |
| ---------- | ----- | ---------------------- |
| Ollama     | 11434 | 寫 code、對話          |
| ComfyUI    | 8188  | 產圖                   |
| LM Studio  | 1234  | 探索新 LLM             |
| Open WebUI | 3000  | ChatGPT 風格瀏覽器介面 |

各服務獨立、不干擾、可以一台 Mac 跑全部（看記憶體預算）。

## 何時這篇會過時

- ComfyUI 主分支 API 短期內穩定（大量社群依賴）。
- SDXL base 1.0 不會消失、但會被新版本（SDXL 1.1、Flux 等）取代——「下載 .safetensors 放 models/checkpoints/」流程不變。
- MPS backend 持續優化、效能會提升、但介面不變。
- Python 版本相容性會持續演化、`pip install -r requirements.txt` 偶爾要降版 Python。

讀的時候若 pip install 失敗、看 ComfyUI GitHub issues 跟 PyTorch release notes 對應的 Python 版本。
