---
title: "5.0 VRAM + RAM 分層預算"
date: 2026-05-12
description: "PC 獨立 GPU 場景的記憶體預算判讀：VRAM 是快的世界、RAM 是大的世界、PCIe 把兩個世界連起來"
tags: ["llm", "discrete-gpu", "vram", "ram", "hardware", "memory-budget"]
weight: 1
---

PC 場景跑本地 LLM 的判讀模型本質跟 [Mac 統一記憶體](/llm/00-foundations/hardware-memory-budget/) 不同：Mac 是一塊預算切系統 / 模型 / [KV cache](/llm/knowledge-cards/kv-cache/)、PC 是 [VRAM](/llm/knowledge-cards/vram/) 跟系統 RAM 兩塊**分層預算**、靠 [PCIe](/llm/knowledge-cards/pcie/) 連起來。本章把「16GB 5060 Ti 能跑 30B 嗎」這類含糊說法、換成可操作的兩塊預算判讀。生字速度上限主要受 [memory bandwidth](/llm/knowledge-cards/memory-bandwidth/) 影響、跟 [統一記憶體](/llm/knowledge-cards/unified-memory/) 的 Mac 場景判讀軸不同。

讀完本章後、你可以對自己這台 PC 直接回答：能跑哪些模型、要不要做 MoE 卸載、KV cache 該量化到哪一級、context 能開多大、系統 RAM 容量該不該升級。

## 本章目標

讀完本章後、你應該能：

1. 看 PC 規格（VRAM + RAM）立刻知道能跑哪一級的模型、需不需要卸載。
2. 理解為什麼 16GB VRAM + 64GB RAM 跑 30B MoE 比跑 14B Dense 全載 VRAM 划算。
3. 判讀 KV cache 量化跟 context 長度的權衡。
4. 判斷自己這台 PC 適不適合跑本地 LLM、瓶頸在 VRAM 還是 RAM。

## PC 記憶體預算的基本算式

PC 跑本地 LLM 的預算拆成兩塊、各有自己的容量上限：

```text
VRAM = 顯卡記憶體（GDDR6/7）= 高頻寬區
  └── 通常需放：當前活躍模型層 + KV cache + 推論中間結果

系統 RAM = 主機板上的 DDR4/5 = 高容量區
  └── 可以放：MoE 不活躍專家層（透過 --n-cpu-moe）、暫存權重、context cache
  └── 通常需保留：作業系統 + 應用程式 + GPU driver pinned memory

PCIe = 兩塊預算之間的橋
  └── 5.0 x16 廠商標稱單向約 64 GB/s、模型載入時較常成為瓶頸、推論時通常較少
```

兩塊預算各自的估算原則（具體數值依硬體世代、廠商規格與驅動版本而變化、本章引用的數字以廠商規格表為主、實際吞吐受系統配置影響）：

1. **VRAM 容量**：決定能放多少模型層。Dense 模型若要生字快、所有層都該在 VRAM；MoE 模型可以只放「共用層 + 部分專家」、其餘走 RAM。
2. **VRAM 頻寬**：影響生字速度上限。常見消費級 NVIDIA 卡的廠商標稱頻寬（向廠商規格表查驗）大致落在數百 GB/s 到約 1 TB/s 級的區間（如 RTX 5060 Ti 16GB 標稱約 448 GB/s、RTX 5070 Ti 約 896 GB/s）；生字 t/s 約等於「VRAM 頻寬 ÷ 模型每 token 讀取的 bytes」、但實際吞吐還受 CUDA backend、量化方式與 batch size 影響。
3. **系統 RAM 容量**：影響 MoE 卸載與多模型併存的彈性。對 16GB VRAM 卡而言、64GB DDR5 通常足以支撐重度 MoE 卸載、128GB 對多模型併存或長 context cache 更從容、32GB 則會限縮可卸載的層數。
4. **系統 RAM 頻寬**：影響卸載到 CPU 的層走多快。DDR5 6000 雙通道的標稱頻寬約 96 GB/s（依主機板、CMK 模組與時序變動）、相對 VRAM 慢約一個量級、所以卸載層數要跟可接受的生字速度損失一起調。
5. **PCIe 頻寬**：模型載入時通常是瓶頸、單人推論時較少成為主要瓶頸（除非每 token 都需要把大量卸載權重拉回 VRAM）。

