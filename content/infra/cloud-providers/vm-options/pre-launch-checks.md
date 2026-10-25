---
title: "建立主機之前的檢查：建好就改不了的設定、登入路徑上各服務的支援組合、兩條登入路徑各自依賴的元件，以及容量稀缺時的取捨"
date: 2026-10-25
description: "在建立頁按下建立之前，把位置、機型與映像檔、網路、登入、安全開機各篇的選項串成幾項檢查：哪些設定建立之後只能重建、怎麼查，登入用的業者服務各自支援哪些機型與作業系統、元件狀態正常為什麼不代表支援，兩條登入路徑各自依賴哪些元件、哪些仍然共用，以及機型容量難取得時設定怎麼選；Oracle Cloud、Google Cloud 與 AWS 各自查這些事的位置"
weight: 8
tags: ["infra", "cloud-providers", "vm", "ssh", "access"]
---

雲端主機建立頁上的設定，有一部分建立之後只能重建才改得了，而登入要經過的業者服務各自只在一部分機型與作業系統上成立。這一篇把這兩類條件整理成按下建立之前要做的檢查：建好就改不了的設定，以及怎麼從業者的文件與工具查出來；登入路徑上每一個業者服務支援的機型與作業系統，以及元件狀態顯示正常為什麼不能當成支援的證據；兩條登入路徑各自依賴哪些元件、哪些元件仍然共用、不經過 sshd 的救援入口，以及停用其他入口之前要先確認什麼；機型容量難取得時，設定為什麼要選補救代價低的那一種；以及 Oracle Cloud、Google Cloud 與 AWS 查這些事的位置。各項設定本身的機制在 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)、[機型與映像檔：CPU 架構、核心與記憶體、計費模式與作業系統](/infra/cloud-providers/vm-options/shape-and-image/)、[網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)、[登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 與 [安全開機：Secure Boot、Measured Boot 與 TPM](/infra/cloud-providers/vm-options/shielded-boot/)；一次沒做這些檢查的實測經過（2026-10-25 在 Oracle Cloud 的 `ap-batam-1` 建了一台 A1 Ubuntu 主機，建好之後登不進去）在 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/)。

## 建好就改不了的設定：補救的代價與查法

建立頁上的設定依建立之後的處置分成三種：可以直接改（Oracle Cloud 的 plugin 開關、磁碟的效能等級）、改的時候要停機或重開（核心數與記憶體）、只能重建（CPU 架構與作業系統）。只能重建的設定，代價出現在發現選錯的那一刻：重建主機會換掉臨時公開 IP（私有 IP 沒有在建立時指定也會換）、開機磁碟上的資料要另外搬，機型容量難取得時還要再搶一次容量。所以建立之前要逐項找出只能重建的設定，替每一項寫出選錯時的補救路徑與代價。

同一項設定在三家的處置不同，所以這份清單要對著業者查，不能從另一家的經驗推過來。以 SSH 公鑰為例：

- **Oracle Cloud**：公鑰與初始化腳本存在主機的中繼資料裡，`oci compute instance update --help` 對 `--metadata` 的說明寫明 `ssh_authorized_keys` 與 `user_data` 在主機建立之後不能改，送出修改的請求會被拒絕。cloud-init 只在第一次開機時把公鑰寫進 `authorized_keys`，所以建立時選了不放金鑰，之後就沒有經由中繼資料補公鑰的方式；剩下的入口（代理程式臨時放公鑰、Run Command、把開機磁碟掛到另一台主機）各有前提，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈建立之後加金鑰與金鑰遺失時的入口〉。
- **Google Cloud**：公鑰存在專案或主機的中繼資料裡，建立之後可以再加。Google 的映像預先裝了 guest environment（業者裝在主機裡的一組程式），其中的 guest agent 持續依中繼資料同步金鑰，加進去的公鑰會寫進主機。
- **AWS**：EC2 Instance Connect 每次連線前把一把公鑰暫時推送到主機的中繼資料，不依賴建立時選的 key pair。條件是主機上裝了 EC2 Instance Connect 的套件、登入者有對應的 IAM 權限，以及連線到得了主機：官方〈Prerequisites for EC2 Instance Connect〉寫明主機要有公開 IP，或經由 Direct Connect、Site-to-Site VPN、VPC peering 這類私有連線，沒有公開 IP 時另一個選擇是 EC2 Instance Connect Endpoint。

