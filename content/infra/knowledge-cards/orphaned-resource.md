---
title: "Orphaned Resource（孤兒資源）"
date: 2026-10-26
description: "刪掉或停掉一台雲端主機之後帳單還在、免費額度被不知名的磁碟佔著，或要盤點一個帳號裡哪些磁碟、IP、快照已經沒有主機在用時"
weight: 74
tags: ["infra", "knowledge-cards", "cloud", "cost"]
---

孤兒資源（orphaned resource）是雲端帳號裡，原本為某一台主機或某一項服務建立、而那台主機已經刪除或停用之後仍然存在的資源：沒有掛在任何主機上的磁碟、沒有附在任何主機上的保留 IP、主機刪除後留下的快照與備份、後面已經沒有主機的負載平衡器與 NAT 閘道。它們在對這類資源收費的業者帳單上各自計費、各自佔用免費額度，而主控台的主機列表裡看不到它們。跟它相關的是 [Deletion Protection](/infra/knowledge-cards/deletion-protection/)（刪除保護）：刪除保護防的是該留的資源被誤刪，孤兒資源是該刪的資源沒有刪。

同名而所指不同的兩個詞：Linux 的孤兒程序（orphan process）是父程序先結束、被 PID 1 收養的程序；套件管理器的孤兒套件是當初作為相依被裝進來、而依賴它的套件已經移除的套件（`pacman -Qtd`、`dnf autoremove` 處理的對象）。本卡講的是雲端帳號裡的資源。

## 概念位置

孤兒資源的成因是建立與刪除的範圍不對稱：建立主機的精靈一次建出主機、開機磁碟、公開 IP，有時連網路一起建；刪除時每一項的去留各有預設，業者為了避免誤刪資料，常把磁碟（AWS 的 [EBS](/infra/knowledge-cards/ebs/) 這類區塊磁碟）的預設設成保留（Oracle Cloud 終止主機時開機磁碟預設保留）。各家的預設與欄位名稱見 [磁碟：開機磁碟與區塊磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)〈刪除（終止）主機時開機磁碟的預設去留〉；暫停一台主機時逐項要決定保留或刪除的資源，見 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/)〈暫停期間仍在計費的資源〉。帳單層看到的「被遺忘的資源」是同一件事，見 [計費模式理解](/operations/08-cost-management/billing-models/)〈隱藏成本：帳單上的意外〉。

DNS 層有一個對應的情形：主機與 IP 都刪了，DNS 紀錄還指著那個位址，這是懸空 DNS 的成因，見 [10.6 命名空間與網域的處置：續約、名稱保留與回收、懸空 DNS](/backend/10-system-evolution/namespace-and-domain-disposition/)〈懸空 DNS 與子網域接管〉。孤兒資源的後果是多付錢與佔額度；懸空 DNS 的後果是業者把位址分給別的客戶之後，網域的流量送到別人的主機。

## 可觀察訊號

- 主機都刪了，帳單上的區塊儲存、公開 IP 或快照費用沒有歸零。
- 免費帳號建新主機時回報區塊儲存額度不足，而執行中的主機加起來沒有用到那麼多。
- 主控台的磁碟列表裡有狀態是「未掛載」的磁碟（AWS 的 EBS 叫 `available`），名稱裡帶著已經不存在的主機名。
- 公開 IP 列表裡有沒有附在任何主機上的保留 IP。

## 設計責任

孤兒資源的處理分在建立、刪除與盤點三個時間點：

- **建立時記下歸屬**：替主機與它的附屬資源加上同一組標籤（專案名、用途、建立者），刪除主機之後依標籤查得出還剩哪些資源；沒有標籤的磁碟只能靠名稱與建立時間猜，猜錯就刪到還在用的資料。
- **刪除時逐項決定**：終止主機的對話框裡，開機磁碟要不要一起刪是一個選項，選了保留就代表之後要回來處理它；保留 IP 與快照不在那個對話框裡，要另外到各自的列表刪。
- **定期盤點**：依資源類型列出沒有附在任何主機上的項目，跟標籤比對；確認不再需要之後才刪，磁碟與快照刪了就救不回來，所以刪之前先確認裡面的資料有沒有另外的備份。
- **用 IaC 管理時**：[Infrastructure as Code (IaC)](/infra/knowledge-cards/iac/) 的 [State（IaC 狀態檔）](/infra/knowledge-cards/state/) 記著它建過的資源，`terraform destroy` 會連同附屬資源一起刪；在主控台手動建、沒有寫進狀態檔的資源不在它的範圍內，destroy 之後照樣留在帳號裡。主控台手動改過 IaC 建的資源，則是 [Drift（設定漂移）](/infra/knowledge-cards/drift/)。

## 鄰卡

- [Deletion Protection](/infra/knowledge-cards/deletion-protection/)
- [EBS](/infra/knowledge-cards/ebs/)
- [Drift（設定漂移）](/infra/knowledge-cards/drift/)
