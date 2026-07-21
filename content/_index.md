---
title: "首頁"
description: "Tarragon blog 首頁，整理教學系列、工作筆記、事後檢討與工程方法論"
tags: ["首頁", "教學", "工程筆記"]
---

龍蒿又稱龍艾，具有類似大茴香的香甜芳香，帶有胡椒的辛辣感。
適合用於烹調肉類、魚類、雞肉、蛋類，以及製作醬料、沙拉醬等。
芳香也能用於製作茵蒿醋，增添食物風味，全聯有進。

目前工作上開發flutter，前端後端也都有寫過。

- **blogroll**：我追的部落格
- [開發心得](/record/)：目前開發中的sideproject
- [工作筆記](/work-log/)：開發遇到的狀況
- [事後檢討](/report/)：開發過程的事後檢討、應該怎麼做、沒這樣做的麻煩
- [Skills](/skills/)：寫作方法論與其他可重用的方法 skill
- **資訊分享**：撿到的文章或者資訊
- [TIL 學習筆記](/til/)：工程之外學到的小知識 — 單字字源、概念由來、冷知識
- [macOS](/macos/)：macOS 系統架構、磁碟管理、開發環境設定
- [其他](/other/)：沒想到分類的東西

## 教學系列

第一次要把服務放上線、不知道從哪個系列開始的，先看 [服務上線的業界常識地基](/going-live/)——它把各系列共同的入門地基（部署是什麼、主機怎麼選、域名與 HTTPS、自架 vs 託管、備份）串成一條線，再往上路由到 Backend / Infra / DevOps 的深度內容。

- [服務上線的業界常識地基](/going-live/)：從本機到上線的新手 on-ramp，把各系列共同假設的地基串成一條路徑
- [Python 維護指南](/python/)：入門教學，以 Hook 系統為範例
- [Python 進階指南](/python-advanced/)：深入內部機制與擴展開發
- [Go 維護指南](/go/)：理解 Go 語言精神與核心開發能力
- [Go 進階指南](/go-advanced/)：深入 Go 並發、WebSocket、runtime 與服務架構
- [Flutter 實戰指南](/flutter/)：Dart 型別設計、狀態與渲染、測試策略與工具鏈，從實際專案 case 抽出判準
- [DDD 領域驅動設計指南](/ddd/)：領域模型的理論與判準層 — entity 判準、不變式強制層次、稽核軌跡，實作限制路由到各語言模組
- [Backend 服務實務指南](/backend/)：整理資料庫、快取、訊息佇列、觀測、部署與可靠性驗證等跨語言後端能力
- [DevOps 全景：軟體交付生命週期](/devops/)：把 Infra（地基）→ CI/CD（管線）→ 運行期維運三階段串成一條交付生命週期的導覽入口，不確定問題進哪個系列先看這裡
- [CI/CD 教學](/ci/)：整理驗證、建置、發布 gate 與不同部署場域的流程差異
- [本地 LLM 寫 code 實務指南](/llm/)：在 Apple Silicon Mac 上跑本地 LLM、整合 VS Code 寫 code 的最短可行路徑
- [商業概念與策略分析](/business/)：整理商業模式、單位經濟、競爭護城河等術語卡片，並用 WRAP 框架拆解具體市場案例
- [Testing 測試策略](/testing/)：三層測試分層、mock 遮蔽機制、protocol integration test、客戶端可觀測性，從終端機 app 的實機測試教訓出發
- [UX Design 畫面設計](/ux-design/)：畫面狀態矩陣、gate fallback、輸入機制、錯誤回復、導航模式，mobile app 的 UX 設計判斷
- [Monitoring 監控體系](/monitoring/)：四類事件分類、SDK 設計、collector 架構、商業方案比較、資安與隱私、行為資料商業利用
- [運行期維運](/operations/)：負載平衡、水平擴展、流量管控、服務探活、容量規劃、高可用、突發流量應對、成本管理
- [Infra 基礎設施建置指南](/infra/)：從零循序漸進把雲端基礎設施做起來 — IaC、身分憑證、網路地基、環境分離、核心服務、可觀測性、自動化 review、治理習慣與組織推動
- [Linux 完整指南](/linux/)：從零安裝 Linux、出問題怎麼除錯、各情境的工具選擇（CLI / 圖形桌面 / 遠端），以及用 dotfile 管理整個工作環境 — 安裝、除錯、工具選單與 dotfile 管理四大子分類
- [免伺服器自動化實務指南](/automation/)：不租主機、用免費雲端服務給靜態站補上動態能力 — 以「幫 GitHub Pages blog 做流量統計」為貫穿案例，教 Google Apps Script + Sheets 的膠水層、beacon、Sheets 當資料庫、排程彙總與配額安全
- [神經多樣性](/neurodiversity/)：為神經多樣性讀者（ADHD、自閉、需求迴避）設計 AI 與文件輸出 — 拆解三個真實 skill 各自解什麼問題、抽出共用的輸出設計方法論，再整合成單一可組合的 skill

---