其他類設定的處置寫在各自的那一篇：架構與映像檔見 [機型與映像檔：CPU 架構、核心與記憶體、計費模式與作業系統](/infra/cloud-providers/vm-options/shape-and-image/)（換作業系統要用新的映像檔重建；Oracle Cloud 可以替換開機磁碟，官方〈Replacing a Boot Volume〉限定只能換成同一個 Linux 發行版，Ubuntu 換不成 Oracle Linux），主要網卡所在的 subnet 與公開 IP 的種類見 [網路：subnet、私有 IP、公開 IP 與防火牆規則](/infra/cloud-providers/vm-options/networking/)，Oracle Cloud 的安全開機見 [安全開機：Secure Boot、Measured Boot 與 TPM](/infra/cloud-providers/vm-options/shielded-boot/)，區域與可用區見 [位置：區域、可用區與故障域](/infra/cloud-providers/vm-options/placement/)。

哪些設定只能重建，業者自己的工具也查得到。修改主機的 API 與 CLI 說明會寫哪些欄位不能改（上面 Oracle Cloud 那一條就是從 `--help` 讀到的）；用 Terraform 管理主機時，`terraform plan` 把只能重建的屬性標成 forces replacement，在 plan 上改一次那個屬性，就看得到它屬於哪一種（見 [terraform plan / apply](/infra/knowledge-cards/terraform-plan-apply/)）。

## 登入路徑上各服務的支援組合：支援清單、Known Issues 與元件狀態

登入一台沒有公開 IP 的主機，連線要經過幾個業者服務：哪個服務負責網路可達性、通道授權與主機登入驗證，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。每一個服務都只在一部分機型與作業系統上成立，而這份範圍寫在服務自己的文件裡，不寫在建立頁上：建立頁讓任何映像檔配任何相容架構的機型，建立會成功，登入在之後才失敗。

所以建立之前，對路徑上每一個服務讀三種文件：

- **支援的作業系統與映像檔清單**：例如 Oracle Cloud 的 Run Command 列出的是 Oracle Autonomous Linux、Oracle Linux、CentOS、Windows Server 與以它們為基礎的自訂映像，沒有 Ubuntu。不在清單上代表官方不保證，不代表一定不能執行：2026-10-25 在一台 A1 Ubuntu 主機上實測，Run Command 的 plugin 確實執行了指令，而能做到哪些事還要看下面的前置條件。AWS 的 EC2 Instance Connect 要主機用預先裝好它的 AMI，或在官方列為支援的 AMI 上自己安裝。
- **Known Issues**：支援清單寫的是作業系統，機型與作業系統的組合不支援的情形常常只寫在這一頁。Oracle Cloud〈Known Issues for Bastion〉的第一條是 Arm 架構的 A1 機型加非 Oracle Linux 的主機不支援 managed SSH session；這個組合在建立頁上建立會成功，A1 是 Always Free 的機型、Ubuntu 是建立頁列出的平台映像，兩者放在一起時 managed SSH session 才不支援。
- **前置條件**：服務在主機上用哪個使用者執行、要什麼權限。Oracle Cloud 的 Run Command 以 `ocarun` 這個使用者執行，要寫其他使用者的檔案得先替它設 sudo；官方列的做法有兩種，建立時用 cloud-init 放 sudoers 檔，或建好之後登入主機設定。主機登不進去時才想用 Run Command 救援，只剩前一種，而初始化腳本是建立後不能改的欄位，所以這件事要在建立之前決定。AWS 的 Session Manager 要主機上有 SSM Agent，並讓 Systems Manager 取得操作這台主機的權限。

元件的狀態欄顯示的是元件啟動了，這個組合能不能完成登入，寫在支援清單與 Known Issues 裡，兩者描述的是不同的事。Oracle Cloud 的主機頁面上，A1 Ubuntu 主機的 Bastion plugin 顯示 `RUNNING`，Bastion 的工作階段照樣在約 15 分鐘後逾時。缺了前置條件時，狀態欄也一樣顯示正常：同一台主機的 Run Command plugin 也是 `RUNNING`，指令確實執行了，而 `ocarun` 沒有 sudo，寫不了 `authorized_keys`。

演練能驗到的，只有演練主機與正式主機相同的那些條件。演練主機與正式主機在機型、映像檔、服務三者都相同時，演練才驗得到組合不支援的情形；上面那一條 Known Issue 只針對 A1，在 x86 機型上用同一版 Ubuntu 的 x86 映像演練，照 Known Issues 的寫法不在不支援的範圍裡（這個推論沒有實跑），演練成功只代表 x86 加 Ubuntu 這個組合支援。機型本身就是要驗的條件時，演練換不了機型，只剩讀文件這一條路。

## 兩條登入路徑：各自依賴的元件與仍然共用的部分

