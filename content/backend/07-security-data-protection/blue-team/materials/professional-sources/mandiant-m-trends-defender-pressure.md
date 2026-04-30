---
title: "Mandiant M-Trends 2025：防守現場壓力素材"
tags: ["Mandiant", "M-Trends", "Threat Intelligence"]
date: 2026-04-30
description: "把 Mandiant M-Trends 2025 轉成藍隊現場壓力與演練素材"
weight: 72516
---

Mandiant M-Trends 2025 的素材責任是提供防守現場壓力。Mandiant 以第一線調查經驗整理攻擊者如何提升複雜度、繞過偵測、利用 edge device 與延長停留時間。

## 來源定位

[M-Trends 2025](https://cloud.google.com/blog/topics/threat-intelligence/m-trends-2025) 適合支撐「防守設計需要面對攻擊者繞過與低可見度資產」的論點。文章提到攻擊者會使用 zero-day、edge devices、proxy networks、custom malware ecosystems 與 obfuscation 來延長存活時間。

## 可引用論點

| 可引用論點                | 藍隊轉譯                            |
| ------------------------- | ----------------------------------- |
| Edge device 可見度壓力    | 7.3 與 7.B2 需要補入口與管理面訊號  |
| 客製化 malware 壓力       | 7.B3 需要用行為與證據鏈驗證控制面   |
| Proxy 與 obfuscation 壓力 | 7.B4 演練要包含低信心訊號與關聯分析 |

## 後端服務轉譯

後端服務引用這張卡時，重點是把高階威脅趨勢轉成可演練情境。典型情境包含管理入口異常、身份來源異常、低頻資料外送、[artifact](/backend/knowledge-cards/artifact-provenance/) 來源偏移與偵測訊號延遲。

## 引用限制

Mandiant 適合支撐現場壓力與威脅趨勢，控制面設計仍要結合自身服務資料源、攻擊面、部署拓撲與事故承接能力。
