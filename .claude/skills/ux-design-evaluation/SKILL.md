---
name: ux-design-evaluation
description: "UX / UI 設計的系統性評估方法：把「使用者被困住」類缺口從實機測試提前到設計階段。Use for: (1) 設計或審查畫面狀態（狀態矩陣四欄：顯示 / 可用操作 / 進入條件 / 退出路徑，退出路徑為空 = 死胡同）, (2) Gate 設計（biometric / network / permission / 環境條件的成功、失敗、不確定路徑與 fallback）, (3) 輸入機制（keyboard type / submit model / IME policy / special keys 四維決策、IME 安全）, (4) 錯誤恢復（錯誤訊息、retry、error loop 逃生口、degraded mode）, (5) 導航（go/push 語意、tab / drawer / deep link、iOS vs Material 慣例）, (6) 互動回饋（回饋分層、時間門檻、spinner vs skeleton、SnackBar / Dialog / Banner 選擇）。Use when: 設計新畫面或流程、審查 UI 實作、UX review、使用者反映被卡住 / 按了沒反應 / 通知被忽略。Triggers: UX 設計, UI 設計, 畫面設計, 狀態矩陣, 退出路徑, 死胡同, gate, fallback, 生物辨識, 權限請求, 輸入框, 鍵盤, IME, 表單, 搜尋框, 錯誤訊息, retry, 重試, 降級, degraded, 導航, back 行為, deep link, tab bar, loading, spinner, skeleton, SnackBar, Dialog, Banner, Bottom Sheet, 通知形式, 按鈕狀態, debounce, 防連點, 回饋."
license: MIT
metadata:
  version: 1.0.0
  category: ux-design
---

# UX Design Evaluation

UX / UI 設計的系統性評估方法。這個 skill 的出發點是一類反覆出現的事故：功能邏輯完整、實機測試才發現使用者被困在畫面裡出不去、按鈕按了沒有任何回饋、Face ID 失敗後沒有替代路徑。加一顆 back 按鈕是 5 分鐘的事，問題在設計階段沒有工具強制回答「每個狀態怎麼離開、每道關卡失敗怎麼辦、每個動作使用者怎麼知道系統收到了」。

本 skill 把 UX 設計從「靠經驗想到」變成「靠方法查到」：每個評估維度都有可機械執行的表格或提問清單，填完表格、空白格自動暴露缺口。適用於任何前端 surface（mobile app、web、桌面），範例以 mobile 為主；不涵蓋視覺設計（色彩、字型、間距）、品牌與使用者研究方法。

---

## Core Pillars（核心支柱）

| 支柱                                               | 意義                                                                               |
| -------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Every state has an exit** 每個狀態都有退出路徑   | 畫面的每個狀態至少一條使用者可自行觸發的離開路徑；退出路徑為空 = UX 死胡同         |
| **Every gate has a fallback** 每道關卡都有替代路徑 | 使用者過不了關卡（認證失敗、斷網、權限被拒）時仍有路可走，而非被擋死               |
| **Every action gets honest feedback** 回饋即時誠實 | 每個使用者動作都有與等待時長相稱的系統回應；沒有回饋的按鈕等同壞掉的按鈕           |
| **Design decisions are artifacts** 設計決策成品化  | 狀態矩陣、gate 設計表、輸入決策表在企劃階段產出、可被 review、可直接轉成 test case |

---

## 評估流程

### 設計新畫面 / 新流程時（事前）

1. 從操作盤點（BDD 情境或功能規格）列出所有畫面與狀態
2. 每個畫面填**畫面狀態矩陣**（四欄：顯示 / 可用操作 / 進入條件 / 退出路徑）— 空白格就是設計缺口
3. 每道 gate 回答成功 / 失敗 / 不確定必答問題、產出 gate 設計表
4. 每個輸入框過輸入機制決策（keyboard type / submit model / IME policy / special keys）
5. 每個非同步操作標時間門檻帶、決定回饋形式
6. 每個導航操作回答「使用者按 back 期望回到哪裡」

### 審查既有 UI / UX review 時（事後）

依症狀路由到對應 reference（見下表），用該 reference 的檢查清單逐項掃。跨維度的快速掃描順序：先掃退出路徑（被困住的代價最高）、再掃 gate fallback、再掃回饋完整性。

---

## 觸發路由

