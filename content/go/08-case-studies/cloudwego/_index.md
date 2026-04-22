---
title: "8.9 ByteDance / CloudWeGo：微服務基礎設施"
date: 2026-04-23
description: "看 Go 如何從單一服務語言沉澱成微服務治理與框架"
weight: 9
---

CloudWeGo 是理解 Go 在大型公司內部如何演化成基礎設施層的好案例。官方介紹指出，它是 ByteDance Infrastructure Service Framework 團隊開源的 middleware 集合，核心關注是高性能、高擴展性、高可靠性與微服務溝通與治理。

## 你應該看什麼

- [CloudWeGo About](https://www.cloudwego.io/about/)
- [CloudWeGo: a leading practice for building enterprise cloud native middleware](https://www.cloudwego.io/blog/2023/06/15/cloudwego-a-leading-practice-for-building-enterprise-cloud-native-middleware/)
- [An Article to Learn About ByteDance Microservices Middleware CloudWeGo](https://www.cloudwego.io/blog/2022/03/25/an-article-to-learn-about-bytedance-microservices-middleware-cloudwego/)

## 這個案例告訴我們什麼

1. Go 可以從單一服務語言，進一步變成微服務平台語言。
2. 大型服務常會把 RPC、HTTP、networking、serialization 拆成不同 middleware。
3. Go 的簡潔語法與高性能 runtime 很適合做基礎設施層。

## 可對照的公開原始碼

- [cloudwego/kitex](https://github.com/cloudwego/kitex)
- [cloudwego/hertz](https://github.com/cloudwego/hertz)
- [cloudwego/netpoll](https://github.com/cloudwego/netpoll)

這三個 repo 很適合對照第 4、6、7 模組，尤其是高併發控制、HTTP 邊界與 ports/adapters 的組織方式。