## PC 配置與可運作模型對照

下表整理 2026 年 5 月常見消費級 NVIDIA GPU 加上不同 RAM 容量、可運作模型的數量級對照。體感標籤是社群常見回報的相對描述、實際因 llama.cpp / Ollama 版本、CUDA backend、模型量化版本、`--n-cpu-moe` 設定與工作流類型而變動、需自行實測校準。

| GPU                   | VRAM | RAM 配置     | 全載 VRAM 可跑 Dense | 配合 MoE 卸載可跑模型        | 體感區段（社群回報） | 備註                                   |
| --------------------- | ---- | ------------ | -------------------- | ---------------------------- | -------------------- | -------------------------------------- |
| RTX 4060 / 5060       | 8GB  | 16GB         | 7B Q4                | 14B MoE 卸載                 | 入門體驗             | 對寫 code 的中大型任務通常仍須混用雲端 |
| RTX 4060 Ti / 5060 Ti | 16GB | 32GB         | 14B Q4 / 20B Q3      | 30B MoE 卸載部分專家層       | 可日常使用           | MoE 卸載空間受 32GB RAM 限制           |
| RTX 4060 Ti / 5060 Ti | 16GB | 64GB         | 14B Q4               | 30B MoE Q4 + 重度卸載        | 多數寫 code 任務流暢 | 2026 年常被列為合理起點之一            |
| RTX 4070 Ti / 5070 Ti | 16GB | 64GB         | 14B Q4               | 30B MoE Q4 / 70B MoE Q3 卸載 | 補完體感更接近即時   | VRAM 頻寬規格上接近 5060 Ti 兩倍       |
| RTX 4090              | 24GB | 64GB         | 32B Q4 / 70B Q3      | 70B MoE Q4                   | 大型任務也流暢       | Dense 70B 可在 Q3 量化下全載           |
| RTX 5090              | 32GB | 64GB ~ 128GB | 70B Q4               | 100B+ MoE 卸載               | 容量充裕             | 適合 70B Dense 主力或多模型併存場景    |

讀這張表要注意四件事：

1. **「全載 VRAM」跟「卸載」是兩種選型**。全載生字較快但模型較小、卸載生字較慢但能跑較大模型；MoE 結構讓兩者的速度差距小於 Dense 模型。
2. **量化等級可以調整**。16GB VRAM 跑 30B MoE Q4 比跑 30B MoE Q5 留下更多 VRAM 餘量、給 KV cache 跟併發數使用。
3. **RAM 容量影響選型**。32GB RAM 配 16GB VRAM 時、可卸載層數有限、能跑的最大 MoE 規模受限；64GB RAM 配 16GB VRAM 通常足以支撐 30B 級 MoE 的重度卸載。
4. **多卡升級建議在單卡跑穩後評估**。雙 GPU 在 llama.cpp 上要設定 [tensor split](/llm/knowledge-cards/llama-cpp-tensor-split/)、實際速度提升依模型與配置變化；消費級主機板的 PCIe lane 分配（常見一條 x16 + 一條 x4）也會影響多卡效益。建議先把單卡跑熟、再依瓶頸決定是否多卡。

## 為什麼 16GB VRAM + 64GB RAM 常被列為寫 code 場景的合理起點

這個配置（RTX 5060 Ti 16GB / RTX 5070 Ti 16GB + 64GB DDR5）在 2026 年 5 月的 PC 本地 LLM 社群裡、常被作為「寫 code 用途」的價格效能比合理起點。對應的判讀軸有四條：

