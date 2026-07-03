---
title: "Right-sizing"
date: 2026-07-03
description: "把配置規格調到貼近實際用量時，怎麼找出過度配置的資源、downsizing 不能砍過膝點、以及機型世代與 reserved 過剩的回收"
weight: 2
tags: ["devops", "cost-management", "right-sizing", "utilization", "downsizing"]
---

過度配置是雲端最大的浪費來源，right-sizing 就是把配置規格調回貼近實際用量。一台長期只用 30% CPU 的機器，那 70% 是純浪費——資源開著、每小時計費，卻沒在做事。right-sizing 是持續對照實際用量調整規格的紀律、不是一次性的動作，因為用量會變、機型會更新、當初配的規格很快就不再是最合適的。

## 找出過度配置的資源

right-sizing 的起點是量測實際用量，跟配置規格比對。過度配置有幾種常見形態。最直接的是規格訂太大——CPU、記憶體長期只用一小部分，配了 8 核卻總在 2 核以內晃。第二種是機型世代過時——還在用舊世代的機型，沒升級到單位效能更好的新代，同樣的錢買到更少的效能。第三種是 reserved 買太多用不滿——當初承諾的量高於實際需求，多出來的承諾照付卻沒用到。

這三種浪費都不會自己報警，要靠定期 review 才抓得到。量測看的是利用率指標（CPU、記憶體、網路、IOPS 的實際使用率），長期偏低就是 downsizing 的候選。這裡要看的是「持續的」利用率，不是某個瞬間——一台平時 20%、但每天有一段跑到 90% 的機器，不能只看平均就砍。

## Downsizing 不能砍過膝點

Downsizing 有一條不能越過的線：不能把規格砍到系統的膝點以下。一台利用率長期 30% 的機器看起來浪費，但如果把它砍到平時就跑在 70%，就沒有 headroom 應付突發了——突發一來直接進飽和曲線的膝點區、延遲飆升。飽和曲線與膝點的位置在 [模組五 規模拐點判斷](/devops/05-capacity-planning/scaling-inflection-point/) 講過，right-sizing 要在那條曲線上留足 headroom：砍掉純浪費的部分、但保住應付波動與 forecast 誤差的緩衝。

所以 downsizing 是有邊界的優化，不是「利用率越高越省」。目標是把利用率調到健康區間（膝點以下的 50% 到 70%），而不是頂到極限。砍過頭省下的機器錢，會用一次突發時的服務降級賠回來，而且賠得更多。downsizing 之後要觀察一段時間，確認新規格在真實流量（含波動）下站得住，再確定這個尺寸。

## 機型世代與 reserved 回收

機型世代升級是低風險的 right-sizing。雲端持續推出新世代的機型，同樣的規格、新世代常常更便宜或效能更好——換過去幾乎沒有壞處，只需要一次規格變更。定期檢查有沒有停在舊世代，是最容易拿到的成本節省之一。

reserved 過剩的回收比較麻煩。買了用不滿的 reserved，錢已經承諾出去了，處理的方式是看能不能把承諾轉移到還在用 on-demand 的其他工作負載上，或在有二級市場的情況下轉售。這也是為什麼 reserved 的承諾要保守——承諾的是「確定長期用得到」的基準量，把不確定的部分留給 on-demand。買 reserved 前先把 right-sizing 做完，才不會用折扣鎖住一個過大的規格：一台過度配置的機器買了 reserved，等於用三年的承諾把浪費也鎖了三年。

## 下一步路由

- 砍規格不能越過的膝點在哪、headroom 怎麼算 → [模組五 規模拐點判斷](/devops/05-capacity-planning/scaling-inflection-point/)
- reserved 的承諾模式、怎麼配工作負載 → [計費模式理解](/devops/08-cost-management/billing-models/)
- 定期 review 靠什麼監控、異常怎麼抓 → [成本監控與告警](/devops/08-cost-management/cost-monitoring/)
