---
title: "7.45 加密備份的密碼、key 檔與主金鑰：換密碼與換主金鑰的差別、密碼外洩與遺失的處置，以 restic 為例"
date: 2026-11-03
description: "加密備份工具把資料交給一把隨機產生的主金鑰加密、密碼只用來解開包著主金鑰的 key 檔：這個分層換到的多份 key 檔與不重新加密的換密碼、換密碼之後舊副本與外流的 key 檔還解得開什麼、什麼條件下要建新 repository 換掉主金鑰，以及密碼遺失時沒有任何找回的路"
weight: 120
tags: ["backend", "security", "backup", "encryption", "key-management", "restic"]
---

這一章整理加密備份工具的密碼與金鑰結構，以 restic 為例。restic 把備份加密之後存進一個 repository（restic 存放加密備份的位置，可以是本機資料夾、NAS 或物件儲存），而 repository 裡跟密碼有關的有兩樣：加密資料用的主金鑰，以及 key 檔（repository 的 `keys/` 目錄底下、用密碼包著主金鑰的檔案）。各節依序是：資料、主金鑰、key 檔與密碼各自的角色，以及一個 repository 為什麼可以有好幾組密碼；換密碼時 repository 裡實際改了什麼、沒改什麼；換密碼之後，之前複製出去的副本與已經外流的 key 檔還解得開哪些資料；什麼條件下只換密碼就足夠、什麼條件下要建一個新的 repository 把主金鑰也換掉，以及這兩條路各自的代價；最後是密碼遺失的後果與事先能做的準備。restic 在 Docker Compose 裡以 sidecar 容器（跟主服務並排、在同一個 Compose 專案裡執行的輔助容器）執行時，換密碼的實際步驟、依 exit code 判斷 repository 狀態的啟動腳本、外洩之後搬到新 repository 與唯讀還原演練，在 [restic sidecar 容器的密碼操作](/backend/07-security-data-protection/hands-on/restic-sidecar-password-operations/)。備份的存取憑證被拿去覆寫或刪除備份是另一類風險，那一類在 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的異地備份那一段。

## 資料、主金鑰、key 檔與密碼各自的角色