| 觸發情境 / 症狀                                                                                    | 讀哪份 reference                     |
| -------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 設計多狀態畫面（連線 / 配對 / 同步）、使用者被困在畫面出不去、審查導航缺口、路由存在但入口找不到   | `references/screen-state-matrix.md`  |
| 設計認證 / 網路 / 權限 / 硬體條件關卡、生物辨識失敗沒退路、權限被拒後的處理、模擬器上測不到的 gate | `references/gate-fallback.md`        |
| 設計輸入框 / 表單 / 搜尋框 / CLI 輸入、鍵盤自動校正破壞輸入、密碼或 secret 欄位、驗證時機選擇      | `references/input-mechanism.md`      |
| 撰寫錯誤訊息、設計重試機制、使用者卡在錯誤迴圈、部分功能不可用的降級呈現                           | `references/error-recovery.md`       |
| 選擇導航模式（stack / tab / drawer）、go vs push 的選擇、back 行為不符預期、deep link 設計         | `references/navigation-patterns.md`  |
| 按鈕按了沒反應、重複提交、loading 該不該顯示、spinner vs skeleton、通知該用 SnackBar 還是 Dialog   | `references/interaction-feedback.md` |

每份 reference 自包含：不讀 SKILL.md 與其他 reference 也能獨立套用。

---

## 跨維度快速自檢

任何 UX / UI 變更提交前的最小檢查（細項在各 reference 內）：

- [ ] 新增或修改的畫面：每個狀態都有至少一條退出路徑？
- [ ] 涉及 gate（認證 / 網路 / 權限）：失敗與不確定路徑都有設計？
- [ ] 涉及輸入框：keyboard type 與 IME policy 是明確決策而非預設值？secret 類欄位過了 IME 安全清單？
- [ ] 涉及非同步操作：按鈕有 loading + disabled + 恢復？結果有通知？
- [ ] 涉及錯誤畫面：除了重試還有第二條路（返回 / 替代方案）？
- [ ] 涉及導航：go / push 的選擇對照過「按 back 期望回哪裡」？
- [ ] 通知形式對照過「是否需要使用者操作 × 干擾程度」二軸？
- [ ] 畫面查詢的對象有獨立生命週期（service worker / 遠端服務）：initializing 與離線分開建模？
- [ ] 批次 / 遍歷操作的完成宣告有窮盡證據、跨 context 的結果通知有端對端驗證？
- [ ] 覆蓋 / 清空既有資料的操作：有後果確認 + 確認機制故障時的安全預設？

---

## Directory Index

```text
ux-design-evaluation/
├── SKILL.md                              # 本檔：支柱 + 評估流程 + 觸發路由
└── references/
    ├── screen-state-matrix.md            # 畫面狀態矩陣：四欄定義、填寫、BDD 展開、路由可達性、happy-path 反模式
    ├── gate-fallback.md                  # Gate 分類、成功/失敗/不確定必答問題、biometric/network/permission、dev vs 真機差異
    ├── input-mechanism.md                # 輸入機制四維決策、表單/搜尋/CLI 場景、IME 安全清單
    ├── error-recovery.md                 # 錯誤訊息兩職責、retry 策略、error loop 逃生口、degraded mode
    ├── navigation-patterns.md            # 導航模式分類、go/push/pushReplacement 語意、平台慣例差異、deep link
    └── interaction-feedback.md           # 回饋三層模型、時間門檻、按鈕狀態、spinner vs skeleton、通知形式選擇
```

---

**Last Updated**: 2026-07-17
**Version**: 1.1.0 — 從一個 Chrome extension 專案的實際事故補 web / 多 context 維度（原案例庫全為 mobile app、系統性缺這一面）：狀態矩陣加 initializing 狀態（查詢對象獨立生命週期）、互動回饋加結果通知鏈路前提與完成宣告窮盡證據、gate 加破壞性操作確認與 fail-safe 預設、錯誤恢復加行動層級對位、導航加 hash SPA 路由辨識；跨維度快速自檢同步擴充
**Version**: 1.0.0 — 從單一模組的簡略版（ux-interaction-feedback：按鈕級 + 畫面級回饋）擴充為全維度 UX 設計評估 skill：新增畫面狀態矩陣、gate fallback、輸入機制、錯誤恢復、導航模式五份 reference，互動回饋 reference 併入通知模式選擇與延遲分布判讀；建立四支柱與事前 / 事後兩條評估流程
