---
title: "7.22 資安風險如何進入 Release Gate"
tags: ["Security", "Release Gate", "Risk Governance", "Deployment"]
date: 2026-04-30
weight: 92
description: "發版流程已有功能測試與 SLO 關卡、要決定哪些變更該因為資安條件被卡下來、以及卡下來時要求什麼證據"
---

發版關卡上已經有功能測試、相容性檢查與 SLO 條件。資安條件要進到同一道關卡時，要先決定兩件事：哪些變更該被卡，以及卡下來的時候要求交出什麼。這兩題答錯的方向相反——判準太寬會讓每次發版都要一輪人工審查，判準太窄會讓真正改變風險的變更沿著標準流程通過。

## 風險等級由變更動到哪一類資產決定

變更的風險等級不由 diff 的大小、涉及的檔案數或功能的商業重要性決定，這幾項與資安風險沒有穩定關係：一行設定變更可以把管理端點開到公開網路，而一次數千行的內部重構可能完全不動任何邊界。可判定的判準是變更動到哪一類資產：

| 命中的資產類別   | 具體形態                                                  |
| ---------------- | --------------------------------------------------------- |
| 認證與授權路徑   | 誰能登入、角色與範圍的定義、會話的建立與失效              |
| 對外暴露面       | 新端點、新入口、管理端點的可達來源、錯誤回應的詳細程度    |
| 秘密與憑證的位置 | 新增秘密、換發行方、改存放位置、改傳遞方式                |
| 資料分級的流向   | 把較高分級的資料送到新的儲存位置、新的接收方或新的區域    |
| 供應鏈與部署路徑 | 新依賴、新的 build 步驟、新的 artifact 來源、新的部署身分 |

命中任一類就走高風險流程，表中各類都沒命中的變更（文案、樣式、介面不變的內部重構）走標準流程。判準寫成資產類別而不是變更類型，是因為讀者在發版前握有的資訊正好是「這次改了什麼」——把它對照這張表是機械動作，而估計「這次風險高不高」需要的是已經做完的判斷。

判定要看實際命中而不是團隊的意圖。一次「只是加一個內部用的除錯端點」的變更命中對外暴露面那一類，因為可達來源由部署位置與路由規則決定，不由命名決定。

## 第二軸是回退能不能收回風險

功能風險的處置有一條標準退路：出事就回退。資安風險的可逆性不同——回退還原的是系統行為，不還原已經發生的暴露。

把一個內部端點誤開到公開網路的變更，回退會把端點關掉，而這段窗口內被列舉出的資源與被取走的資料不會隨之回收；把秘密寫進映像檔的變更，回退部署不會讓那個秘密回到未外流狀態，止血動作是撤銷與替換，能不能在時限內完成見 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)。

第二軸的判準因此是：這次變更若判斷錯了，回退能不能把風險收回來。收得回來的那類可以把驗證放在放行後的觀察窗口，用 [rollback condition](/backend/knowledge-cards/rollback-condition/) 定義收手的條件；收不回來的那類要在放行前驗證完，「出事再回退」對它不成立。兩軸的組合決定 gate 上要求的強度：命中任一類且回退收不回風險時，證據要在放行前補齊；命中而回退收得回來的那類，可以把一部分驗證移到放行後的觀察窗口，條件是收手的門檻與觀察者都已經指定。

## 必備控制與證據由命中的類別導出

必備控制清單由上一段命中的資產類別導出，不是一份固定的通用檢查表。命中的類別對應到承接的控制面，控制面的分類與主責見 [7.B1 防守控制面地圖](/backend/07-security-data-protection/blue-team/defense-control-map/)；動到認證與授權路徑的變更要驗的是授權邊界與高權限操作路徑，動到部署路徑的要驗的是 artifact 來源與部署身分，兩者的驗證方式與證據來源都不同。

證據的形式由 [evidence package](/backend/knowledge-cards/evidence-package/) 規格化（來源、時間窗、查詢入口、owner、資料品質、已知缺口、保留期）。gate 上最容易通過而實際沒有驗到的形態是證據對應的是欄位而不是機制——這一點在下方的兩條 chain 展開。

## 放行決策要寫成可回放的紀錄

放行要寫成一筆帶範圍的紀錄，而不是一個布林值。[Gate decision](/backend/knowledge-cards/gate-decision/) 的規格是同時寫出允許前進的範圍與被擋住的風險面，資安側的形態是「允許在只對內部網段開放的條件下上線，公開開放留待傳輸驗證完成」——這句話比「security review 通過」可操作，因為它讓下一個接手的人知道現在的狀態是什麼、以及什麼條件解除限制。

帶範圍限制的放行本身就是一筆風險例外。例外的協議欄位、期限與關閉條件在 [7.17 例外、凍結與 Tripwire](/backend/07-security-data-protection/security-exception-freeze-tripwire/) 有完整展開，機制見 [security exception](/backend/knowledge-cards/security-exception/) 與 [tripwire](/backend/knowledge-cards/tripwire/)；本章的責任只到一條時點要求：例外要在放行決策的同一刻建立，不是放行之後補登記。補登記的形態下，補償控制的生效時點晚於風險的生效時點，而那段落差不會出現在任何一份紀錄上。