restic 的 repository 裡，備份的檔案內容、目錄樹（tree）與快照（snapshot）都由一把主金鑰（master key）加密。主金鑰在 `restic init` 時隨機產生，包含一把加密用的金鑰與一把驗證完整性用的 MAC 金鑰（[restic 的設計文件](https://restic.readthedocs.io/en/stable/100_references.html#keys-encryption-and-mac)）。密碼不直接加密任何資料：每一份 key 檔裡存著用密碼推導出的金鑰加密過的主金鑰，加上推導用的參數（scrypt 這個金鑰推導函式的成本參數 N、r、p，決定每推導一次要花多少記憶體與運算時間，讓猜密碼的人每試一次都要付同樣的成本，見 [Memory-Hard Function](/backend/knowledge-cards/memory-hard-function/)；以及讓同一組密碼每次推導出不同金鑰的隨機值 salt，見 [Salt](/backend/knowledge-cards/salt/)）。打開 repository 的順序是：用密碼與 key 檔裡的參數推導出一把金鑰，用它解開 key 檔裡的主金鑰，再用主金鑰讀資料。這種用一把金鑰包著另一把金鑰的做法稱為金鑰包裝（key wrapping），雲端金鑰管理服務（KMS）的信封加密（envelope encryption）是同一個結構，金鑰的生命週期在 [Key Management](/backend/knowledge-cards/key-management/)。

這個分層不是 restic 獨有的：Borg 的 repokey 模式與磁碟加密 LUKS 的 keyslot（LUKS 磁碟標頭裡用一組密碼包著磁碟加密金鑰的欄位，一顆磁碟可以有好幾個）也是用密碼包著一把真正加密資料的金鑰，本章的判斷方式同樣適用。Borg 另有 keyfile 模式，包著金鑰的檔案放在備份用戶端的主機上、不在 repository 裡，repository 副本本身不帶 key 檔，下文「帶著舊 key 檔的副本」在那個模式下要換成「用戶端主機上的 key 檔」；差別在 LUKS 另有原地重新加密資料的工具（`cryptsetup reencrypt`，本章沒有實跑），換主金鑰不必另建一份。

主金鑰與密碼的變動頻率不同，所以中間隔了 key 檔。資料量可能是幾百 GB，主金鑰一換就要把全部資料重新加密；密碼是人要記住、會外洩、會想換的秘密。密碼只拿來打開 key 檔，所以密碼的變動只碰到 key 檔，資料與主金鑰維持不動。

這個分層換到兩件事：

- **一個 repository 可以有好幾組密碼**：`restic key add` 用另一組密碼替同一把主金鑰再包一份 key 檔，`restic key list` 列出現有的 key 檔（每一份的 ID、使用者名稱、主機名稱與建立時間），`restic key remove` 刪掉其中一份。每一組密碼解開的都是同一把主金鑰。多台主機、多個人各持一組密碼時，刪掉其中一個人那一份 key 檔，他就無法再用 restic 打開這個 repository；他在那之前是否讀出過主金鑰，是另一件事，判斷方式在〈換密碼與換主金鑰的適用條件〉那張表的「人員離開」那一列。`key list` 的使用者與主機名稱預設取自執行 `key add` 的那個環境，在容器裡加的 key 全是 `root` 加上容器名稱，認不出是誰的；`key add` 帶 `--user` 與 `--host` 可以寫成看得出持有人的名稱。
- **換密碼不必重新加密資料**：`restic key passwd` 用新密碼包一份新的 key 檔、刪掉舊的那一份，資料檔與快照沒有被改寫，所以換密碼花的時間跟 repository 的大小無關（這是從結構推論的，實測只在幾 KB 的 repository 上跑過）。

用 `cat` 讀 `keys/` 底下任何一份 key 檔，看得到這個結構：它是一段 JSON，`kdf` 欄位是 `scrypt`，`N`、`r`、`p` 與 `salt` 是推導用的參數，`data` 是被包起來的主金鑰。`restic cat masterkey` 則印出解開之後的主金鑰（`encrypt` 與 `mac` 兩個欄位），能用任何一組密碼打開 repository 的人，都能用這個指令讀出它。

## 換密碼之後，repository 裡改了什麼、沒改什麼

`restic key passwd` 改的只有 `keys/` 目錄：多一份新密碼包的 key 檔，少一份舊密碼包的 key 檔。主金鑰沒有變，資料與快照沒有重新加密。由這一點推出兩個後果，持有 repository 的人換密碼之後，在還原或判斷外洩範圍時會碰到它們：

**之前複製出去的副本不會跟著換。** 備份有多份副本時（NAS 上一份、物件儲存上一份、某次搬家時手動複製的一份），換密碼只改了執行 `key passwd` 的那一份 repository 的 `keys/`，其他副本的 `keys/` 還是舊的 key 檔，要用舊密碼打開。換密碼之後還要用某一份舊副本還原時，手上要有舊密碼，或在那一份副本上也做一次 `key passwd`。

**外流的舊 key 檔加上舊密碼，仍然解得開同一把主金鑰。** 主金鑰沒換，所以任何時候拿到的資料，都能用這把主金鑰讀。實測時（restic 0.19.1）先把 `keys/` 底下的舊 key 檔另存一份、執行 `key passwd`、再做一次新的備份，接著把舊 key 檔放回一份後來才取得的 repository 副本裡，用舊密碼執行 `restic snapshots`，換密碼之後才建立的那個快照也列得出來、讀得到。換句話說，對方只要曾經同時拿到過舊 key 檔與舊密碼，之後再取得任何一份 repository 的副本（物件儲存的 bucket 外洩、NAS 被入侵），換密碼都擋不住他讀資料。

## 換密碼與換主金鑰的適用條件：對方可能取得的材料

要讀 repository 裡的資料，需要主金鑰；要得到主金鑰，需要「某一份 key 檔」加上「包那一份 key 檔的密碼」，兩樣要對得上。所以外洩之後，只換密碼是否足夠、還是要連主金鑰一起換，看對方手上有哪幾樣、它們是不是同一組。下表的「帶著舊 key 檔的副本」指換密碼之前取得的副本，或還沒做過 `key passwd` 的那幾份副本（NAS、手動複製的那一份）；換密碼之後才取得、而且已經換過的副本，裡面只有新密碼包的 key 檔：

| 對方可能取得的材料                                               | 換密碼之後的結果                                                                              | 只換密碼的判定                                   |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 只有密碼，所有帶著舊 key 檔的副本都在對方碰不到的地方            | 舊 key 檔被刪除，對方手上的密碼沒有對應的 key 檔可解                                          | 足夠                                             |
| 密碼，加上任何一份帶著舊 key 檔的副本，或那份 key 檔本身         | 對方從舊 key 檔解出主金鑰，之後拿到的每一份副本都讀得到，包括換密碼之後的快照                 | 不足，主金鑰也要換                               |
| 只有 repository 副本（例如物件儲存的存取金鑰外洩），密碼沒有外洩 | 現在讀不到；那份副本裡 key 檔的密碼日後任何時候外洩，它就讀得到，之後再換密碼也保護不了這一份 | 密碼強度足以擋住離線猜測時足夠；不確定時換主金鑰 |
| 人員離開：曾經能打開 repository 的人，用的是他自己那一份 key 檔  | 刪掉他的 key 檔之後，他無法再用 restic 打開；他若讀出過主金鑰，之後拿到的副本仍讀得到         | 他之後仍接觸得到任何一份副本時不足               |
| 例行的定期輪替，沒有外洩跡象                                     | 舊 key 檔被刪除                                                                               | 足夠                                             |

「只有密碼」那一列的前提要能查證：repository 放在哪幾個位置、每個位置有哪些人或哪些機器的存取憑證能讀。查不清楚時，「只有密碼」與「密碼加上帶著舊 key 檔的副本」兩列分不開，而把「密碼加上副本」的情形判成「只有密碼」的代價，是對方持續讀得到之後的每一份備份、而且沒有任何訊號。放 `RESTIC_PASSWORD` 的那份 `.env` 若同時放著物件儲存的存取金鑰，那份檔案外洩就同時交出了密碼與取得副本的路徑，落在「密碼加上帶著舊 key 檔的副本」那一列。「只有副本」那一列的離線猜測，是對方拿著 key 檔逐一試密碼，scrypt 的成本參數讓每試一次都要花記憶體與時間，擋得住多少取決於密碼的長度與隨機程度。「人員離開」那一列只適用於每個人各有一份 key 檔的情形；團隊共用同一組密碼時，離開的人手上的就是那組密碼，照「只有密碼」與「密碼加上帶著舊 key 檔的副本」兩列判斷。他「讀出過主金鑰」不需要特殊工具，上面的 `restic cat masterkey` 就做得到。

表中判成「足夠」的兩列，前提是換密碼或 `key remove` 之後，舊 key 檔確實從儲存端消失了。防止備份被覆寫或刪除的儲存設定，正好讓這個前提不成立：

- **append-only 的 rest-server**：實測（rest-server 0.14.0 以 `--append-only` 執行）`key passwd` 寫得進新 key 檔，刪除舊 key 檔時 rest-server 回 `403 Forbidden`，restic 以 exit 1 結束；之後舊密碼照樣打得開，`key list` 列出新舊兩份 key 檔。
- **開了版本保留或物件鎖定的物件儲存**：刪除只留下刪除標記，舊 key 檔成為非現行版本，有權限讀取舊版本的人取回它，用舊密碼就打得開（從物件儲存的版本語意推論，沒有實跑）。

在這兩種儲存端上，「只有密碼」與「例行輪替」兩列要改照「密碼加上帶著舊 key 檔的副本」那一列判斷，除非舊 key 檔的舊版本另外清掉。`key passwd` 與 `key remove` 要在持有完整存取權、刪得掉檔案的那台機器上執行，跟 7.43 對 `forget` 與 `prune` 的安排相同；物件儲存的舊版本要另外刪除，或等保留期滿。存取金鑰本身的撤銷與輪替在 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/) 的異地備份那一段。

