---
title: "5.5 攻擊者視角（紅隊）：平台與入口弱點判讀"
date: 2026-04-24
description: "以概念層判讀部署平台弱點，聚焦入口、生命周期、設定與交付節奏"
weight: 5
---

本章的責任是把部署平台的弱點判讀維持在概念上限。核心輸出是平台問題地圖、案例對照與交接條件，讓實作前決策可先對齊。

## 服務環節問題地圖

| 環節 | 主要問題 | 注意事項 | 優先案例 |
| --- | --- | --- | --- |
| 入口暴露面 | 入口分級與實際可達範圍不一致 | 入口清單與責任鏈要先對齊 | [MOVEit 2023](../07-security-data-protection/red-team/cases/edge-exposure/moveit-2023-mass-exfiltration/) |
| 生命周期訊號 | readiness、draining、shutdown 節奏不一致 | 平台合約要先定義再驗證 | [Ivanti 2024](../07-security-data-protection/red-team/cases/edge-exposure/ivanti-2024-vpn-chain/) |
| 設定與密鑰下發 | 設定漂移與權限擴張同時發生 | 高風險設定要進 release gate，並分離 [management plane](../knowledge-cards/management-plane/) | [F5 BIG-IP 2023](../07-security-data-protection/red-team/cases/edge-exposure/f5-bigip-cve-2023-46747-auth-bypass/) |
| 交付切換節奏 | 回滾與切換條件不清晰 | 先定停損條件再定交付速度 | [TeamCity 2024](../07-security-data-protection/red-team/cases/supply-chain/teamcity-2024-cve-27198-27199-auth-path-traversal/) |

## 案例對照表（情境 -> 判讀 -> 注意事項 -> 路由章節）

| 情境 | 判讀 | 注意事項 | 路由章節 |
| --- | --- | --- | --- |
| 外網可達入口在發版後增加 | 入口分級與交付節奏存在脫鉤 | 入口盤點要成為交付前條件 | [5.3 Load Balancer Contract](../05-deployment-platform/load-balancer-contract/) |
| readiness 通過但實際流量錯誤率上升 | 生命周期合約與流量模型不一致 | 探針、draining、shutdown 要同批驗證 | [6.5 驗證缺口弱點判讀](../06-reliability/attacker-view-validation-risks/) |
| 設定異動與異常事件同時出現 | 設定漂移可能已跨越安全邊界 | 設定審查與責任追蹤要同步維護 | [8.5 復盤與改進追蹤](../08-incident-response/post-incident-review/) |

## 到實作前的最後一層

本章在概念層回答的是平台風險判讀與交接節奏。當討論進入 Kubernetes 欄位、LB 規則、系統服務參數或腳本配置時，就代表已進入實作層。
