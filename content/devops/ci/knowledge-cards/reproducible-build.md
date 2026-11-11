---
title: "Reproducible Build（可重現建置）"
date: 2026-10-22
description: "要確認一個建置產物沒有在建置過程中被改過、或建置主機被入侵之後要判斷入侵期間的產物能不能保留時，查同一份原始碼能否建出逐位元相同的產物"
tags: ["CI", "build", "supply-chain", "knowledge-card"]
weight: 27
aliases: ["/ci/knowledge-cards/reproducible-build/"]
---

可重現建置（reproducible build）是同一份原始碼在相同的建置環境與指令下，建出逐位元相同的產物的性質。具備這個性質時，任何人重新建置一次、比對雜湊值，就能確認手上的 [Artifact](/devops/ci/knowledge-cards/artifact/) 確實出自那份原始碼，沒有在建置過程中被植入原始碼以外的程式。

## 跟其他概念的關係

建置不可重現的常見成因是 [Artifact](/devops/ci/knowledge-cards/artifact/) 裡帶進了每次都不同的資訊：建置時間戳、檔案的排列順序、建置主機的路徑、沒有固定版本的相依套件。消除這些成因之後，雜湊比對才有意義。它與產物的來源證明（[Artifact Provenance](/backend/knowledge-cards/artifact-provenance/)）互補：來源證明記錄產物宣稱出自哪裡，可重現建置讓第三方能用重新建置驗證這個宣稱。CI 對可重播性的最低要求見 [Artifact 與可重播性](/devops/ci/artifact-reproducibility/)。

## 可觀察訊號與例子

CI 建置主機被入侵後，團隊從已審查的原始碼重新建置入侵期間的每一個產物：建置可重現時，雜湊值與先前產物相同的可以保留，不同的就是被改過；建置不可重現時，雜湊值本來就不會相同，只能把入侵期間的產物全部撤下、改用重建的版本。

## 判斷條件與後果

建置是否可重現，看的是輸入與產物裡是否帶著每次都不同的資訊。基礎映像用 tag 而不是 digest 指定、相依套件沒有固定版本時，同一份原始碼在不同時間建置拿到的是不同的輸入；產物裡帶著建置時間戳或主機路徑時，輸入相同，雜湊值也每次不同。這兩種情形下，重新建置比對雜湊得不到結論，建置主機被入侵後分不出哪些產物被改過，只能把入侵期間的產物全部撤下。建置設定的任何一次改動都可能重新帶進這類資訊，而建置照常成功，所以可重現性要靠定期抽樣重建比對來確認仍然成立。入侵後的產物處置見 [8.25 建置主機被入侵後的根除與重建](/backend/08-incident-response/compromised-build-host-eradication/)。