### 換掉主金鑰：建新 repository 並用 restic copy 搬快照

restic 沒有在原地更換主金鑰的指令（`restic key` 只有 add、list、passwd、remove 四個子指令），換主金鑰的方式是建一個新的 repository（新的 `restic init` 產生一把新的主金鑰），再用 `restic copy` 把舊 repository 的快照搬過去。`copy` 會把資料從舊主金鑰解開、用新 repository 的主金鑰重新加密寫入。實測時把同一份舊 key 檔放進新 repository 的 `keys/`，用舊密碼打開，restic 回報 `ciphertext verification failed` 並以 exit 1 結束：舊 key 檔解出的是舊主金鑰，對新 repository 的資料不成立。

這條路的代價：

- **全部資料重新加密、重新寫一次**：`copy` 要把全部快照讀一次、寫一次；快照搬完之前，新舊兩個 repository 都要有空間，新 repository 放在物件儲存時，上傳量是全部資料。`copy` 不會重新切分檔案，所以搬過來的資料與之後直接 `backup` 到新 repository 的資料，要用同一組切塊參數（restic 依內容把檔案切成資料塊，切點由每個 repository 在 `init` 時各自隨機產生的參數決定；相同內容切出相同的資料塊，才認得出是重複的）才能互相做重複資料刪除（deduplication）；`restic init` 加 `--copy-chunker-params` 讓新 repository 沿用舊的參數，參數不同時，換過去之後第一次備份會把同樣的內容再存一次（[restic 文件的 Ensuring deduplication for copied snapshots](https://restic.readthedocs.io/en/stable/045_working_with_repos.html)）。
- **舊 repository 要淘汰，包括它的每一份副本**：舊 repository 只要還在某個位置，對方拿到它就讀得到搬遷之前的全部快照；換主金鑰保護的是之後的備份，已經外流的副本救不回來。
- **備份程式要改指到新 repository**：設定與密碼都換，換完確認新的快照照常產生。

## 密碼遺失的後果與事先的準備：另存的密碼與離線保管的備援密碼

密碼與 key 檔都在、主金鑰才解得開。所有 key 檔的密碼都遺失時，沒有任何服務、管理員或工具能找回主金鑰，資料就無法還原，`restic init` 的輸出直接寫著這一點（`Losing your password means that your data is irrecoverably lost.`）。

密碼只存在被備份的那台主機上時（寫在主機的 `.env` 或設定檔裡），主機的硬碟壞掉，資料與密碼一起不見：異地的備份完整，卻沒有密碼打得開。所以密碼要另外存在不依賴那台主機的位置（密碼管理器），而且換密碼之後同一次更新那一份。

多份 key 檔的結構另外提供一種準備：用 `restic key add` 以另一組密碼再包一份 key 檔，這份 key 檔跟其他的一樣留在 repository 的 `keys/` 裡，離線保存的是它的密碼（紙本放保險箱、或另一個帳號的密碼管理器）。日常用的那一組密碼遺失時，這一組密碼仍然打得開。把現有的 key 檔複製一份放到離線位置沒有這個作用：那份 key 檔還是要原本那組密碼才解得開。代價是多一組要保管的秘密，以及多一條外洩路徑：這一組密碼也要放進〈換密碼與換主金鑰的適用條件〉那張表一起判斷，換密碼時它不會自動跟著換。

## 延伸閱讀：sidecar 容器的實際操作、備份的寫入憑證與使用者密碼外洩

- 換密碼、啟動腳本依 exit code 區分「repository 不存在」與「密碼錯誤」、外洩之後搬到新 repository、唯讀掛載的還原演練，實測步驟與輸出在 [restic sidecar 容器的密碼操作](/backend/07-security-data-protection/hands-on/restic-sidecar-password-operations/)。
- 備份的存取憑證只給上傳權限時仍然覆寫得掉既有備份、版本保留與 append-only 伺服器，在 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/)；物件鎖定的兩種模式在 [WORM Storage](/backend/knowledge-cards/worm-storage/)。
- 一批使用者密碼外洩時怎麼定重設範圍，是另一個對象（使用者帳號的密碼，不是加密金鑰的密碼），在 [7.37 密碼外洩之後](/backend/07-security-data-protection/credential-breach-response/)。