1. **30B 級 MoE 模型在多數寫 code 任務已能勝任**。Qwen3-30B-A3B 等 [MoE](/llm/knowledge-cards/moe/) 模型在公開 coding benchmark 上的回報（如 Qwen 官方技術報告、社群 SWE-bench 跑分）顯示表現接近大型 Dense 模型；具體分數依任務類型、prompt 設計與評測版本變動、需參考各模型官方文件或 [SWE-bench 卡片](/llm/knowledge-cards/swe-bench/)。模型總參數與 [active parameter](/llm/knowledge-cards/active-parameter/) 是兩個獨立軸、影響記憶體需求跟生字速度上限。
2. **MoE 卸載讓 16GB VRAM 能載入 30B 級模型**。把約 30 層 MoE 專家權重留在 RAM、其餘放 VRAM、Qwen3-30B-A3B Q4 量化下整套模型總記憶體約落在 18 ~ 22GB 區間、其中常見約 12 ~ 14GB 在 VRAM（實際依模型結構與 `--n-cpu-moe` 設定變化）。
3. **KV cache 量化能在剩餘 VRAM 開大 context**。模型權重放好後、剩餘 VRAM 配上 K=Q8 / V=Q4 的 KV cache 量化、社群常見回報能開到 128K ~ 256K 級 context（依模型 attention 配置變化）、寫 code 場景的長 prompt 較少需要截斷。
4. **零件可分次採購、後續可升級**。相對 Apple Silicon 整機綁定配置、PC 零件（GPU、RAM、CPU、儲存）可分次採購與升級；具體零件價格依在地市場、世代與促銷波動、本文不引用具體幣值。

下表是社群討論中常被提及的兩張同代 16GB 卡的相對對照、用意是「同樣 16GB VRAM 但頻寬不同對 throughput 的影響」、不是嚴格 benchmark：

| 顯卡             | VRAM 頻寬（廠商標稱） | Prefill 數量級       | 生成數量級                      | 可開 context（量化 KV cache 下） |
| ---------------- | --------------------- | -------------------- | ------------------------------- | -------------------------------- |
| RTX 5060 Ti 16GB | 約 448 GB/s           | 數百 t/s             | 數十 t/s（較 5070 Ti 低約一半） | 128K ~ 256K 級                   |
| RTX 5070 Ti 16GB | 約 896 GB/s           | 約為 5060 Ti 的 2 倍 | 約為 5060 Ti 的 2 倍            | 128K ~ 256K 級                   |

兩張卡的差異主要在 VRAM 頻寬（廠商標稱接近 2 倍）、不在 VRAM 容量。對「同樣的模型能否載入」沒影響、對「生字多快」影響較大。實際 throughput 因驅動版本、模型量化方式、`--n-cpu-moe` 設定與 prompt 長度而變動、需自行用 `llama-bench` 或實際工作流校準。