登入路徑上的每一個元件都可能失效：代理程式沒有啟動、服務不支援這個組合、權限漏給、出站路徑被收緊、sshd 的設定改壞。只有一條路徑時，那條路徑上任何一個元件失效，主機就沒有入口；這個代價在重建昂貴時才成立（主機上有狀態、機型容量難取得、第一次用這個機型加作業系統的組合）。主機不存狀態、重建便宜時，重建本身就是那一條備用路徑，見 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/) 的〈不可變基礎設施下的臨時授權：通道平時關閉〉。備用路徑能不能當退路，看它跟原本那條路徑共用哪些元件：共用的元件失效時兩條一起斷，例如 Oracle Cloud 的 managed SSH session 與 Run Command 都經由主機上的 Oracle Cloud Agent，代理程式停掉時兩者一起失效。所以要把兩條各自依賴的元件逐項列出來，確認建立之前最沒有把握的那一項（這次的機型加作業系統是否在支援範圍、代理程式會不會正常運作）只出現在其中一條上。

列的時候要把整條路徑走完，不只看名字裡的服務。Oracle Cloud 的 managed SSH session 名字裡只有 Bastion，而 plugin 做的是把公鑰臨時放進 `authorized_keys`，登入照樣經過主機的 sshd；官方〈Managed SSH Session Creation Failed〉把 sshd 設定與 `authorized_keys` 列在成因裡。三家常見的組法與它們實際依賴的元件：

- **Oracle Cloud**：managed SSH session 依賴 Bastion plugin、機型與作業系統在支援範圍、代理程式連到服務端點的出站路徑；SSH port forwarding session 不經過 plugin，依賴建立時放進中繼資料、由 cloud-init 寫進 `authorized_keys` 的公鑰。兩條仍然共用 Bastion 服務與它允許連入的來源位址、建工作階段的權限、security list 放行 22 port 的規則、主機的 sshd。所以這一組擋得住 plugin 與支援範圍出錯，擋不住 sshd 改壞或 Bastion 允許的來源位址過期。
- **Google Cloud**：IAP TCP forwarding 加 OS Login 依賴 IAM 角色、防火牆放行 IAP 的來源位址 `35.235.240.0/20`、guest environment 處理的 OS Login，以及主機的 sshd。OS Login 啟用之後主機忽略中繼資料裡的公鑰，OS Login 開著時同一台主機上沒有另一條不經過 OS Login 的 SSH 路徑；對單台主機把中繼資料設成 `enable-oslogin=FALSE` 會恢復 guest agent 同步公鑰的路徑（主機層級的設定蓋過專案層級），組織政策強制 OS Login 時這條用不了，而且它仍然共用 IAP、防火牆、guest agent 與 sshd，算不上獨立的備用路徑。所以常備的備用路徑是序列主控台（serial console）加事先建好的救援帳號：它經由 Google 的序列埠閘道連線，用中繼資料裡的 SSH 公鑰驗證連線者，不經過主機自己的網路設定與 sshd，在登入提示用救援帳號的密碼登入。
- **AWS**：Systems Manager Session Manager 依賴 SSM Agent、Systems Manager 操作這台主機的權限與出站路徑，不經過 sshd；EC2 Instance Connect 或建立時選的 key pair 依賴 sshd、security group 放行 22 port，以及連得到主機的網路（公開 IP、私有連線或 EC2 Instance Connect Endpoint），EC2 Instance Connect 另外要登入者的 IAM 權限。這兩條共用的元件最少。官方另有 EC2 Serial Console，支援 Nitro 系統上的主機，要先完成存取設定、主機裡要有設了密碼的帳號。

三家都有一條不經過 sshd 的救援入口：序列主控台加設了密碼的救援帳號。這個帳號要在主機還登得進去時建，或建立時用初始化腳本建；Oracle Cloud 與 AWS 的平台映像，預設使用者只用金鑰登入、沒有密碼。救援帳號怎麼建、序列主控台平時為什麼關著，見 [Serial Console（序列主控台）](/infra/knowledge-cards/serial-console/) 卡。

兩條路徑都要在停用公開 IP 的 SSH 這類其他入口之前，各自實際登入過一次。只寫在設定裡、沒登入過的路徑，登入時才會發現少了哪一項條件；這跟切換管理通道時救援入口要先準備好並登入過是同一件事，見 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/) 的〈救援入口：管理通道斷掉時的備用路徑〉。

