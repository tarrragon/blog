---
title: "Sigma：偵測規則生命週期素材"
tags: ["Sigma", "Detection Engineering", "Detection Rule"]
date: 2026-04-30
description: "把 Sigma detection format 轉成偵測規則欄位、誤報治理與維護流程素材"
weight: 72515
---

Sigma 的素材責任是提供跨 SIEM 的偵測規則描述語言。Sigma rules 使用 YAML 描述 logsource、detection、condition、falsepositives 與 level，適合支撐 detection-as-code 與規則維護流程。

## 來源定位

[Sigma Rules documentation](https://sigmahq.io/docs/basics/rules.html) 適合支撐「偵測規則需要明確資料源、條件、誤報說明與等級」的論點。[Sigma Conditions documentation](https://sigmahq.io/docs/basics/conditions.html) 則適合支撐「偵測邏輯需要可讀的 AND/OR/NOT 與 filter 表達」。

## 可引用論點

| 可引用論點              | 藍隊轉譯                                                                        |
| ----------------------- | ------------------------------------------------------------------------------- |
| 規則需要 logsource      | 7.B2 的 signal 要標明來源系統                                                   |
| 規則需要 condition      | 偵測邏輯要可 review、可測試                                                     |
| 規則需要 falsepositives | 誤報情境要進 triage 與調校流程                                                  |
| 規則需要 level          | [severity](/backend/knowledge-cards/incident-severity/) 與 escalation 可接到 08 |

## 後端服務轉譯

後端服務引用這張卡時，重點是把 detection rule 當成生命週期資產。每條規則都需要來源、觸發條件、測試事件、誤報說明、調校紀錄、owner 與退場條件。

## 引用限制

Sigma 適合支撐規則格式與維護欄位，實際查詢語法、資料品質與 alert 噪音要依 SIEM、log schema 與服務流量特性調校。