> **事實查核註**：表中 prefill / 生成的具體數字是社群討論中常見回報的相對數量級、不是經本文系統實測的 benchmark。VRAM 頻寬以 NVIDIA 廠商規格表為主、實作上會被 GDDR 模組廠商、PCIe 版本、CUDA backend 版本影響。引用前請以最新官方規格表跟 [llama.cpp 官方 benchmark](https://github.com/ggml-org/llama.cpp/discussions) 為準。

社群常見回報的三個觀察點（同樣需以自身配置實測校準）：

1. `--n-cpu-moe` 數值往上加（如從 20 加到 30）、單張卡的 VRAM 佔用降低、可開的 context 上限拉大、但生成速度也會下降；具體下降幅度依模型 active parameter 比例變化。
2. KV cache 量化（K=Q8 / V=Q4）相對 fp16 KV cache 體積大幅壓縮、能換取更大 context 上限；寫 code 場景的補完品質影響社群多數回報為小幅或不明顯、但會視 prompt 長度與任務類型而異。
3. 系統 RAM 從 32GB 升到 64GB 後、可卸載的 MoE 層數上限明顯提高、能跑的最大模型規模也跟著拉開；具體層數依模型結構而定。

對應的 PC 配置面向（2026 年 5 月、不引用具體幣值）：

- **價格優先**：RTX 5060 Ti 16GB + 64GB DDR5 + 中階 CPU（如 AMD 9900X / Intel 14700K）+ 1TB NVMe。
- **生字速度優先**：RTX 5070 Ti 16GB + 64GB DDR5 + 中階 CPU。VRAM 容量跟 5060 Ti 相同、頻寬規格接近兩倍。
- **跑得了 70B 級**：RTX 4090 24GB / RTX 5090 32GB + 64GB ~ 128GB DDR5。

若你正準備組新機主要為了跑本地 LLM 寫 code、16GB VRAM + 64GB RAM 是社群常見的合理起點；具體選哪張卡、視預算上限與對生字速度的要求而定。

## MoE 卸載 vs 全載 Dense 的選型差異

PC 場景有 Mac 沒有的選型變數：**同樣 16GB VRAM、要跑「全載 14B Dense」還是「卸載 30B MoE」？**

兩條路線的差異：

| 維度            | 全載 14B Dense                          | 卸載 30B MoE                                    |
| --------------- | --------------------------------------- | ----------------------------------------------- |
| 生字速度        | 相對較快                                | 相對較慢、視卸載層數而定                        |
| 模型能力        | 14B 級、跨檔案重構任務的成功率較 30B 低 | 30B 級、跨檔案重構任務社群回報成功率相對較高    |
| 對 RAM 容量需求 | 較低（32GB 通常足夠）                   | 較高（64GB 常見起點、128GB 對重度使用者更從容） |
| context 上限    | KV cache 競 VRAM、上限受限              | 配合 KV cache 量化、社群回報可開 128K 級以上    |
| 系統熱度與功耗  | GPU 為主負載                            | GPU 跟 CPU 同時負擔                             |

**判讀原則**：寫 code 場景下、模型能力對任務成敗的影響通常比生字速度更顯著；30B 模型能完成的跨檔案任務、生字較慢仍可能勝過 14B 較快但解不出來的情況。若工作流以高頻短補完為主、對生字即時體感要求高、14B Dense 全載仍是合理選擇。實際取捨建議用一週實測校準。

## KV cache 量化與 context 的權衡

VRAM 預算扣掉模型權重後、剩下的空間主要給 KV cache。KV cache 跟 context 長度大致成正比、長 context 場景的 VRAM 限制跟 Mac 統一記憶體場景類似、但 PC 多了「量化 KV cache」這個工程選項。

下表為 KV cache 體積的數量級估算（依模型 attention head 數、hidden size、量化策略變化、實際值需用工具測量、本表用於說明量化前後的比例變化）：

| Context 長度 | KV cache 不量化（數量級） | KV cache K=Q8 / V=Q4（數量級） | 16GB VRAM 餘量觀察   |
| ------------ | ------------------------- | ------------------------------ | -------------------- |
| 8K tokens    | 1 GB 級                   | < 0.5 GB                       | 餘量寬鬆             |
| 32K tokens   | 數 GB 級                  | 1 ~ 2 GB                       | 量化後仍寬鬆         |
| 128K tokens  | 10 GB 級以上              | 數 GB 級                       | 不量化時 VRAM 不足   |
| 256K tokens  | 數十 GB 級                | 10 GB 級                       | 量化後接近 VRAM 上限 |

KV cache 量化在寫 code 場景的體感判讀有三條社群常見回報的原則（具體影響因模型、量化版本與工作流而變、需自行實測校準）：

1. **K（key）對量化容忍度通常較高**：key 用來計算 attention score、本質是相對量級的比較。社群多數回報指出 K=Q8 相對 fp16 在補完品質上差異不明顯、可作為較安全的起手量化等級。
2. **V（value）對量化敏感度集中在長 context 末尾**：value 是被加權平均的內容、量化誤差會累積進輸出。短 prompt（< 32K）下 V=Q4 跟 fp16 的差異多為小幅；長 prompt（128K+）的對話末尾、社群回報偶爾觀察到「對前文細節記憶較模糊」的情形、但對跨檔案 code 補完任務影響社群多數回報為小。
3. **品質影響在 coding 跟自由創作場景不同**：寫 code 的輸出空間受語法 / 型別 / 編譯限制、KV cache 量化的小幅誤差較容易被約束過濾；自由創作（小說、詩、長對話）對 V 量化較敏感、社群回報品質差異較明顯。

實務上、K=Q8 / V=Q4 是 PC 場景開大 context 的常見組合；若觀察到長 prompt 末尾的回答品質下降、可考慮把 V 升回 Q8 或 fp16（代價是 VRAM 佔用上升、context 上限會縮短）。

具體調參邏輯詳見 [5.2 KV cache 量化策略](/llm/05-discrete-gpu/kv-cache-quantization-strategy/)。

## 系統 RAM 容量在 PC 場景的角色

Mac 統一記憶體只有一個容量數字、PC 多了「VRAM」跟「系統 RAM」兩個獨立數字。PC 場景的預算分配若全部投入 VRAM、可能忽略系統 RAM 對 MoE 卸載策略的支撐角色。

系統 RAM 在本地 LLM 場景的主要用途（具體佔用量依工作流變化）：

1. **作業系統 + 開發工具**：Windows / Linux + VS Code + 瀏覽器、常見佔用約 8 ~ 16GB。
2. **GPU driver pinned memory**：NVIDIA driver 為了 PCIe DMA 會固定一塊系統 RAM、依驅動版本與配置常見約 1 ~ 2GB。
3. **MoE 卸載的專家權重**：跑 30B MoE 卸載多數專家層、所需 RAM 落在 10 GB 級以上；跑 70B MoE 重度卸載通常需要數十 GB 級。具體數字依模型結構與 `--n-cpu-moe` 設定變化。
4. **多模型併存**：同時跑 coding model + embedding model + 翻譯模型、每個各佔數 GB 級。
5. **page cache / 系統暫存**：Linux 會把剩餘 RAM 用於 page cache、模型 reload 時可加速。

對 16GB VRAM 配置而言、64GB RAM 通常足以支撐重度 MoE 卸載、是社群常見的起點容量。32GB RAM 配 16GB VRAM 在重度 MoE 卸載場景容易吃緊、可卸載層數會受限；視工作流類型、32GB 也可能足夠跑全載 Dense 模型。

## PCIe 頻寬的角色

PCIe 在「載入模型」階段較常成為瓶頸、單人推論時通常不是、但 MoE 卸載會讓 PCIe 在推論時也參與資料流：

1. **模型載入時**：PCIe 5.0 x16 廠商標稱單向約 64 GB/s（PCIe 4.0 x16 約一半）、實際走完磁碟 → RAM → VRAM 整條路徑的吞吐通常較規格低、模型載入時間視 NVMe 讀取速度、檔案系統與量化格式變動。常見差異在啟動秒數、推論階段一般感受不到。
2. **MoE 卸載推論時**：每 token 啟用的專家層權重需透過 PCIe 從 RAM 拉到 VRAM。以 Qwen3-30B-A3B 為例、每 token 啟用約 3B active parameter；若部分專家層在 RAM、每 token 需透過 PCIe 拉部分權重。單人推論場景下、相對 PCIe 5.0 x16 的可用頻寬佔比通常較小、社群多數回報不是主要瓶頸；併發數高或卸載比例極大時會逐漸顯現。
3. **多卡推論**：多卡 tensor parallel 會密集走 PCIe / NVLink。消費級 GPU 普遍不支援 NVLink、訊息走 PCIe；多卡的吞吐縮放比社群回報相對單卡 + MoE 卸載的線性度差、需依工作流評估。

實務上、單卡 + MoE 卸載場景下 PCIe 較少成為主要瓶頸；多卡或極端卸載比例下、PCIe lane 分配（如主機板的 x16 + x4 配置）會明顯影響可達吞吐。

## 給讀者的決策表

看完上面的對照後、可以照下表做決策：

| 情境                                | 建議                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| 已有 8GB VRAM 卡、想試本地          | 用 Qwen3 7B / Gemma 4 8B 試一週、評估是否值得升級、寫 code 主力可暫時保留雲端   |
| 已有 12GB VRAM 卡（如 3060 / 4070） | 14B Dense Q4 全載 / 20B MoE Q4 卸載、依寫 code 場景速度需求選擇                 |
| 已有 16GB VRAM 卡、RAM 32GB         | 先評估升級 RAM 到 64GB 再評估 MoE 卸載策略、32GB RAM 配 16GB VRAM 卸載空間有限  |
| 已有 16GB VRAM 卡、RAM 64GB         | Qwen3-30B-A3B MoE Q4 + `--n-cpu-moe` 約 30 是社群常見起點配置                   |
| 已有 24GB VRAM 卡（如 4090）        | 32B Dense Q4 全載 / 70B MoE Q4 卸載、依任務類型評估                             |
| 已有 32GB VRAM 卡（如 5090）        | 70B Dense Q4 全載通常可行、依任務評估是否仍需 MoE 卸載                          |
| 正準備組新機、價格優先              | 5060 Ti 16GB + 64GB DDR5 + 中階 CPU、整機可分次採購、具體預算依在地零件價格而定 |
| 正準備組新機、追求生字速度          | 5070 Ti 16GB + 64GB DDR5、VRAM 頻寬規格相對 5060 Ti 約 2 倍                     |
| 正準備組新機、要兼跑 70B            | 4090 24GB / 5090 32GB + 64GB ~ 128GB DDR5                                       |

## 釐清需求類型：個人使用 vs 服務多人

初次接觸本地 LLM 時、常見的疑問是「是不是要 H100 / H200 等資料中心級配置才能跑」。實際上資料中心級配置的設計目標是**大規模並發推論服務**（同時對許多 client 出 token）、跟單人寫 code 的需求側重不同。釐清需求類型後、硬體選擇會清楚很多。

三條判讀軸：

1. **能載入的模型大小**主要受 VRAM 容量影響、跟 GPU 算力等級沒有單一對應關係。16GB VRAM 配 MoE 卸載可載入 30B 級 MoE 模型；資料中心級 GPU 容量更大、能載入更大的 Dense 模型、但對個人寫 code 場景的能力提升不一定線性。
2. **生字速度上限**主要由 VRAM 頻寬影響。消費級高階卡（如 RTX 5070 Ti、4090、5090）的頻寬已足以支撐單人寫 code 場景的補完即時體感、實際差異依模型量化、context 長度與 backend 變化。
3. **大量並發推論**才需要資料中心級配置。單人開 VS Code 跟 LLM 對話、通常不會用到資料中心的並發優勢。

對應的決策路徑：先確認需求是「個人寫 code」還是「服務多人」、再選 16GB VRAM + 64GB RAM 級的起點配置、實測一週觀察模型能力是否符合任務需求、再依痛點選擇升級方向（VRAM 容量、頻寬、或多卡）。

升級到能跑 70B 級之前、建議先確認痛點是「模型能力不夠」還是「生字速度不夠」。本地 30B MoE 在多數寫 code 任務上已能勝任、社群多數使用者回報不是每個工作流都需要 70B 級模型；具體判斷需用自己的任務實測。

## 小結

PC 場景跑本地 LLM 的關鍵在於 **VRAM × RAM 兩塊預算的搭配**、單看 VRAM 容量不足以判讀完整圖像。16GB VRAM + 64GB RAM 配 30B MoE + CPU 卸載、在 2026 年的 PC 本地 LLM 社群中、常被列為寫 code 場景的合理起點之一；24GB / 32GB VRAM 則開始能勝任 70B Dense；雙卡跟資料中心級配置的價值主要在大量並發推論場景、單人使用的邊際效益依工作流而定。KV cache 量化（K=Q8 / V=Q4）值得認識、能在不大幅犧牲品質的前提下開大 context、是 PC 場景相對 Mac 多出來的工程選項。

本章引用的具體數字（VRAM 頻寬、KV cache 體積、生成速度範圍）以廠商規格、官方文件、社群常見回報為來源、實際吞吐受硬體配置、驅動版本、模型量化方式與工作流類型影響、建議讀者用 `llama-bench`、實際工作流任務與 [llama.cpp 官方 benchmark](https://github.com/ggml-org/llama.cpp/discussions) 校準。

下一章：[5.1 MoE 模型與 CPU 卸載策略](/llm/05-discrete-gpu/moe-cpu-offload-strategy/)、深入 `--n-cpu-moe` 的判讀。
