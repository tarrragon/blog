---
title: "4.C21 Tail sampling：採樣壓力下保留 error 與尾延遲樣本"
date: 2026-07-04
description: "head sampling 在資訊不全時就決定去留、高錯誤率下丟掉你要的 error trace；tail sampling 看完整條才依 policy 保留高診斷價值樣本"
weight: 21
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供觀測系統在採樣壓力下優雅降級的做法：不是無差別丟資料、而是保住診斷價值最高的樣本。

## 觀察

OpenTelemetry Collector Contrib 的 tail sampling processor：「The tail sampling processor samples traces based on a set of defined policies」。status_code 政策「Sample based upon the status code (OK, ERROR or UNSET)」（可設 `status_codes: [ERROR]` 只保留 error trace）；latency 政策「Sample based on the duration of the trace. The duration is determined by looking at the earliest start time and latest end time」（需整條 trace 才算得出、因此決策發生在 trace 完成後）。processor 另有過載徵兆 metric `sampling_trace_dropped_too_early`（in-memory trace 超過 `num_traces` 時的降級失敗）。

## 判讀

head sampling 在 trace 開頭、資訊不全時就隨機決定去留、高錯誤率下要保留的那條 error / 慢 trace 常被丟掉。tail sampling 把決策延到整條 trace 的 span 到齊之後、才依 policy（ERROR 狀態、超過延遲門檻）決定保留 —— 這是觀測系統在採樣壓力下的優雅降級：資源不夠時有選擇地保住錯誤與尾延遲這些事故最需要的樣本。`sampling_trace_dropped_too_early` 本身是「觀測系統過載」的一手判讀點：tail sampling 也有自己的記憶體上限、超過時降級會失敗。

## 對應大綱

觀測共命運章「優雅降級」段（採樣壓力下保留高價值樣本）。

## 引用源

- [Tail Sampling Processor（OpenTelemetry Collector Contrib）](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/tailsamplingprocessor/README.md) — 一手官方。已 WebFetch 驗證。

## 二手來源與狀態標注

README 開頭定義句未明講「決策發生在 trace 完成後」、由 latency policy 的「earliest start / latest end」間接佐證 —— 要斬釘截鐵引「決策晚於 head」可補 opentelemetry.io sampling 概念頁作第二一手源。
