---
title: "Reddit"
date: 2026-05-01
description: "Reddit Pi Day 2023 k8s 升級事故"
weight: 22
---

Reddit 2023 Pi Day（3/14）的 314 分鐘事故是 Kubernetes 升級導致的事故、揭露 k8s 升級在大規模生產環境的隱性風險。Reddit engineering blog 公開 post-mortem 細節豐富。

## 規劃重點

- Kubernetes 升級風險：minor version 升級的 breaking change
- 升級回滾困境：為何 k8s control plane 不能直接降版
- 大規模 stateful workload 的特殊性：pod 重排對狀態服務的衝擊
- 內部 IR 流程：Reddit 的 IR commander / scribe 結構公開度

## 預計收錄事故

| 年份    | 事故                     | 教學重點                            |
| ------- | ------------------------ | ----------------------------------- |
| 2023-03 | Pi Day k8s 升級 314 分鐘 | k8s upgrade、control plane 回滾困境 |

## 案例定位

Reddit 這個案例在講的是 Kubernetes 升級如何在大規模 stateful 工作負載上拉長事故。讀者先看懂控制平面升級、回滾限制與狀態服務的特性，再把 Pi Day outage 當成升級風險的具體樣本。

## 判讀重點

當 control plane 進行升級時，最先要保住的是回滾空間與資料完整性。當 pod 重排碰到 stateful workload 時，恢復節奏就不能只看節點健康，而要看整個狀態層是否真的穩回來。

## 可操作判準

- 能否判斷問題是在 k8s 升級還是 workload 本身
- 能否把回滾限制與控制平面風險講清楚
- 能否辨識 stateful workload 的額外恢復成本
- 能否把 IR commander / scribe 的流程用在對外說明

## 與其他案例的關係

Reddit 和 GitHub、Heroku 的交集在於，它們都會把平台層變更直接反映成使用者可見的 outage。這頁最值得和 GCP 一起看，因為 Kubernetes 升級與 control plane 回滾問題，能很好地補足「服務自己沒有寫錯，但平台還是會出事」這個視角。

## 代表樣本

- 2023-03 Pi Day 314 分鐘事故是 k8s 升級與 stateful workload 互相放大的樣本。
- 這類事件特別能看出 control plane 回滾為何比一般服務回滾更麻煩。
- IR commander / scribe 讓對外資訊流有固定節奏。
- k8s 升級風險和其他平台事故頁可以互相對照。
- stateful workload 的 pod 重排會把效能恢復拉長。
- control plane rollback 的限制讓升級決策必須更早做完。
- kube upgrade 不是單純版本更新，而是整個平台控制面的變更。
- stateful service 的 cold start 會把恢復時間拉長到使用者可感知的程度。

## 引用源

- [Reddit Status](https://www.redditstatus.com/)：Reddit 狀態頁與 incident history。
- [Reddit Status - Incident History](https://www.redditstatus.com/history)：歷史事故與 uptime 檢視。
- [Reddit Status - API](https://www.redditstatus.com/api)：status page API 文件。
- [The Search for Better Search at Reddit](https://redditinc.com/blog/the-search-for-better-search-at-reddit)：Reddit 工程內容總入口之一，補基礎工程脈絡。
