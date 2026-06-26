---
title: "HashiCorp Vault"
date: 2026-06-26
description: "機密管理系統，集中存放密碼、API key、TLS 私鑰，提供存取控制、稽核和自動輪替"
weight: 48
tags: ["infra", "knowledge-cards"]
---

HashiCorp Vault 是機密管理系統，集中存放和控制對敏感資料（密碼、API key、TLS 私鑰、資料庫憑證）的存取。每一次讀取都有稽核紀錄、每一份機密都有存取政策、憑證可以設定自動輪替。

## 概念位置

Vault 在 infra 裡負責「機密值的集中管理」。跟直接把密碼寫在環境變數或設定檔的差別是：Vault 提供存取控制（只有被授權的身分能讀特定 secret）、稽核軌跡（誰在什麼時候讀了什麼）、以及動態 secret（每次請求產生一組臨時憑證、用完即銷毀）。

連網環境通常用雲端的 secret manager（AWS Secrets Manager、GCP Secret Manager）。斷網環境沒有雲端服務可用、Vault 是 self-hosted 的替代方案。

## 可觀察訊號

系統需要 Vault 的訊號是：多個服務共用同一組資料庫密碼且密碼寫在設定檔裡、沒有人知道上次輪替是什麼時候、或是稽核要求「列出誰能存取哪些機密」而答不出來。

## 設計責任

使用 Vault 時要決定：unseal 方式（連網用 cloud auto-unseal、斷網用 Shamir's secret sharing——需要 N 把 key 中的 M 把才能解鎖）、storage backend（Consul、PostgreSQL、filesystem）、認證方式（人用 LDAP/OIDC、機器用 AppRole）、secret engine 的選擇（KV 存靜態值、PKI 簽發憑證、database 動態產生 DB 帳號）。

## 鄰卡

- [IAM](/infra/knowledge-cards/iam/)：Vault 的存取政策跟 IAM 的 policy 概念類似
- [SSL/TLS](/infra/knowledge-cards/ssl-tls/)：Vault 的 PKI engine 可以當內部 CA 簽發憑證
