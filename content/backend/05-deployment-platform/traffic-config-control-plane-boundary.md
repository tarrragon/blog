---
title: "5.7 Traffic、Config 與 Control Plane Boundary"
date: 2026-05-11
description: "說明流量、設定、secret、service discovery 與管理面如何分責任與回退。"
weight: 7
tags: ["backend", "deployment", "traffic", "control-plane"]
---

Traffic、config 與 control plane boundary 的核心責任是把平台切換中的資料面與控制面分開。進入 Kubernetes、ELB、Envoy、Consul 或 Terraform 前，讀者需要先知道流量、設定、secret、service discovery 與管理面各自有不同風險與回退方式。

## Traffic Boundary

Traffic boundary 的責任是決定 request 如何進入服務、如何分流、如何回退。它包含 load balancer、routing rule、health check、sticky session、timeout 與 drain。

流量切換要能回答三個問題：哪一批 request 會到新版本、失敗時如何停止擴批、舊版本是否仍能承接回退流量。這三個答案明確後，canary 才能從比例設定變成可回退策略。

Traffic boundary 的判讀重點是 customer impact 如何被分批限制。小比例 canary、區域切流、tenant 切流與 route rule 都是不同切換單位；切換單位越清楚，rollback window 越容易被驗證。

## Config Boundary

Config boundary 的責任是決定設定如何下發、如何生效、如何回退。[config rollout](/backend/knowledge-cards/config-rollout/) 和應用版本不一定同步，因此要保留相容窗口。

高風險設定包含 payment provider endpoint、feature flag、rate limit、routing rule、timeout 與 fallback policy。這些設定變更可能不需要新 image，卻能改變 production 行為，因此要進 release gate。

## Secret Boundary

Secret boundary 的責任是讓 credential、token、certificate 與 machine identity 可輪替、可稽核、可回退。Secret 變更同時影響平台、應用與外部依賴，應使用比普通 config 更嚴格的 evidence 與 rollback window。

Secret rollout 要回答版本相容、雙軌驗證、舊 secret 撤除時間與失敗回退。這裡要接到 [7.27 Credential Rotation with Scoped Evidence](/backend/07-security-data-protection/credential-rotation-scoped-evidence/)。

## Service Discovery Boundary

Service discovery 的責任是維持可用 endpoint 集合。它回答服務應該連到哪些實例；業務設定與版本正確性則分別交給 config boundary 與 rollout gate。

Discovery 失準常見於 rollout、擴縮容與區域故障。判讀時要拆成註冊時序、健康判斷、DNS/registry 新鮮度與 fallback 存活時間。

## Control Plane Boundary

[management plane](/backend/knowledge-cards/management-plane/) 的責任是管理設定、策略、部署與路由規則。Control plane 變更會影響大量服務，因此需要更嚴格的 evidence、gate 與 decision log。

Control plane 事故常見於規則推送、routing 誤配、secret 下發失敗與 registry 異常。這類事故要先保留 decision timeline，避免事後只看到資料面錯誤率。

## 選型前判準

平台選型前要先回答：

1. 哪些變更屬於 traffic，哪些屬於 config，哪些屬於 secret。
2. 每種變更是否能分批、暫停與回退。
3. Discovery 失準時是否有可控 fallback。
4. Control plane 變更是否有 audit、owner 與 blast radius 限制。

這些答案決定後續要比較 load balancer、service mesh、secret manager、service registry 或 deployment controller 的能力。

## 實體服務討論承接點

實體平台文章要承接本篇的 traffic、config 與 control plane boundary。ELB、nginx、Envoy、service mesh、Consul、Kubernetes controller、secret manager 或 Terraform 的比較，要先分清它們是在資料面接流量、在控制面改規則，還是在設定面下發狀態。

若主問題是流量切換，後續文章要比較 routing rule、weight、health check、drain 與 rollback。若主問題是設定與 secret，後續文章要比較 rollout、audit、rotation 與相容窗口。若主問題是 control plane 風險，後續文章要比較 blast radius、approval、observability 與 incident decision log。

## 下一步路由

要把流量邊界接到實際 LB 合約，接著讀 [5.3 load balancer 合約](/backend/05-deployment-platform/load-balancer-contract/)。要把 control plane 決策寫入事故流程，接著讀 [8.23 Control Plane Decision Log and Write-back](/backend/08-incident-response/control-plane-decision-log-write-back/)。
