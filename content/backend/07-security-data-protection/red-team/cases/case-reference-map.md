---
title: "7.R7.M 案例引用地圖（服務主題 -> 案例 -> workflow）"
date: 2026-04-24
description: "把服務主題連到完整案例體系，再連回 incident workflow 檢查點"
weight: 7179
---

這份地圖的責任是提供雙向引用路由：服務設計可以從主題找到案例，incident workflow 可以從流程步驟回查案例證據。

## 認證與權限邊界

這個主題處理身分入口、憑證信任鏈與高權限操作隔離。優先案例是 [Uber 2022](identity-access/uber-2022-mfa-fatigue/)、[Twilio 2022](identity-access/twilio-2022-social-engineering/)、[MGM 2023](identity-access/mgm-2023-identity-lateral-impact/)、[Storm-0558 2023](identity-access/microsoft-storm-0558-2023-signing-key-chain/)。

workflow 檢查點：高風險操作 step-up、異常身分即時隔離、跨租戶權杖異常升級。對應流程章節：[incident-report-to-workflow](../../../../08-incident-response/incident-report-to-workflow/)。

## 第三方整合與 token

這個主題處理供應商事件傳導與 token 收斂速度。優先案例是 [GitHub OAuth 2022](supply-chain/github-oauth-2022-token-supply-chain/)、[Okta + Cloudflare 2023](identity-access/okta-cloudflare-2023-support-supply-chain/)、[Cloudflare 2023](identity-access/cloudflare-2023-okta-token-follow-through/)、[Slack 2022](identity-access/slack-2022-token-compromise/)。

workflow 檢查點：第三方事件觸發全域 token 盤點、分域撤銷與輪替、供應商事件 playbook。對應流程章節：[incident-report-to-workflow](../../../../08-incident-response/incident-report-to-workflow/)。

## CI/CD 與更新供應鏈

這個主題處理 build 與更新信任鏈在事件中的凍結與恢復節奏。優先案例是 [SolarWinds 2020](supply-chain/solarwinds-2020-sunburst/)、[TeamCity 2023](supply-chain/teamcity-cve-2023-42793-ci-entrypoint/)、[CircleCI 2023](supply-chain/circleci-2023-secrets-rotation/)、[3CX 2023](supply-chain/3cx-2023-desktopapp-supply-chain/)、[XZ 2024](supply-chain/xz-backdoor-2024-open-source-supply-chain/)、[Log4Shell 2021](supply-chain/log4shell-cve-2021-44228-component-chain/)。

workflow 檢查點：部署凍結、artifact 驗證、分批輪替 secrets、版本回退與復測。對應流程章節：[incident-report-to-workflow](../../../../08-incident-response/incident-report-to-workflow/)。

## 邊界設備與外網入口

這個主題處理暴露面高與修補窗口短的組合風險。優先案例是 [MOVEit 2023](edge-exposure/moveit-2023-mass-exfiltration/)、[Ivanti 2024](edge-exposure/ivanti-2024-vpn-chain/)、[PAN-OS 2024](edge-exposure/panos-cve-2024-3400-edge-rce/)、[Fortinet SSL-VPN 2024](edge-exposure/fortinet-ssl-vpn-cve-2024-21762/)、[ProxyLogon 2021](edge-exposure/proxylogon-2021-exchange-entry-chain/)、[ProxyShell 2021](edge-exposure/proxyshell-2021-exchange-post-auth-chain/)、[Citrix 後續事件](edge-exposure/citrix-adc-2023-follow-on-session-risk/)。

workflow 檢查點：漏洞公告即隔離、分區修補、修補後狀態驗證、session 或憑證全域收斂。對應流程章節：[incident-report-to-workflow](../../../../08-incident-response/incident-report-to-workflow/)。

## 資料外送與營運回復

這個主題處理資料外送與營運停擺同步發生時的決策順序。優先案例是 [Snowflake 2024](data-exfiltration/snowflake-2024-credential-abuse/)、[LastPass 2022](data-exfiltration/lastpass-2022-backup-chain/)、[WS_FTP 2023](data-exfiltration/progress-wsftp-2023-file-service-breach/)、[GoAnywhere 2023](data-exfiltration/goanywhere-mft-2023-exfiltration-chain/)、[VMware ESXiArgs 2023](data-exfiltration/vmware-esxiargs-2023-ransomware-recovery-pressure/)、[Change Healthcare 2024](data-exfiltration/change-healthcare-2024-ops-impact/)。

workflow 檢查點：外送封鎖、受影響清單盤點、RTO/RPO 路由、回復優先級排序與跨組織通報。對應流程章節：[incident-report-to-workflow](../../../../08-incident-response/incident-report-to-workflow/)。

## 使用規則

1. 每個服務主題至少引用一篇同類型案例。
2. 每次引用至少帶出一個可操作 workflow 檢查點。
3. 每個 runbook 變更都回寫到對應案例與 workflow 章節，維持雙向可追溯。