不放公鑰減少了主機裡長期有效的金鑰，代價是在 Oracle Cloud 上拿掉了不經過代理程式的那一條路徑。放在私有 subnet、沒有公開 IP 的主機，網路可達性這一層已經擋住外部的連線，用得了這把公鑰的只剩持有私鑰、而且有建工作階段的權限或已經在同一個 subnet 裡的人，增加的暴露很小，換到的是代理程式失效時的入口；代價是這把金鑰要管理、人員離開時要收回，而在 Oracle Cloud 上，中繼資料裡的公鑰建立後不能換。同時滿足「主機裡沒有長期有效的使用者公鑰」與「不依賴代理程式」的做法是 SSH 憑證：建立時用初始化腳本放 CA 的公鑰，登入時用 CA 簽的短效憑證，代價是要維運一個 CA；在 Oracle Cloud 上 CA 的公鑰同樣經由建立後不能改的初始化腳本放入，換 CA 要登入主機改或重建，做法見 [伺服器管理通道的設計：網路可達性、通道授權、主機登入驗證三層的做法與選擇，以及救援入口](/infra/03-network-foundation/management-access-channel/) 的〈主機登入驗證的做法：SSH 金鑰怎麼發、怎麼收回〉。所以第一次在某個機型加作業系統的組合上建主機時，放一把自己的公鑰。這把公鑰之後要不要從 `authorized_keys` 拿掉，取決於另一條不共用代理程式的入口在不在：拿掉之後只剩代理程式那一條，回到單一路徑；先建好序列主控台的救援帳號並登入過，拿掉公鑰時才仍然有兩條，而救援帳號的密碼同樣是長期有效的憑證，要逐台輪替（見 Serial Console 卡的〈設計責任〉）（Oracle Cloud 上的做法與前提見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉最後一段）。

## 容量稀缺時設定的取捨：補救代價與最嚴格設定的驗證位置

機型的容量難取得時（免費額度裡的熱門機型、GPU 機型），建好就改不了的設定選錯的代價，除了重建，還多了一次重新取得容量。Oracle Cloud 的 Always Free A1 在 `ap-batam-1` 實測時，同一個帳號 2026-10-24 整天的建立請求都回容量不足，2026-10-25 用重送腳本送了 16 次才建成（重送的做法與限流的量測見 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/hands-on/launch-instance-walkthrough/) 的〈重送建立請求：CLI 自己的重送、限流門檻與重送腳本〉）。

這時的取捨是選補救代價低的設定：作業系統選登入服務完整支援的那一個、建立時放一把之後可以移除的公鑰、兩條登入路徑都備齊。最嚴格的設定（不放任何金鑰、只靠代理程式）要拆成兩部分驗：跟機型無關的那一部分（代理程式的設定、登入權限、防火牆規則）可以先在容易重建的機型上測；跟機型有關的支援範圍，照〈登入路徑上各服務的支援組合：支援清單、Known Issues 與元件狀態〉讀文件對這次的機型確認，演練驗不到這一部分。必須在某個時間點拿到容量的情境，可以改用預留容量（capacity reservation），見 [機型與映像檔：CPU 架構、核心與記憶體、計費模式與作業系統](/infra/cloud-providers/vm-options/shape-and-image/) 的〈計費模式：隨用隨付、可被收回、預留容量與專屬主機〉。

搶容量的重送腳本把建立參數寫死在腳本裡，所以腳本送出的設定，是寫腳本那一刻的判斷。從寫好腳本到建成主機可能隔了好幾個小時，這段時間裡查到的新資訊（Known Issues 的一條、某個服務的前置條件）不會自己進到腳本裡；腳本裡的參數要在兩個時間點再對過這一篇的檢查（建好就改不了的設定、各服務的支援組合、兩條登入路徑各自依賴的元件）：重新啟動腳本的那一刻，以及腳本還在跑時查到會改變建立參數的新資訊的那一刻（這時先停掉腳本，改完參數再啟動）。一開始就選補救代價低的參數時，判斷過期的代價也跟著變小。

## 各家查建立後不能改的欄位、登入服務支援組合與代理程式狀態的位置

| 要查的事                     | Oracle Cloud                                                                         | Google Cloud                                   | AWS                                                                   |
| ---------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------- | --------------------------------------------------------------------- |
| 哪些欄位建立後不能改         | `oci compute instance update --help` 各欄位的說明；〈Replacing a Boot Volume〉的限制 | Compute Engine 文件修改各項屬性的頁面          | EC2 文件修改主機屬性的頁面與 `aws ec2 modify-instance-attribute help` |
| 登入服務支援的組合           | Bastion 的〈Known Issues for Bastion〉；Run Command 說明頁的支援映像清單             | OS Login 與 IAP TCP forwarding 的說明頁        | EC2 Instance Connect 的〈Prerequisites〉；Session Manager 的前置條件  |
| 代理程式與 plugin 的執行狀態 | 主機頁面的 Oracle Cloud Agent 分頁，或 `oci instance-agent plugin list`              | `get-serial-port-output` 裡 guest agent 的啟動 | Systems Manager 的 Fleet Manager 列出的受管主機                       |

「代理程式與 plugin 的執行狀態」那一列查到的是元件有沒有啟動；〈登入路徑上各服務的支援組合：支援清單、Known Issues 與元件狀態〉那一節的支援清單與 Known Issues，仍然要另外讀。