## 高風險變更的階段節奏

高風險變更的流程分成以下幾段，每段的產出是下一段的輸入：

1. **預檢**：對照資產類別表判定是否命中、以及回退能不能收回風險。產出是風險等級與需要的證據清單。
2. **驗證**：依控制面執行對應的驗證，驗證分類（設計、技術、流程、放行、復盤）見 [7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/)。產出是證據本身。
3. **審查**：檢查證據對應的是機制而不是欄位。產出是通過、退回補證據、或縮小放行範圍三者之一。
4. **放行**：寫成 gate decision，帶範圍、擋住的風險面、owner 與收手條件。範圍有限制時同步建立例外紀錄。
5. **回寫**：把這次的判定回寫到判準本身。放行後出現的事故若屬於預檢判定為不命中的類別，缺的是判準的一列，回寫目標見 [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)。

回寫這一段最容易被省略，因為前面各段都有明確的產出物而它沒有。省略的後果是判準停在建立當時的形態，而變更的形態會持續長出新的類別。

## 從 Gate 通過到 control 實際驗證

Gate 通過代表流程跑完（風險等級、必備控制、證據與例外都有填），控制是否真在生產環境生效要靠兩條 chain：

- **Evidence chain**：證據列出的內容要對應到控制的實際機制，不是對應到欄位有沒有填。「TLS 已啟用」若以生產環境連得上 https 為證據，驗到的只是有一條 TLS 通道存在；該控制要證明的是加密套件、憑證有效期與 HSTS preload 三項，機制見 [7.5 傳輸信任與憑證生命週期](/backend/07-security-data-protection/transport-trust-and-certificate-lifecycle/)。
- **Re-evaluation chain**：tripwire 觸發、例外到期或外部事件都會讓上一次的判定過期，回到 [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/) 與對應主章重評估。

兩條 chain 都跑通，放行才是一次降低風險的決策。Gate 與控制的關係是流程層對實作層，兩層由證據的內容連起來——證據只證明欄位填了，兩層之間就是斷開的。

## 判讀訊號與下一步

| 判讀訊號                                               | 代表的缺口                                               | 下一步                                                                                                                                                                                                |
| ------------------------------------------------------ | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 發版條件只檢查功能測試與 SLO                           | gate 上沒有資安證據欄位，動到邊界的變更沿標準流程通過    | 依本章的資產類別表建立預檢；證據形式見 [evidence package](/backend/knowledge-cards/evidence-package/)、驗證分類見 [7.B3](/backend/07-security-data-protection/blue-team/security-control-validation/) |
| 例外的期限過了、放行狀態仍在生效                       | 重評估觸發器缺席，例外退化成永久狀態                     | 補 [tripwire](/backend/knowledge-cards/tripwire/) 的訊號與門檻；治理協議見 [7.14](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)                                   |
| 高風險變更的放行紀錄只有一個通過標記，查不到當時的依據 | 放行寫成布林值而不是 gate decision，事後無法回放判斷     | 依 [gate decision](/backend/knowledge-cards/gate-decision/) 的欄位補範圍、擋住的風險面與 owner；部署側的承接見 [05 部署平台](/backend/05-deployment-platform/)                                        |
| 放行後發生的資安事故，屬於預檢判定為不命中的類別       | 判準的資產類別清單缺一列，而下一次同型變更仍會判成不命中 | 回寫判準，路徑見 [7.24 資安事故如何回寫產品與架構](/backend/07-security-data-protection/security-incident-write-back-to-product-and-architecture/)                                                    |

## 驗收條件

gate 上的資安條件可用的驗收是三件事同時成立：預檢能用機械對照完成（不需要一輪人工風險討論）、必備控制由命中的類別導出（不是通用清單）、放行紀錄能讓事後的人重建當時的判斷依據。三者缺任一項時，gate 仍會產生通過紀錄，但那份紀錄無法在事故當天回答「當時憑什麼放行」。

## 必連章節

- [7.21 資安如何成為服務設計輸入](/backend/07-security-data-protection/security-as-service-design-input/)（gate 上要求的證據，來源是設計階段定的證據計畫）
- [7.17 例外、凍結與 Tripwire：資安決策如何避免過期](/backend/07-security-data-protection/security-exception-freeze-tripwire/)
- [7.14 資安治理例外與 Tripwire](/backend/07-security-data-protection/security-governance-exception-and-tripwire/)
- [7.B3 資安控制驗證](/backend/07-security-data-protection/blue-team/security-control-validation/)
- [7.18 資安控制面如何交接到部署與事故流程](/backend/07-security-data-protection/security-control-handoff-to-delivery-and-incident/)
- [7.23 資安與可靠性的共同控制面](/backend/07-security-data-protection/security-and-reliability-shared-controls/)
