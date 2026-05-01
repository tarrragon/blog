---
title: "6.18 Reliability Metrics Governance"
date: 2026-05-01
description: "DORA / SPACE / CFR 等可靠性指標的選用、量測與治理"
weight: 18
---

## 大綱

- 為何指標需要治理：選錯指標會優化錯方向、Goodhart's law 風險
- DORA 四指標：deploy frequency、lead time、change failure rate、MTTR
- SPACE：Satisfaction、Performance、Activity、Communication、Efficiency 補 DORA 缺的人因
- 指標選用：團隊發展階段不同、指標重點不同（startup / scale / mature）
- baseline 對齊：跟同產業 / 同團隊大小對標、不是抄業界數字
- 反 gaming：指標被優化到失去意義時的偵測（如 deploy 拆碎只為衝頻率）
- 跟 [6.6 SLO](/backend/06-reliability/slo-error-budget/) 的差異：SLO 是商業承諾、6.18 是工程能力
- 跟 [6.8 release gate](/backend/06-reliability/release-gate/) 的整合：CFR 是 gate 健康度
- 反模式：指標當 KPI 強制達成、團隊 gaming；只看 4 指標忽略品質；指標跨團隊比較強制排名

## 判讀訊號

- 工程團隊優化指標數字、實際品質下降
- 指標數字好看、客戶投訴與事故未減
- 跨團隊強制排名、團隊間互不分享經驗
- DORA 採集靠人工、指標滯後一個月以上
- 指標無 owner、半年無人 review

## 交接路由

- 06.6 SLO：商業承諾層的指標
- 06.8 release gate：CFR 是 gate 健康度訊號
- 04.6 SLI/SLO：跟訊號層的對應
- 08.5 postmortem：MTTR 計算的事件來源
