---
title: "Apache JMeter"
date: 2026-05-01
description: "老牌 load test 工具、GUI + plugins"
weight: 5
tags: ["backend", "reliability", "vendor"]
---

JMeter 是 Apache 出品的老牌 load test 工具、承擔三個責任：GUI-driven test plan 設計、多 protocol sampler（HTTP / JDBC / JMS / FTP / mail）、plugins 生態廣 + 企業環境普及。設計取捨偏向「GUI 易上手 + 既有測試資產治理 + 多 protocol」、跟 code-first（k6 / Gatling）的取捨在 dev workflow 跟 version control 友善度。

## 本章目標

讀完本章後、你應該能：

1. 用 GUI 設計 test plan（thread group / sampler / listener / assertion）
2. 跑 non-GUI mode 給 CI
3. 用 Distributed mode（master / slave）擴張 VU
4. 用 JMeter Plugins Manager 加擴展
5. 評估 JMeter vs 現代 CLI-first（k6 / Gatling / Locust）的選用

## 最短路徑：5 分鐘把 JMeter 跑起來

```bash
# 1. 安裝
# TODO: brew install jmeter / 下載 zip

# 2. GUI 設計 .jmx
# TODO: 開 jmeter GUI、加 Thread Group / HTTP Sampler / Listener

# 3. CI 跑 non-GUI mode
# TODO: jmeter -n -t test.jmx -l result.jtl -e -o report/
```

## 日常操作與決策形狀

### Test plan 結構

子議題：

- Thread Group（VU + ramp-up + loop count）
- Sampler（HTTP / JDBC / JMS / FTP / Java Request）
- Listener（aggregate report / view tree / graph）
- Assertion（response / duration / size）

### Non-GUI mode for CI

子議題：

- `-n` non-GUI
- `-t` test file / `-l` log file
- `-e -o` 產生 HTML dashboard
- Exit code 0 / 1（搭配 backend listener / assertion）

### Distributed testing

子議題：

- Master / slave 配置
- RMI port 設定
- Result aggregation 在 master

## 進階主題（按需閱讀）

### Plugins Manager

子議題：

- jmeter-plugins.org plugins
- 常用：PerfMon / Dummy Sampler / Custom Thread Groups / WebSocket
- 安裝管理：Plugins Manager 安裝後可 UI 管

### Recording controller

子議題：

- HTTP(S) Test Script Recorder
- Browser proxy 設定
- 適合：快速錄製 user flow

### CSV data set / parameterization

子議題：

- CSV Data Set Config
- 各 thread 取不同資料
- 適合 data-driven test

### CI / Jenkins integration

子議題：

- Jenkins JMeter plugin
- Performance plugin（trend analysis）
- 對應 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)

### 既有 .jmx 資產治理

子議題：

- XML 不友善 git diff
- 大 test plan 可讀性差
- 改用 module 拆 + Test Fragment
- 對應企業遷移到 k6 / Gatling 評估

## 排錯快速判讀

### High VU 起不來

操作原則：JVM heap 不夠 / GUI 模式有限制（永遠 non-GUI for production load）。

### Listener 拖慢

操作原則：View Results Tree 記錄太多 → 改 simple data writer / disable detail。

### Distributed RMI 連不上

操作原則：firewall + RMI port 不對。

### Assertion noise

操作原則：assertion failed 多但實際 OK → response time / size 設過嚴。

## 何時改走其他服務

| 需求形狀              | 改走                                                                                            |
| --------------------- | ----------------------------------------------------------------------------------------------- |
| Code-first / CI-first | [k6](/backend/06-reliability/vendors/k6/) / [Gatling](/backend/06-reliability/vendors/gatling/) |
| Python                | [Locust](/backend/06-reliability/vendors/locust/)                                               |
| Cloud managed         | BlazeMeter / Octoperf / Tricentis NeoLoad                                                       |
| Browser flow          | Playwright / Cypress / k6 browser                                                               |
| Capacity planning     | [09 performance capacity](/backend/09-performance-capacity/)                                    |

## 不在本頁內的主題

- 完整 plugins 列表
- BeanShell / Groovy scripting
- JMeter internal architecture

## 案例回寫

**待補 JMeter customer case**：企業內部 JMeter 大規模採用案例、JMeter → k6 遷移案例。

## 下一步路由

- 上游概念：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)
- 平行 vendor：[k6](/backend/06-reliability/vendors/k6/)、[Gatling](/backend/06-reliability/vendors/gatling/)
- 下游能力：[09 performance capacity](/backend/09-performance-capacity/)
