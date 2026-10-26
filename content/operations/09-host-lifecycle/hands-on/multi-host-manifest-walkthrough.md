---
title: "多台主機維護清單的實作紀錄：在容器上安裝 ansible-core 與 Terraform、由 Terraform 產生 inventory、用 Ansible 的範本部署每台的清單、以 sudo 與 systemd-run 執行檢查腳本，以及清理"
date: 2026-10-26
description: "要照著部署多台主機的維護清單並執行檢查腳本，或要讀跨主機執行時 ansible 的 exit code 與每台的 rc、門檻造成的 WARN、清單格式錯與連不上的主機各自印出什麼時，或要確認 Terraform 寫出的 inventory 的檔案權限、`--check` 預覽與實際部署結果不同的情形時，查在可拋棄的容器上實際跑過的指令、輸出與遇到的錯誤"
weight: 1
tags: ["operations", "maintenance", "ansible", "terraform", "toml", "systemd", "hands-on"]
---

> **事件說明**：2026-10-26，在一台 Apple Silicon 的 macOS 開發機上，用 OrbStack 提供的 Docker Engine 29.8.2（核心 `7.2.12-orbstack`，arm64，[cgroup（控制群組）](/backend/knowledge-cards/cgroup/) v2）建立可拋棄的容器，把多台主機的維護清單從 Terraform 產生 inventory、用 Ansible 部署到兩台主機並執行檢查腳本。受管主機（managed node，Ansible 連過去執行任務的主機）是兩個 Oracle Linux 10.2 容器（systemd 257 當 PID 1，OpenSSH 9.9p1、Python 3.12.15、sudo 1.9.17、dnf-automatic 4.20.0），以 `--privileged --cgroupns=private` 執行。控制端（control node，執行 `ansible` 與 Terraform 指令的機器）是一個 `python:3.12-slim` 容器（Debian 13，OpenSSH 用戶端 10.0p2），裝 ansible-core 2.17.7（Jinja2 3.1.6）與 Terraform 1.9.8，Terraform 的 `hashicorp/local` provider（Terraform 操作某一類資源的外掛）是 2.5.2。檢查腳本是沒有公開的 `host-check.py`（2026-10-26 的版本），原樣複製一份來用。

這篇把 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/) 的做法在兩台可拋棄的受管主機上從安裝走到清理，一台只當 web、另一台同時是 web 與 db。各節依序是：

- 受管主機與控制端的容器怎麼建、裝了哪些套件。
- 控制端經由 SSH 登入受管主機用的金鑰、`known_hosts` 與 sudo。
- Terraform 由主機清單寫出 inventory（Ansible 讀的主機清冊，見 [Configuration Management（組態管理）](/infra/knowledge-cards/configuration-management/)），以及 `local_file` 的預設檔案權限。
- 變數檔與範本照檢查腳本實際要求的欄位寫，兼任兩種角色的主機怎麼取得兩個角色的入口。
- 用 playbook（依序執行多個任務的 YAML 檔）部署檢查腳本與每台的清單：`validate` 改用檢查腳本自己的載入函式、在寫出之前就驗出欄位錯誤，以及 `--check` 的預覽與實際執行結果不同的那一次。
- 以 `-b` 與 `systemd-run` 對所有主機執行檢查腳本，每台的輸出與 `ansible` 指令的 exit code。
- 刻意讓一台的門檻變成 `WARN`、讓一台的清單格式錯、讓一台連不上時，`ansible` 的 exit code 與每台的 `rc` 各是什麼。
- 容器跟真主機不同的地方，以及在真主機上要另外確認的項目。
- 清理。

值為什麼分成每台相同、依角色不同、每台不同三類，合併為什麼放在部署時，exit code 2 與 4 的意思，這些判斷依據寫在那篇概念文章，這裡只寫套在這次環境上的操作與結果。清單的格式、檢查腳本的白名單與 `systemd-run` 各屬性的效果在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)。這次沒有碰雲端：主機是容器，雲端防火牆那一層的檢查在清單裡寫成要到主控台確認的項目，`terraform plan` 對雲端資源的比對也沒有量。

## 前置條件：開發機的資源、檔案配置與檢查腳本

- **開發機的記憶體**：這次三個容器同時在跑時，`docker stats` 量到受管主機各用 36 MiB 與 52 MiB、控制端 5 MiB（檢查腳本執行時，systemd 回報那一次執行的記憶體高峰是 70 MiB 到 79 MiB）。這些值依映像檔與正在跑的服務而變；開發機上已經有別的容器在跑時，建容器之前先看 swap 已用多少（macOS 是 `sysctl vm.swapusage`）與 OrbStack 分到的記憶體上限（在 OrbStack 的設定裡）。
- **主機的數量**：兩台受管主機加一個控制端是這次需要的最小組合：一台只當 web、一台兼任 web 與 db，才看得到依角色取聯集的結果；控制端一個就夠。
- **一個工作目錄**：控制端容器把它掛在 `/work`，Terraform 的設定、Ansible 的變數檔、範本、產生出來的 inventory 與 Terraform 的 [State（IaC 狀態檔）](/infra/knowledge-cards/state/) 都放在這裡；容器刪掉之後 State 仍在開發機上，清理時才查得到 Terraform 建過什麼。這次的配置：

  ```text
  .
  ├── host-image/Containerfile       # 受管主機的映像檔
  ├── ctl-image/Containerfile        # 控制端的映像檔
  └── work/
      ├── tf/main.tf                 # Terraform：主機清單與寫出 inventory 的 local_file
      └── ansible/
          ├── inventory.yml          # 由 Terraform 寫出，不手改
          ├── group_vars/all.yml     # 每台相同的值
          ├── group_vars/web.yml     # web 角色的值
          ├── group_vars/db.yml      # db 角色的值
          ├── host_vars/mh-web1.yml  # 只有 mh-web1 不同的值
          ├── host.toml.j2           # 清單的範本
          ├── files/host-check.py    # 檢查腳本
          ├── deploy.yml             # 部署腳本與清單的 playbook
          └── check.sh               # 對每台執行檢查的 ad-hoc 指令（不寫 playbook、直接執行單一模組）
  ```

  下面各節程式碼區塊第一行的註解寫著檔名，照那個路徑在開發機上建檔，路徑的起點依檔案分三種：

  - `host-image/…`、`ctl-image/…`：從 `work/` 的上一層起算。兩個映像檔的建置目錄不必掛進控制端，所以不放進 `work/`。
  - `tf/main.tf`：從工作目錄 `work/` 起算。
  - 其餘的（`group_vars/…`、`host.toml.j2`、`deploy.yml`、`check.sh`）：從 `work/ansible/` 起算。

  `ansible/` 與 `tf/` 目錄要在起控制端容器之前建好。`inventory.yml` 跟 `group_vars/`、`host_vars/` 放在同一個目錄，是 Ansible 載入這兩個目錄的條件：Ansible 從 inventory 檔所在的目錄（以及 playbook 所在的目錄）找 `group_vars/` 與 `host_vars/`。

- **檢查腳本**：`host-check.py` 沒有公開，照著做時換成自己的檢查腳本。這篇的步驟用到的腳本行為有下面這幾項，替代的腳本要全部滿足，或照它的行為改寫對應的步驟：
  - 有一個只載入與驗證清單、不執行檢查的函式或模式，清單格式錯時以非零結束（`host-check.py` 是 `load_manifest()`，格式錯時丟出例外）；部署時的 `validate` 用它。
  - exit code 0 代表沒有 `WARN`、1 代表至少一項 `WARN`、2 代表清單格式錯；跨主機的輸出靠每台的 `rc` 分出這三種情形（`rc` 是 Ansible 回報的、那台主機上指令的 return code，執行檢查時就是檢查腳本的 exit code）。
  - 結尾一定印一行 `summary:`；腳本沒有開始或沒有跑完時，靠這一行分辨。
  - 接受 `--manifest <路徑>` 指定清單的位置。
  - `--no-state` 不讀也不寫結果檔。
  - 結果檔放在 `/var/lib/host-check/`，由 `systemd-run` 的 `StateDirectory=host-check` 建立。
  - 在沙箱底下跑得完：`ProtectSystem=strict`、只有 `ReadWritePaths` 列的 `/var/log` 與 `/var/cache/dnf` 兩個目錄（加上 `StateDirectory`）可寫、`IPAddressDeny=any` 擋掉所有網路連線。
  - 給 `runpy` 載入時：模組層級沒有副作用、`__name__` 不是 `__main__` 時不執行主程式、載入函式以丟出例外表達格式錯；主機的 Python 是 3.11 以上（`tomllib`）。
  - 清單的欄位：〈變數檔與範本：檢查腳本實際要求的欄位、兼任兩種角色的主機〉那一節列的欄位與允許值是 `host-check.py` 自己的規格，換腳本時範本換成那支腳本要求的欄位。

  換成自己的腳本時，正文的預期輸出（`PASS`、`WARN`、`MANUAL` 的行格式、`since:` 與 `DELTA`、`manifest error:` 的訊息、`[vars]` 的替換）以那支腳本自己的輸出為準。
- **容器、network 與映像檔的名稱一律 `mh-` 開頭**：清理時 `docker ps -a --filter name=mh-` 這一類查詢列得出這次建的全部資源，開發機上其他專案的容器不會被誤刪。
- **把這個 lab 固定成自動化測試時**：可用的工具是 molecule 的 docker driver，它拿容器當受管主機，依序建立容器、套用 playbook（converge）、執行驗證。這次沒有用 molecule，每一步都手動執行。

## 受管主機與控制端的容器：Oracle Linux 10 加 systemd 與 sshd、python:3.12-slim 加 ansible-core 與 Terraform

受管主機的映像檔以 `oraclelinux:10` 為底，裝 sshd、sudo、Python 與檢查腳本會查的 dnf-automatic，建一個 `ops` 帳號當 Ansible 登入的帳號：

```dockerfile
# host-image/Containerfile：受管主機
FROM oraclelinux:10
RUN dnf -y install systemd procps-ng iproute openssh-server sudo python3 dnf-automatic dnf-plugins-core \
    && dnf clean all \
    && systemctl mask systemd-logind.service getty.target console-getty.service \
    && systemctl enable sshd.service \
    && useradd -m ops \
    && echo 'ops ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/ops && chmod 0440 /etc/sudoers.d/ops
STOPSIGNAL SIGRTMIN+3
CMD ["/usr/sbin/init"]
```

```dockerfile
# ctl-image/Containerfile：控制端
FROM python:3.12-slim
ARG TF_VERSION=1.9.8
# TARGETARCH 由 docker build 依開發機的架構填入（這台是 arm64），Terraform 的壓縮檔名照它選
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client curl unzip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir ansible-core==2.17.7 \
    && curl -fsSLo /tmp/tf.zip https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_${TARGETARCH}.zip \
    && unzip /tmp/tf.zip terraform -d /usr/local/bin && rm /tmp/tf.zip
WORKDIR /work
```

```bash
# 開發機上，在 work/ 的上一層執行；-f 指定檔名，因為檔名是 Containerfile 而 docker build 預設找 Dockerfile
docker build -f host-image/Containerfile -t mh-host:ol10 host-image
docker build -f ctl-image/Containerfile -t mh-ctl:1 ctl-image
docker run --rm mh-ctl:1 sh -c 'ansible --version | head -1; terraform version | head -1'
```

最後一條印出 `ansible [core 2.17.7]` 與 `Terraform v1.9.8`。這台開發機上 `oraclelinux:10` 已經在本機，受管主機的映像檔建了 23 秒；控制端要下載 pip 套件與 Terraform 的壓縮檔，建了 101 秒。兩個時間依網路與本機的快取而變。

受管主機的 Containerfile 最後兩行讓 systemd 當容器的 PID 1：`CMD ["/usr/sbin/init"]` 啟動 systemd，`STOPSIGNAL SIGRTMIN+3` 讓 `docker stop` 送出 systemd 認得的關機訊號。systemd 收到 SIGRTMIN+3 才照正常的關機流程停下各個 unit；Docker 預設送的是 SIGTERM，systemd 不把它當成關機，`docker stop` 會等到逾時再強制結束容器（依 systemd 文件對訊號的說明推論，沒有實跑拿掉這一行的結果）。

**這次遇到的錯誤**：第一次建受管主機的映像檔時套件名寫成 `'dnf-command(needs-restarting)'`，dnf 回 `Unable to find a match`，在 Oracle Linux 10 上 `needs-restarting` 由 `dnf-plugins-core` 提供，`oraclelinux:10` 的映像檔已經裝了它。Containerfile 仍把 `dnf-plugins-core` 寫進安裝清單，讓檢查腳本依賴的套件明示在這一行：換成沒有預裝它的底層映像檔時，建映像檔那一步會裝上它，不會漏掉。

換成 VM 或別的發行版、不開特權、sudo 要密碼、改用別的安裝方式時的結果，在〈這一節的其他做法：容器或 VM、作業系統、遮蔽的 unit、privileged、sudo 密碼、安裝版本與雜湊、金鑰密碼〉。

兩台受管主機與控制端接在同一個 Docker network 上，控制端用容器名就連得到受管主機：

```bash
docker network create mh-net
docker run -d --name mh-web1  --hostname mh-web1  --network mh-net --privileged --cgroupns=private mh-host:ol10
docker run -d --name mh-both1 --hostname mh-both1 --network mh-net --privileged --cgroupns=private mh-host:ol10
docker exec mh-web1 systemctl is-system-running --wait    # 等 systemd 啟動完成，印 running
docker exec mh-both1 systemctl is-system-running --wait
```

`docker network create` 另建一個 network，因為 Docker 預設的 bridge network 不提供容器名的 DNS 解析，接在上面的容器只能用 IP 互連；自建的 bridge network 由 Docker 內建的 DNS 把容器名解析成位址（依 Docker 文件〈Bridge network driver〉，沒有在預設的 bridge 上實跑）。

`--privileged --cgroupns=private` 讓容器裡的 systemd 管得到自己的 cgroup，`systemd-run` 才建得出暫時的 unit（transient unit：執行時由 `systemd-run` 建立、不寫成 unit 檔的 unit）。Docker 在 cgroup v2 的主機上，cgroup namespace 的預設就是 `private`，所以 systemd 能否當 PID 1 啟動，取決於 `--privileged`，`--cgroupns=private` 只是把預設寫明（依 `docker run` 參考文件推論）。拿掉 `--privileged` 時，容器裡的 systemd 管不到自己的 cgroup，PID 1 起不來，或 `systemd-run` 建不出暫時的 unit（從 systemd 文件〈The Container Interface〉對 cgroup 階層的要求推論，沒有實跑）。[主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/) 在同一種容器裡量沙箱的效果時用的就是這組參數。`--privileged` 的代價與不開特權的做法，在〈這一節的其他做法：容器或 VM、作業系統、遮蔽的 unit、privileged、sudo 密碼、安裝版本與雜湊、金鑰密碼〉。

`systemctl is-system-running --wait` 等到 systemd 的啟動結束才印出狀態：`running` 代表啟動完成、沒有失敗的 unit，`degraded` 代表有 unit 失敗，用 `systemctl --failed` 查是哪一個。不加 `--wait`、緊接在 `docker run` 之後執行時，這次印的是 `initializing`、exit code 1，systemd 還在啟動，sshd 可能還沒開始接聽。

兩台各再做三件事，這三件在真主機上分別由建立主機時的設定與服務自己的部署負責，這裡用 `docker exec` 代替：

```bash
# 開發機上執行；<暫存目錄> 換成工作目錄以外的一個暫存目錄，金鑰的用法在〈控制端連到受管主機的 SSH：金鑰、known_hosts 與 sudo〉
mkdir -p <暫存目錄>/keys    # ssh-keygen 不建上層目錄
ssh-keygen -q -t ed25519 -N '' -C mh-walkthrough -f <暫存目錄>/keys/id_ed25519
for h in mh-web1 mh-both1; do
  docker exec $h install -d -m 0700 -o ops -g ops /home/ops/.ssh
  docker cp <暫存目錄>/keys/id_ed25519.pub $h:/home/ops/.ssh/authorized_keys
  docker exec $h sh -c 'chown ops:ops /home/ops/.ssh/authorized_keys && chmod 0600 /home/ops/.ssh/authorized_keys'
  docker exec $h systemctl enable --now dnf-automatic.timer
  docker exec $h systemd-run --unit=stand-in-http python3 -m http.server 80
done
docker exec mh-both1 systemd-run --unit=stand-in-postgres python3 -m http.server 5432
docker exec mh-both1 ss -H -l -n -t
```

- **公鑰**：`ssh-keygen` 在暫存目錄產生一把新的金鑰。暫存目錄要在工作目錄以外：工作目錄整個掛進控制端容器，私鑰放在裡面的話會跟著掛進去，而控制端只需要唯讀掛載的那一份金鑰目錄。`keys` 目錄不存在時它以 `Saving key … failed: No such file or directory` 失敗，所以先 `mkdir -p`。`-N ''` 讓私鑰不設密碼，控制端執行 Ansible 時才不必輸入。雲端主機在建立時由 cloud-init 把公鑰放進預設帳號，這裡用 `docker cp` 手動放。
- **dnf-automatic 的 timer**：清單要求它 `enabled` 而且 `active`，真主機上由部署腳本啟用。
- **代替服務的接聽程式**：web 角色的入口是 80，db 角色是 5432，檢查腳本確認那個連接埠有程序在聽。這次沒有裝 nginx 與 PostgreSQL，用 `python3 -m http.server` 在兩個連接埠上接聽；`systemd-run --unit=` 建的是暫時的 unit，容器重啟之後就不在，〈一台變成 WARN、一台清單格式錯、一台連不上：ansible 的 exit code 與每台的 rc〉那一節正好用到這個性質。

最後一條在 `mh-both1` 上列出 `0.0.0.0:22`、`[::]:22`、`0.0.0.0:80` 與 `0.0.0.0:5432`，另有 Docker 內建 DNS 在 `127.0.0.11` 上的一個 TCP 連接埠（它的另一個連接埠是 UDP，不在 `-t` 的輸出裡）；Docker 內建 DNS 的位址在 loopback 上，檢查腳本的 `listen_audit` 只比對 loopback 以外的位址，所以 DNS 的連接埠不算多開的連接埠。

### 這一節的其他做法：容器或 VM、作業系統、遮蔽的 unit、privileged、sudo 密碼、安裝版本與雜湊、金鑰密碼

- **受管主機用容器**：容器建得快、刪得乾淨，代價是沙箱、SELinux、logind 這幾項跟真主機不同（〈容器跟真主機不同的地方，以及在真主機上要另外確認的項目〉）。換成完整的 VM（Lima、UTM、multipass）或雲端主機時，那一節列的 SELinux、logind 的 session 與持久的 journal 這幾項就量得到，代價是建立與清理都比較慢、雲端主機要計費（推論，這次沒有用 VM 跑）。
- **受管主機的作業系統**：檢查腳本的 `[updates]` 段讀的是 dnf-automatic 的設定檔（INI 格式的 `[commands]` 段），`reboot_check` 用 `dnf needs-restarting -r`，所以選 Oracle Linux；同為 dnf 系的 Rocky Linux、AlmaLinux 同樣適用（推論，沒有實跑）。換成 `debian:12` 這類 Debian 系的映像檔可以少下載一些，代價是 Debian 上沒有 dnf-automatic 的設定檔、timer 與 `dnf` 指令，`[updates]` 那幾項（timer、config、reboot）都不會是 `PASS`，`[updates]` 段要照 unattended-upgrades 的設定改寫，檢查腳本也要跟著改（從腳本的程式碼推的，沒有實跑）。
- **systemd 當 PID 1 與遮蔽的 unit**：檢查要用 `systemd-run` 套沙箱，`[updates]` 也要查 [systemd timer](/linux/dotfile/knowledge-cards/systemd-timer/) 的狀態，所以容器裡要有 systemd。`systemctl mask` 那幾個 unit 是容器裡用不到的登入與終端機服務；遮蔽 `systemd-logind` 的副作用寫在〈容器跟真主機不同的地方，以及在真主機上要另外確認的項目〉。不遮蔽時，logind 會替每次 SSH 登入建一個 session scope，Ansible 模組的紀錄落在那個 scope 底下，`log/sshd` 的最新一筆就不再是 Ansible 的紀錄（推論，這次沒有實跑不遮蔽的版本）。
- **`--privileged` 的代價與不開特權的做法**：`--privileged` 的代價在 Linux 開發機上最明顯：這種容器拿得到主機上所有的裝置與 Linux capability，約等於主機上的 root（[Privileged Container（特權容器）](/backend/knowledge-cards/privileged-container/)；Docker 的 `--privileged` 跟卡上寫的 `securityContext.privileged` 是同一種權限）。這次的 Docker Engine 跑在 OrbStack 的 Linux VM 裡，拿到的是那台 VM 的權限，不是 macOS 本身。不想開特權時，Podman 的 `--systemd=always` 不需要 privileged 也能讓 systemd 當 PID 1（依 Podman 文件，沒有實跑）。
- **`ops` 帳號的 sudo 不要密碼**：Ansible 的 become（`-b`，讓 Ansible 登入之後經由 sudo 切成 root）因此不必另外給密碼。sudo 要密碼的主機，`ansible` 與 `ansible-playbook` 要加 `-K`（`--ask-become-pass`）在執行時輸入，或把密碼放進 Ansible Vault（Ansible 內建的加密功能，把變數檔加密存放、執行時用密碼解開）加密的變數；不給的話 become 那一步失敗（依 Ansible 文件〈Understanding privilege escalation: become〉，沒有實跑）。由排程執行時沒有人輸入，`-K` 用不了；改用 Vault 時，解開 Vault 的密碼檔要放在控制端上，控制端被入侵時密碼檔與私鑰一起被拿走，風險的範圍沒有變小（推論）。
- **ansible-core 與 Terraform 固定版本**：ansible-core 用 `pip install ansible-core==2.17.7`，Terraform 下載 1.9.8 的壓縮檔。改用 apt、pipx 或 HashiCorp 的套件庫安裝時拿到的版本可能不同，版本不同時 `ansible` 與 `terraform` 印出的格式與本文的輸出不保證相同（從版本差異推論，沒有實跑其他版本）。
- **Terraform 的壓縮檔沒有驗證雜湊**：HashiCorp 在同一個目錄放了 `terraform_<版本>_SHA256SUMS` 與它的簽章，下載之後用 `sha256sum -c` 比對，可以確認下載到的檔案沒有被換掉；這次沒有做這一步（依 HashiCorp 的下載頁，沒有實跑）。
- **金鑰不設密碼**：替代做法是設密碼，在控制端起 `ssh-agent` 並 `ssh-add` 解鎖一次：私鑰檔外洩時多一層密碼保護，代價是每次開一個新的 shell 都要先解鎖（推論，沒有實跑）。

## 控制端連到受管主機的 SSH：金鑰、known_hosts 與 sudo

控制端用的金鑰是〈受管主機與控制端的容器：Oracle Linux 10 加 systemd 與 sshd、python:3.12-slim 加 ansible-core 與 Terraform〉那一節在暫存目錄產生的那一把，開發機上自己的金鑰沒有拿來用：這把金鑰只授權給這兩個可拋棄的容器，清理時連同容器一起刪掉。

```bash
# 開發機上；<工作目錄> 是〈前置條件：開發機的資源、檔案配置與檢查腳本〉的工作目錄，<暫存目錄> 是產生金鑰時用的那一個
docker run -d --name mh-ctl --network mh-net -v <工作目錄>:/work -v <暫存目錄>/keys:/keys:ro mh-ctl:1 sleep infinity
docker exec mh-ctl sh -c 'mkdir -p ~/.ssh && cp /keys/id_ed25519 ~/.ssh/ && chmod 600 ~/.ssh/id_ed25519
  for h in mh-web1 mh-both1; do ssh-keyscan -t ed25519 $h; done > ~/.ssh/known_hosts
  for h in mh-web1 mh-both1; do ssh ops@$h "id; sudo -n id -u"; done'
```

`-v <工作目錄>:/work` 把開發機上的工作目錄掛進控制端；金鑰的目錄唯讀掛載，再複製一份進容器改權限，因為 ssh 拒絕權限比 0600 寬的私鑰，而掛載進來的檔案權限照開發機那一份。私鑰複製到 `~/.ssh/id_ed25519`，是 ssh 沒有指定金鑰時預設會試的路徑之一，Ansible 經由 ssh 連線時也就用這一把，inventory 不必另外寫 `ansible_ssh_private_key_file`。最後那個迴圈在 `mh-web1` 上印出 `uid=1000(ops)` 與 `0`：`ops` 登入成功，`sudo -n`（不問密碼，要密碼就直接失敗）切成了 root。這次實跑時這一條只連了 `mh-web1`，`mh-both1` 的登入與 sudo 由後面的 `ansible -b` 指令確認。

`ssh-keyscan` 把兩台主機出示的 host key 直接寫進 `known_hosts`，等於第一次連線時不比對指紋就信任（[SSH Host Key 與 known_hosts（主機金鑰）](/infra/knowledge-cards/ssh-host-key/) 卡寫了首次信任的風險）。在一個只有這三個容器的 Docker network 裡，連線的另一端只可能是這次建的容器，所以這次接受這個風險。改用自己的金鑰、或改用別的方式寫入 `known_hosts` 時的結果，在〈這一節的其他做法：自己的金鑰與寫入 known_hosts 的方式〉。

之後的 Terraform 與 Ansible 指令都在控制端容器裡的 shell 執行，從開發機進入那個 shell：

```bash
# 開發機上；-w 把 shell 的工作目錄設在 /work/ansible
docker exec -it -w /work/ansible mh-ctl bash
```

下文寫「控制端容器裡」的指令都在這個 shell 執行，工作目錄是 `/work/ansible`；Terraform 那幾條在 `/work/tf`，區塊裡先 `cd /work/tf`。

### 這一節的其他做法：自己的金鑰與寫入 known_hosts 的方式

- **用自己的金鑰**：用自己的金鑰也連得上，代價是要把自己的私鑰掛進控制端容器，控制端容器裡的任何程式都讀得到它。
- **`ssh-keyscan` 寫進 `known_hosts`**（這次的做法）：之後的連線都會比對 host key，主機重建、host key 換了時 ssh 拒絕連線。
- **不寫 `known_hosts`**：Ansible 預設檢查 host key，第一次連到沒有紀錄的主機時沒有人回答確認的提問，那一台失敗；在 `ansible.cfg` 設 `host_key_checking = False` 可以跳過，代價是之後每次連線都不比對，連到被冒充的主機也不會發現（依 Ansible 文件〈Connection methods and details〉的〈Managing host key checking〉，沒有實跑）。
- **`StrictHostKeyChecking=accept-new`**（OpenSSH 7.6 起）：第一次連到沒有紀錄的主機時自動把 host key 記進 `known_hosts`，之後 host key 變了照樣拒絕連線；首次連線同樣不比對指紋，跟 `ssh-keyscan` 承擔的是同一個風險，差別是不必先跑一次掃描（依 ssh_config 的文件，沒有實跑）。
- **比對主控台或序列主控台印出的指紋再寫入**：真主機建立時，業者的主控台或序列主控台的開機輸出印得出 host key 的指紋，比對過 `ssh-keyscan` 取回的 host key 再寫進 `known_hosts`，第一次連線也不必無條件信任。代價是每建一台主機都要人工比對一次（這次沒有真主機，沒有實跑）。
- **SSH 憑證：只寫 CA 公鑰**：用 [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/) 簽主機金鑰的環境，`known_hosts` 只要寫一行 CA 的公鑰，新建的主機不必逐台加紀錄；代價是要先建好簽發主機憑證的 CA 與流程（從機制推論，沒有實跑）。

## 由 Terraform 產生 inventory：init、plan、apply 與 local_file 的檔案權限

Terraform 的設定（[HCL](/infra/knowledge-cards/hcl/) 寫成）照 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈主機由 Terraform 建立時由它的輸出產生 inventory〉的寫法，主機改成這次的兩個容器，`all` 群組（Ansible 內建、包含 inventory 裡每一台主機的群組）加上 Ansible 登入用的帳號。跟概念文章那份設定不同的兩處：每台主機的鍵名 `public_ip` 改成 `address`，因為這次填的是容器名、不是 IP；`filename` 指向 `ansible/` 目錄，inventory 寫在 Ansible 的變數檔旁邊。

```hcl
# tf/main.tf
terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "2.5.2" }
  }
}

# 實際的設定裡，address 來自主機資源的屬性（例如 public_ip）；這裡用容器名代替
locals {
  hosts = {
    "mh-web1"  = { roles = ["web"], address = "mh-web1" }
    "mh-both1" = { roles = ["web", "db"], address = "mh-both1" }
  }
}

resource "local_file" "inventory" {
  filename        = "${path.module}/../ansible/inventory.yml"
  file_permission = "0644"
  content = yamlencode({
    all = {
      vars = { ansible_user = "ops" }
      children = {
        for role in distinct(flatten([for h in values(local.hosts) : h.roles])) :
        role => { hosts = { for name, h in local.hosts : name => { ansible_host = h.address } if contains(h.roles, role) } }
      }
    }
  })
}

output "hosts" { value = local.hosts }
```

```bash
# 控制端容器裡
cd /work/tf
terraform init
terraform plan
terraform apply -auto-approve
ansible-inventory -i ../ansible/inventory.yml --graph
terraform output -json hosts
```

`required_providers` 宣告這份設定要用的 provider（Terraform 操作某一類資源的外掛，`hashicorp/local` 管本機的檔案），`terraform init` 依它下載 provider；`${path.module}` 是 `main.tf` 所在的目錄，`filename` 因此指到 `tf/` 旁邊的 `ansible/`。`children` 那兩層 `for` 把「每台主機有哪些角色」反轉成「每個角色有哪些主機」：外層取出不重複的角色，每個角色成為一個群組，內層把角色串列含有這個角色的主機收進那個群組。`apply` 的 `-auto-approve` 跳過執行前的確認提問，這裡用它是因為剛跑過 `plan` 看過內容。

`terraform init` 印出 `Installed hashicorp/local v2.5.2 (signed by HashiCorp)`，花了 8.8 秒（下載 provider 的時間，依網路而變）；[`plan`](/infra/knowledge-cards/terraform-plan-apply/) 印 `local_file.inventory will be created` 與 `Plan: 1 to add`；`apply` 之後，`--graph` 列出 `db` 群組裡有 `mh-both1`、`web` 群組裡有 `mh-both1` 與 `mh-web1`，`mh-both1` 同時在兩個群組裡。產生出來的 `inventory.yml`（以同一份設定在 `hashicorp/terraform:1.9.8` 容器裡另外重跑 `apply` 之後 `cat` 的輸出；`yamlencode` 依鍵名排序，字串一律加引號）：

```yaml
"all":
  "children":
    "db":
      "hosts":
        "mh-both1":
          "ansible_host": "mh-both1"
    "web":
      "hosts":
        "mh-both1":
          "ansible_host": "mh-both1"
        "mh-web1":
          "ansible_host": "mh-web1"
  "vars":
    "ansible_user": "ops"
```

`address` 填的是容器名，Docker network 的內建 DNS 把它解析成容器的位址；真主機上填 `<主機資源>.public_ip` 這類屬性，或主機在私有網路時的私有位址，看控制端從哪一條網路連進去。

`terraform output -json hosts` 印出同一份主機清單的 JSON：`{"mh-both1":{"address":"mh-both1","roles":["web","db"]},"mh-web1":{"address":"mh-web1","roles":["web"]}}`，給 Ansible 以外的工具讀。

`local_file` 的 `file_permission` 預設值是 `"0777"`，實際的檔案權限是它扣掉建立檔案那個程序的 umask。照上面寫了 `file_permission = "0644"` 的設定做時，`inventory.yml` 的權限是 `644`；明寫 `0644` 讓權限不依賴執行環境的 umask，固定讓其他帳號改不了這份檔案。

這一行是這次第一次 apply 之後才加的。這個控制端容器的 umask 是 `0000`，所以沒有寫 `file_permission` 時，`stat -c %a ../ansible/inventory.yml` 印 `777`，同一台機器上的任何帳號都改得了 inventory，也就改得了 Ansible 要以 root 連去的主機清單；另一次在 umask 0022 的容器裡重跑是 `755`。

加上 `file_permission = "0644"` 之後，`plan` 印 `local_file.inventory must be replaced` 與 `file_permission = "0777" -> "0644" # forces replacement`，apply 之後權限是 `644`。

產生出來的檔案不手改。下面這個實驗是可以略過的驗證，用來確認手改會被蓋掉：在 `inventory.yml` 末端加一行 `# 手加的一行` 之後，`plan` 回報 `local_file.inventory will be created`，apply 之後那一行消失（`grep -c` 印 `0`），跟概念文章寫的結果相同。plan 寫的是重新建立，原因是 `local_file` 讀取時發現檔案內容跟 State 記的不同，就把這個資源當成不存在（從 plan 的訊息推論的機制）。

手寫 inventory、動態 inventory、直接讀 State 的 inventory plugin 這幾種做法的結果，在〈這一節的其他做法：產生 inventory 的方式〉。

### 這一節的其他做法：產生 inventory 的方式

產生 inventory 的方式與這次的環境下各自的結果：

- **Terraform 的 `local_file`**（這次的做法）：主機清冊只有 `locals`（真實環境是主機資源）這一個來源，增刪主機時 inventory 跟著改。
- **手寫 inventory**：不需要 Terraform；主機由 Terraform 建立時，增刪主機要在 Terraform 與 inventory 兩邊各改一次，判斷依據在概念文章〈主機由 Terraform 建立時由它的輸出產生 inventory〉。這次沒有實跑手寫的版本。
- **Ansible 的動態 inventory**（雲端業者的 inventory plugin 直接查業者的 API）：主機由 autoscaling 這類服務建立、不在 State 裡時也列得出來，代價是控制端要有讀業者 API 的憑證，分組要依主機的標籤（依 Ansible 文件〈Working with dynamic inventory〉與各業者 plugin 的文件，沒有實跑）。
- **Ansible 的 `cloud.terraform` collection**：它的 inventory plugin 直接讀 Terraform 的 State 列出主機，不寫 `inventory.yml` 這份檔案，也就沒有 `local_file` 的檔案權限與手改被蓋掉這兩件事（依 collection 的文件推論，沒有實跑）。讀 State 與寫檔案兩種做法的判斷依據在概念文章〈主機由 Terraform 建立時由它的輸出產生 inventory〉。

## 變數檔與範本：檢查腳本實際要求的欄位、兼任兩種角色的主機

變數檔照 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈用 Ansible 的 inventory、群組變數與範本產生每台的清單〉的分層：每台相同的寫在 `group_vars/all.yml`，依角色不同的寫在角色的檔案，每台不同的寫在 `host_vars`。

```yaml
# group_vars/all.yml：每台相同的預設值
host_provider: container
host_region: local
min_free_bytes: 1073741824       # 根檔案系統至少留 1 GiB
journal_limit_bytes: 1073741824
update_timer: dnf-automatic.timer
manifest_path: /etc/host-check/host.toml
checker_path: /opt/host-check/host-check.py
ansible_python_interpreter: /usr/bin/python3
```

```yaml
# group_vars/web.yml：web 角色；依角色不同的串列用帶角色名的變數名
web_entrypoints:
  - { name: http, port: 80, exposure: cdn-only }
```

```yaml
# group_vars/db.yml：db 角色
db_entrypoints:
  - { name: postgres, port: 5432, exposure: admin-only }
```

```yaml
# host_vars/mh-web1.yml：只有 mh-web1 不同的值
min_free_bytes: 2147483648       # 這台的根檔案系統至少留 2 GiB
```

`web.yml` 與 `db.yml` 的入口串列用 `web_entrypoints`、`db_entrypoints` 兩個不同的變數名。兩個群組用同一個變數名時，同層的群組依名稱排序合併、後合併的蓋過先合併的，`mh-both1` 少掉一個角色的入口；合併規則與聯集的寫法在概念文章〈用 Ansible 的 inventory、群組變數與範本產生每台的清單〉。

`ansible_python_interpreter` 指定受管主機上的 Python。沒有指定時 Ansible 自己找，每次執行都印一段 `[WARNING]: Platform linux on host mh-web1 is using the discovered Python interpreter at /usr/bin/python3.12`，執行結果相同；指定之後警告消失。`manifest_path` 與 `checker_path` 是清單與腳本在受管主機上的固定位置，playbook 與執行檢查的指令都用這兩個值。清單放在 `/etc/host-check/`，因為 `/etc` 是 FHS 規定放設定檔的位置，主機備份設定檔時會一起收進去。`host_provider` 與 `host_region` 寫進清單 `[host]` 段的 `provider` 與 `region`，這次填 `container` 與 `local`，真主機填業者與區域的名稱；主機分在幾家業者或幾個區域時，這兩個值就從每台相同改成依群組或每台不同。

檢查腳本載入清單時逐欄比對型別與允許的值，所以範本照腳本要求的欄位寫。`host-check.py` 要求的欄位：

- **`[host]` 要有 `name`、`provider`、`region`、`role` 四個字串**：`role` 只收一個字串，兼任兩種角色的主機寫成 `group_names | join(',')`，`mh-both1` 得到 `"db,web"`。`group_names` 是 Ansible 替每台主機算出的所屬群組清單（不含 `all`），依群組名排序；`name` 用的 `inventory_hostname` 是那台主機在 inventory 裡的名字（`mh-web1`、`mh-both1`）。
- **`[listen_audit]` 是 `protocols` 與 `allow`**：允許接聽的連接埠由兩處合起來，`where = "host"` 的每一筆 `[[entrypoint]]` 自動算進去，`allow` 只寫入口以外、刻意允許的連接埠（每一筆是 `{ port, protocol, reason }`）。所以入口的串列取聯集之後，`listen_audit` 就跟著有了兩個角色的連接埠，`allow` 這次是空的。
- **`[[filesystem]]` 的門檻是 `min_free_bytes`**：剩餘空間的位元組數下限。
- **`exposure` 只能是 `public`、`cdn-only`、`admin-only`、`loopback`**：寫了清單外的值（例如 `private`）時，檢查腳本把清單判成格式錯（exit code 2），〈一台變成 WARN、一台清單格式錯、一台連不上：ansible 的 exit code 與每台的 rc〉實測過。
- **`[[entrypoint]]` 要有 `protocol`、`where`、`enforced_by`，每一層防護各一筆 `[[entrypoint.verify]]`**：`enforced_by` 列出這個入口靠哪幾種防護限制來源（雲端防火牆、主機防火牆這類），每一種是一「層」，各寫一筆 `[[entrypoint.verify]]` 說明怎麼確認那一層。`where` 寫在哪裡要確認：`host` 是檢查腳本在主機上自己確認，`console` 是要人到業者主控台確認。這次每個入口寫一層 `cloud-firewall`，`where = "console"`，執行時印成要到主控台確認的 `MANUAL`。
- **`[[log]]`、`[[accumulation]]`、`[updates]`、`[[suspend]]`、`[[resume]]` 都是必填**：少了任何一段，腳本判成格式錯。這次各寫一筆最小的內容。`[[suspend]]` 與 `[[resume]]` 的每一步要寫出主機停下來時還計不計費（`billed_when_stopped` 這幾個欄位）；容器沒有計費，填 `unknown`，欄位的意思在 [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈清單欄位的設計：檢查腳本要讀的與人要讀的〉。

跟概念文章那份範本對照：概念文章的範本是示範值怎麼代入的節錄，鍵名有幾個是那篇自己取的，例如它的 `[[filesystem]]` 用 `warn_percent`（使用率的百分比），檢查腳本不認得這個鍵。

下面是 `ansible/host.toml.j2` 的全文。字串值一律經過 `to_json` 輸出，引號與反斜線由它跳脫，含中文的值加 `ensure_ascii=False` 讓中文原樣寫出；直接輸出時會發生什麼，在概念文章〈值寫進 TOML 的方式：直接輸出、to_json 與 ensure_ascii〉。

```jinja
# 由 Ansible 依 host.toml.j2 產生，不在主機上手改。TOML 1.0。
[vars]
journal_dir = "/var/log/journal"

[host]
name = {{ inventory_hostname | to_json(ensure_ascii=False) }}
provider = {{ host_provider | to_json(ensure_ascii=False) }}
region = {{ host_region | to_json(ensure_ascii=False) }}
role = {{ group_names | join(',') | to_json(ensure_ascii=False) }}

[listen_audit]
protocols = ["tcp"]
allow = []

{% set eps = [{'name': 'ssh', 'port': 22, 'exposure': 'admin-only'}]
   + (web_entrypoints if 'web' in group_names else [])
   + (db_entrypoints if 'db' in group_names else []) %}
{% for ep in eps %}
[[entrypoint]]
name = {{ ep.name | to_json(ensure_ascii=False) }}
port = {{ ep.port }}
protocol = "tcp"
exposure = {{ ep.exposure | to_json(ensure_ascii=False) }}
where = "host"
enforced_by = ["cloud-firewall"]

  [[entrypoint.verify]]
  layer = "cloud-firewall"
  where = "console"
  console_path = "業者主控台 → 網路 → 防火牆規則"
  expect = {{ ("TCP " ~ ep.port ~ " 的規則只對 " ~ ep.exposure ~ " 的來源開放") | to_json(ensure_ascii=False) }}

{% endfor %}
[[log]]
name = "sshd"
source = "journal:sshd.service"
look_for = "登入失敗與不認得的帳號"
interval_days = 7
manual_command = "journalctl -u sshd --since -7d"

[[accumulation]]
name = "journal"
path = ["{% raw %}{{journal_dir}}{% endraw %}"]
missing_ok = true
limit_bytes = {{ journal_limit_bytes }}
purge_command = "journalctl --vacuum-size=500M"

[[filesystem]]
name = "root"
mount = "/"
min_free_bytes = {{ min_free_bytes }}

[updates]
mode = "download-only"
timer = {{ update_timer | to_json(ensure_ascii=False) }}
config_files = ["/etc/dnf/automatic.conf"]
expect = { download_updates = "yes", apply_updates = "no" }
reboot_check = "dnf needs-restarting -r"

[[suspend]]
step = 1
resource = "主機"
billed_when_stopped = "unknown"
billed_when_stopped_beyond_free = "unknown"
billing_basis = "依業者的計費文件"
where = "console"
console_path = "業者主控台 → 主機 → 停止"
verify = "主機的狀態是已停止"

[[resume]]
step = 1
resource = "主機"
billed_when_stopped = "unknown"
billed_when_stopped_beyond_free = "unknown"
billing_basis = "依業者的計費文件"
where = "console"
console_path = "業者主控台 → 主機 → 啟動"
verify = "主機的狀態是執行中"
```

範本裡每台相同的值（ssh 的入口、log、累積的資料、更新的設定、暫停與恢復的步驟）直接寫在範本本身：這些值在所有主機都相同、也不隨角色變，放進 `group_vars/all.yml` 只多一層間接；它開始依群組或主機而變時，才換成變數。依角色不同的入口由 `eps` 那一行依 `group_names` 取聯集，每台不同的只有主機名與 `min_free_bytes`。`[[accumulation]]` 的 `path` 用檢查腳本自己的替換語法 `{{journal_dir}}`，包在 `{% raw %}` 與 `{% endraw %}` 之間，Jinja2 原樣輸出，留給檢查腳本換成 `[vars]` 的值；理由在概念文章〈範本的 {{ }} 與清單自己的替換語法同形〉。

部署到主機之前，先在控制端用 `-c local` 產生一份到 `out/` 看內容：

```bash
# 控制端容器裡，在 /work/ansible 執行；out/ 要先存在
mkdir -p out
ansible all -i inventory.yml -c local -e ansible_python_interpreter=/usr/local/bin/python3 \
  -m template -a "src=host.toml.j2 dest=out/{{ inventory_hostname }}.toml" -o
python3 -c '
import sys, tomllib
for f in sys.argv[1:]:
    d = tomllib.load(open(f, "rb"))
    print(f, d["host"]["role"], [(e["name"], e["port"]) for e in d["entrypoint"]], d["filesystem"][0]["min_free_bytes"], d["accumulation"][0]["path"])
' out/*.toml
```

`ansible` 這一條兩台都印 `CHANGED`，exit code 0。`-m` 指定要執行的模組（這裡是 `template`），`-a` 是給那個模組的參數，`-o` 把每台的結果擠成一行印出。`-c local` 讓 Ansible 在控制端自己身上執行模組，這時「受管主機」就是控制端，而 `group_vars/all.yml` 的 `ansible_python_interpreter`（`/usr/bin/python3`）照樣套用；`python:3.12-slim` 沒有 `/usr/bin/python3`，Python 裝在 `/usr/local/bin/python3`，所以用 `-e` 換成控制端的路徑，不換的話這一條以 exit code 2 失敗。`python3` 那一段用 `tomllib` 讀回兩份清單，印出：

```text
out/mh-both1.toml db,web [('ssh', 22), ('http', 80), ('postgres', 5432)] 1073741824 ['{{journal_dir}}']
out/mh-web1.toml web [('ssh', 22), ('http', 80)] 2147483648 ['{{journal_dir}}']
```

`mh-both1` 有兩個角色的入口，門檻沿用 `all` 的 1 GiB；`mh-web1` 只有 web 的入口，門檻是 `host_vars` 的 2 GiB；兩份的 `path` 都留著 `{{journal_dir}}`。`tomllib` 讀得懂只代表語法正確；要確認欄位是否符合檢查腳本的規格，得讓檢查腳本自己載入一次，〈部署清單：建目錄、copy 與 template、validate 改用檢查腳本的載入函式、--check 的預覽〉裡 template 任務的 `validate` 做的就是這件事。`out/` 的檔案在這個 umask `0000` 的控制端上寫成 `0666`；它們只用來預覽，看完刪掉即可。省略這一步時的結果，在〈這一節的其他做法：省略本機的預覽〉。

### 這一節的其他做法：省略本機的預覽

這一步可以省略，直接部署也會寫出同樣的內容；先在本機產生一份的好處是不連任何主機就看得到每台的清單，改範本時可以先比對 `out/` 裡新舊兩份的差異。

## 部署清單：建目錄、copy 與 template、validate 改用檢查腳本的載入函式、--check 的預覽

部署有三個任務：建放腳本與清單的目錄、把檢查腳本複製過去、依範本寫出每台的清單。三個任務都要以 root 寫進 `/opt` 與 `/etc`，所以整個 play 設 `become: true`，Ansible 以 `ops` 登入後經由 sudo 切成 root。

```yaml
# deploy.yml
- hosts: all
  become: true
  tasks:
    - name: 放腳本與清單的目錄
      ansible.builtin.file:
        path: "{{ item }}"
        state: directory
        owner: root
        group: root
        mode: "0755"
      loop:
        - "{{ checker_path | dirname }}"
        - "{{ manifest_path | dirname }}"
    - name: 檢查腳本
      ansible.builtin.copy:
        src: files/host-check.py
        dest: "{{ checker_path }}"
        owner: root
        group: root
        mode: "0755"
    - name: 每台的清單（寫出之前用檢查腳本自己的載入函式驗證）
      ansible.builtin.template:
        src: host.toml.j2
        dest: "{{ manifest_path }}"
        owner: root
        group: root
        mode: "0644"
        validate: >-
          python3 -I -c 'import runpy, sys;
          runpy.run_path(sys.argv[1], run_name="hc")["load_manifest"](sys.argv[2])'
          {{ checker_path }} %s
```

建目錄的任務用 `loop` 對串列裡的每一項各執行一次，每一次的值放在 `item`；`dirname` 過濾器取路徑的上層目錄，`/opt/host-check/host-check.py` 得到 `/opt/host-check`。`validate: >-` 是 YAML 的折疊寫法：底下幾行接成一行、行與行之間換成空白、結尾不留換行，長指令可以分行寫。

```bash
# 控制端容器裡
ansible-playbook -i inventory.yml deploy.yml --check --diff   # 預覽，不寫任何檔案
ansible-playbook -i inventory.yml deploy.yml
```

加上 `file` 任務之後，第一次執行三個任務都是 `changed`，再執行一次 `changed=0`，花 1.9 秒（兩台，控制端與主機在同一台開發機上，真主機要加上網路來回的時間）。

**這次遇到的錯誤**：建目錄的任務是第一次實跑失敗之後加的。最初的 playbook 只有 copy 與 template 兩個任務，`--check --diff` 預覽時兩台都回報 `changed=2`、`failed=0`；實際執行時兩台都在 copy 那一步失敗，訊息是 `Destination directory /opt/host-check does not exist`，exit code 2。copy 與 template 都不建上層目錄（template 單獨執行時同樣以 `Destination directory … does not exist` 失敗，另外單獨實跑過一次確認），而 check 模式沒有實際寫檔，碰不到這個錯誤，所以預覽的 `failed=0` 不代表實際執行會成功。

**`validate` 用的是檢查腳本自己的載入函式**。[多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈產生時驗證清單與比對主機上的清單〉的 `validate` 範例只用 `tomllib` 解析，驗得到語法、驗不到欄位。`host-check.py` 的 `load_manifest()` 讀清單並逐欄驗證，格式錯時丟出 `ManifestError`，不執行任何檢查，所以 `validate` 用 `runpy.run_path` 載入腳本、只呼叫這個函式：函式丟出例外時 Python 以 exit 1 結束，Ansible 判成驗證失敗，那一台的清單維持原樣。

- **用 `runpy.run_path` 載入腳本**：腳本開頭有 `from __future__ import annotations`，`dataclass` 要從 `sys.modules` 找到這個模組。`runpy.run_path` 執行期間會把它登記進去，`run_name="hc"` 讓腳本結尾的 `if __name__ == "__main__"` 不成立，`main()` 不會跑。
- **`%s` 與 `{{ checker_path }}`**：`%s` 由 Ansible 換成暫存檔的路徑，`{{ checker_path }}` 換成上一個任務放好的腳本。`validate` 在受管主機上執行，用的是主機上的 Python 與主機上那一份腳本，所以 copy 的任務要排在 template 之前，主機上的 Python 也要是 3.11 以上（`tomllib`）。
- **`-I`**：Python 的隔離模式，忽略所有 `PYTHON*` 環境變數，不把目前目錄與使用者的 site-packages 加進模組的搜尋路徑；執行 `validate` 時的工作目錄裡放了 `json.py` 這類跟標準函式庫同名的檔案，也不會取代標準函式庫被載入。

**這次遇到的錯誤**：寫進 `validate` 之前，先在控制端拿 `out/` 的兩份清單試載入；最初用 `importlib.util.spec_from_file_location` 載入，在腳本的 `@dataclass` 那一行丟出 `AttributeError: 'NoneType' object has no attribute '__dict__'`，因為那樣載入的模組沒有登記進 `sys.modules`。

**check 模式不執行 `validate`**：另外在一個裝 ansible-core 2.17.7 的容器裡，以 `-c local` 對一個 template 任務設 `validate` 指向一條一定 exit 1、執行時會留下紀錄的指令，`--check --diff` 回報 `changed`、exit code 0，紀錄檔沒有出現；拿掉 `--check` 實際執行時以 `failed to validate` 失敗、exit code 2，紀錄檔有那一行。所以會被 `validate` 擋下的清單，`--check` 的預覽照樣顯示成功。

`--check --diff` 對 copy 任務會印出整份腳本的差異（這次一千多行），清單的差異埋在後面；只想看清單時，用〈一台變成 WARN、一台清單格式錯、一台連不上：ansible 的 exit code 與每台的 rc〉那一節的 ad-hoc 指令，只對 template 模組跑 `--check --diff`。

`validate` 的其他寫法、逐台驗證造成的部分部署、copy 任務的替代，在〈這一節的其他做法：validate 的寫法、部分部署與 copy 的替代〉。

### 這一節的其他做法：validate 的寫法、部分部署與 copy 的替代

這個 `validate` 擋得下的範圍在下面〈一台變成 WARN、一台清單格式錯、一台連不上：ansible 的 exit code 與每台的 rc〉實測過一次：db 角色寫了 `exposure: private` 時，只有 `mh-both1` 驗證失敗、維持舊的清單，`mh-web1` 照常部署。三種寫法的差別：

- **檢查腳本的載入函式**（這次的做法）：型別、允許的值、必填欄位、白名單都在寫出之前驗過，主機上不會出現一份腳本拒絕載入的清單。需要腳本有這樣的函式，而且 `validate` 依賴腳本內部的函式名，腳本改名時這一行要跟著改。
- **只用 `tomllib`**：只要求主機上有 Python 3.11 以上，不依賴腳本的內部；`exposure = "private"` 這種語法正確、值不允許的寫法會被寫到主機上，等下一次執行檢查時腳本以 exit code 2 結束（`exposure = "private"` 是合法的 TOML，所以 `tomllib` 照常解析，這一點是從 TOML 的語法推的，沒有另外實跑）。
- **不寫 `validate`**：寫壞的清單直接上主機。〈一台變成 WARN、一台清單格式錯、一台連不上：ansible 的 exit code 與每台的 rc〉那一節在主機上手改清單的實驗就是這個結果：那台主機在修好之前一項檢查都沒有跑。

`validate` 逐台執行，一台驗證失敗時其他台照常寫出新版，結果是部分部署：這次 `exposure: private` 那一輪，`mh-web1` 照常部署、`mh-both1` 留在舊版；範本的改動同時涉及兩台時，兩台就會停在不同的版本。要全部主機一起成功或一起不動時，有兩種替代：先在控制端用 `-c local` 產生全部主機的清單，用同一個載入函式驗完再部署；或在 play 設 `any_errors_fatal: true`，有一台失敗就停下整個 play（兩種都是推論，沒有實跑；`any_errors_fatal` 停的是之後的任務，失敗那一刻之前已經寫出的主機不會退回）。

copy 那一個任務另有兩種做法：把檢查腳本放進主機的映像檔，或打包成套件由套件管理員安裝。兩種都讓腳本的版本跟著映像檔或套件的版本走，代價是改腳本要重建映像檔或重新打包；打包成 rpm 時，另外換到 `rpm -V` 查得出主機上那一份腳本有沒有被改過。這次腳本與清單一起由 Ansible 部署，改腳本與改範本是同一個步驟。這一點是從部署的流程推的，沒有實作另外兩種。

## 以 -b 與 systemd-run 執行檢查腳本：每台的輸出與 ansible 的 exit code

執行檢查之前，先確認 `systemd-run` 的限制在這次的容器裡有沒有套上：[主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/) 記錄過 OrbStack 的 LXC 機器會讓限制靜默無效。

```bash
# 控制端容器裡
ansible all -i inventory.yml -b -m command -a "systemd-detect-virt" -o
ansible mh-web1 -i inventory.yml -b -m command -a "systemd-run --wait --pipe --collect -p ProtectSystem=strict touch /var/x"
```

`systemd-detect-virt` 兩台都印 `docker`（Docker 容器；LXC 環境印的是 `lxc`）；`touch /var/x` 那一條在 `mh-web1` 上以 `rc=1` 失敗，輸出 `/bin/touch: cannot touch '/var/x': Read-only file system`，`ProtectSystem=strict` 套上了。印的是 `lxc`、或 `touch` 成功時，這個環境量不到沙箱的效果，真主機上的確認方式在〈容器跟真主機不同的地方，以及在真主機上要另外確認的項目〉。這一條的 `ansible` 指令本身以 exit code 2 結束，是預期的結果：`rc=1` 正是要看到的失敗（整批的 exit code 怎麼讀，在 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈用 Ansible 對多台主機執行檢查腳本：整批的 exit code、每台的 rc 與執行身分的代價〉）。

執行檢查的指令寫成一支小腳本，屬性照 TOML 那一篇〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉的 `systemd-run` 寫法。這次量輸出時 `check.sh` 寫的是固定路徑 `/opt/host-check/host-check.py` 與 `/etc/host-check/host.toml`，跟下面用變數的版本代入之後的值相同：

```bash
#!/bin/bash
# check.sh：對 inventory 的每台主機以 root、在 systemd 沙箱裡執行檢查腳本；"$@" 接其他 ansible 參數（例如 --limit）
ansible all -i inventory.yml -b -m command -o -a "systemd-run --wait --pipe --collect \
  -p ProtectSystem=strict -p 'ReadWritePaths=/var/log /var/cache/dnf' \
  -p StateDirectory=host-check -p StateDirectoryMode=0700 \
  -p NoNewPrivileges=yes -p PrivateTmp=yes -p IPAddressDeny=any \
  python3 {{ checker_path }} --manifest {{ manifest_path }}" "$@"
```

`check.sh` 建在控制端的 `/work/ansible`（開發機上是工作目錄的 `ansible/`），建好之後在控制端容器裡加上執行權限，下文以 `./check.sh` 執行：

```bash
chmod +x check.sh
```

要依環境換的位置只有 `all`（要檢查的主機範圍）。腳本與清單的路徑寫成 `{{ checker_path }}` 與 `{{ manifest_path }}`，Ansible 執行時用每台主機的變數代入，跟部署時用的是同一組值；寫死路徑的話，`group_vars` 改了位置而 `check.sh` 沒改時，檢查會安靜地讀舊路徑上過期的清單。`command` 模組用 `shlex` 切參數、不經過 shell，所以 `'ReadWritePaths=/var/log /var/cache/dnf'` 的單引號讓兩個路徑留在同一個參數裡。變數代入與引號的切法另外在一個裝 ansible-core 2.17.7 的容器裡，以 `-c local` 對設了這兩個變數的 localhost 實跑過一次：`{{ checker_path }}` 與 `{{ manifest_path }}` 換成了變數的值，`'ReadWritePaths=/var/log /var/cache/dnf'` 留在同一個參數裡。不加 `--manifest` 時，腳本讀它自己所在目錄的 `host.toml`，這次清單放在 `/etc/host-check/`，所以要寫。

讀下面的輸出之前，先把兩個 exit code 分開：`ansible` 指令本身的 exit code 是整批的結果，每台的 `rc` 是那台主機上檢查腳本的 exit code。

| `ansible` 指令的 exit code（整批） | 代表                                     |
| ---------------------------------- | ---------------------------------------- |
| 0                                  | 每台的任務都成功                         |
| 2                                  | 至少一台主機的任務失敗（標成 `FAILED!`） |
| 4                                  | 有主機連不上（標成 `UNREACHABLE!`）      |

| 每台的 `rc`（檢查腳本的 exit code） | 代表            |
| ----------------------------------- | --------------- |
| 0                                   | 沒有 `WARN`     |
| 1                                   | 至少一項 `WARN` |
| 2                                   | 清單格式錯      |

讀的順序：先看整批的值決定要不要告警，再看每台的 `rc` 決定處置；`rc` 是 1 時另看輸出裡有沒有 `summary:` 那一行。

`./check.sh` 第一次執行，`ansible` 的 exit code 是 0，花 0.9 秒。兩台都印 `CHANGED | rc=0`；`command` 模組不論指令做了什麼一律回報 changed，所以這個 `CHANGED` 只代表指令執行了，不代表檢查改動了主機。`-o` 把每台的報告印成一行、換行寫成 `\n`；要看分行的報告時，拿掉 `-o` 再跑一次（`ansible all -i inventory.yml -b -m command -a "…"`，指令照 `check.sh`），每台的 stdout 會分行印出。`mh-both1` 的報告：

```text
PASS   entrypoint/ssh:22/tcp  有程序在聽（0.0.0.0, [::]），exposure=admin-only
MANUAL entrypoint/ssh:22/tcp/cloud-firewall  [主控台] 業者主控台 → 網路 → 防火牆規則 → 預期：TCP 22 的規則只對 admin-only 的來源開放
PASS   entrypoint/http:80/tcp  有程序在聽（0.0.0.0），exposure=cdn-only
MANUAL entrypoint/http:80/tcp/cloud-firewall  [主控台] 業者主控台 → 網路 → 防火牆規則 → 預期：TCP 80 的規則只對 cdn-only 的來源開放
PASS   entrypoint/postgres:5432/tcp  有程序在聽（0.0.0.0），exposure=admin-only
MANUAL entrypoint/postgres:5432/tcp/cloud-firewall  [主控台] 業者主控台 → 網路 → 防火牆規則 → 預期：TCP 5432 的規則只對 admin-only 的來源開放
PASS   listen-audit  loopback 以外只有清單列出的連接埠在聽（tcp）
PASS   log/sshd  最新一筆：2026-10-26T13:44:47+00:00 mh-both1 python3[1904]: ansible-ansible.legacy.command Invoked …；每 7 天讀一次：journalctl -u sshd --since -7d
PASS   accumulation/journal  路徑不存在，算 0 bytes（/var/log/journal）
PASS   filesystem/root  / 剩 77.7 GiB／共 117.6 GiB（下限 1.0 GiB）
PASS   updates/dnf-automatic.timer/is-enabled  enabled（預期 enabled）
PASS   updates/dnf-automatic.timer/is-active  active（預期 active）
PASS   updates/config  download_updates = yes, apply_updates = no（mode download-only，讀了 /etc/dnf/automatic.conf）
PASS   updates/reboot  不需要重開機
since: 沒有前一次的結果（/var/lib/host-check/last.json）
summary: 11 PASS, 0 WARN, 3 MANUAL（phase maintain，/etc/host-check/host.toml）
```

`mh-web1` 少了 postgres 的兩行，結果是 `10 PASS, 0 WARN, 2 MANUAL`，`filesystem/root` 的下限印成 `2.0 GiB`。`summary:` 裡的 `phase maintain` 是這次跑的檢查階段：檢查腳本分維護（`maintain`，預設）、暫停（`suspend`）與恢復（`resume`）三種階段，這次跑的是維護。報告之後的 stderr 是 `systemd-run` 印的那一次執行的資料：`Finished with result: success`、`Service runtime: 378ms`、`Memory peak: 79M`。三個值得讀的位置：

- **`accumulation/journal` 判成 `PASS` 而路徑不存在**：`[[accumulation]]` 寫了 `missing_ok = true`，這個容器的 [journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/) 只把 journal 存在記憶體裡（`/run/log/journal`），`/var/log/journal` 沒有建出來。`path` 那一格印出 `/var/log/journal`，代表檢查腳本把 `{{journal_dir}}` 換成了 `[vars]` 的值。
- **`log/sshd` 的最新一筆是 Ansible 自己留下的**：`ansible-ansible.legacy.command Invoked` 是這次執行檢查時 Ansible 的模組寫進 journal 的紀錄，而它被算在 `sshd.service` 底下，所以「journal 裡有 sshd 的紀錄」這一項由檢查的執行本身滿足。成因寫在〈容器跟真主機不同的地方，以及在真主機上要另外確認的項目〉。
- **結果檔**：`/var/lib/host-check` 是 `700`、`last.json` 是 `600`，擁有者都是 root，`StateDirectoryMode=0700` 生效了。第二次執行時 `since:` 那一行印出上一次的時間，量到的值都跟前一次相同時接著印 `，與前一次相同`（`since: <上一次的時間>，與前一次相同`），後面沒有其他行；`DELTA <項目> 舊值 → 新值（差）` 這種行只在量到的值變了時出現，例如〈一台變成 WARN、一台清單格式錯、一台連不上：ansible 的 exit code 與每台的 rc〉把門檻改成 1 TiB 的那一輪。

不加 `-b`、不經過 `systemd-run`、改由每台的 timer 執行、接上排程時讀結果的方式，以及沙箱屬性寫在 `check.sh` 的代價，在〈這一節的其他做法：-b、systemd-run、執行的位置、排程讀結果與屬性的住址〉。

### 這一節的其他做法：-b、systemd-run、執行的位置、排程讀結果與屬性的住址

執行檢查這一步，在 `-b`、`systemd-run` 與執行的位置上各有替代。「不加 `-b`」與「不加 `-b`、也不經過 `systemd-run`」只對 `mh-web1` 跑過，指令是：

```bash
# 控制端容器裡；不加 -b：check.sh 那一條拿掉 -b，只對 mh-web1
ansible mh-web1 -i inventory.yml -m command -o -a "systemd-run --wait --pipe --collect \
  -p ProtectSystem=strict -p 'ReadWritePaths=/var/log /var/cache/dnf' \
  -p StateDirectory=host-check -p StateDirectoryMode=0700 \
  -p NoNewPrivileges=yes -p PrivateTmp=yes -p IPAddressDeny=any \
  python3 /opt/host-check/host-check.py --manifest /etc/host-check/host.toml"
# 不加 -b、也不經過 systemd-run：以 ops 直接執行檢查腳本
ansible mh-web1 -i inventory.yml -m command -o -a "python3 /opt/host-check/host-check.py --manifest /etc/host-check/host.toml --no-state"
```

- **不加 `-b`**：`systemd-run` 以 `ops` 執行，`ansible` 把 `mh-web1` 標成 `FAILED!`、`rc` 是 1，stderr 是 `Failed to start transient service unit: Access denied`，檢查腳本沒有執行，`ansible` 的 exit code 是 2。這個 `rc` 跟檢查腳本「至少一項 `WARN`」的 exit code 1 相同，只看 `rc` 分不開，要看輸出裡有沒有 `summary:` 那一行：腳本跑完一定印它，沒有這一行代表腳本沒有跑完或沒有開始。
- **不加 `-b`、也不經過 `systemd-run`**（以 `ops` 直接執行檢查腳本；`--no-state` 不讀也不寫結果檔，這次的測試因此不改到 root 那份 `last.json`）：腳本照常跑完，stderr 印 `note: 不是 root，journal、audit.log 與 collector 的目錄可能讀不到（會印成 WARN）`，結果是 `9 PASS, 1 WARN, 2 MANUAL`，多出來的 `WARN` 是 `log/sshd`（`ops` 讀不到 journal）。這次的清單只有少數幾項需要 root；TOML 那一篇的完整清單在專用帳號（加了 `systemd-journal` 與 `adm` 兩個群組的非 root 帳號）下，從 37 項 `PASS` 掉到 29 項。
- **以 root 執行而不套 `systemd-run`**：這次沒有跑。結果依 TOML 那一篇的量測：檢查照常，dnf 的 log 與 sqlite 的 `-shm` 這類工具自己的寫入不再被擋下，檢查過程會在主機上留下寫入，只讀的保證沒有了。
- **Ansible 集中執行，或每台用自己的 timer 執行**：這次用的是 Ansible 集中執行。[多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈用 Ansible 對多台主機執行檢查腳本：整批的 exit code、每台的 rc 與執行身分的代價〉寫了集中執行的代價：控制端握有能 SSH 登入每台、再切成 root 的憑證。這次的 `ops` 帳號是 `NOPASSWD: ALL`，控制端的這把私鑰就等於兩台的 root。
- **接上排程時讀結果的方式**：`-o` 的一行輸出要用 `grep` 分出每台的 `rc`。設 `ANSIBLE_STDOUT_CALLBACK=json` 時，`ansible` 改印一份 JSON，每台的 `rc` 與 stdout 是其中的欄位，排程的腳本可以直接取值，代價是輸出不再適合人直接讀；改寫成 playbook，在任務上設 `failed_when: result.rc not in [0, 1]`（`result` 是 `register` 存下的結果），`WARN` 的 `rc=1` 就不算失敗，整批的 exit code 只在清單格式錯或腳本沒跑起來時變成 2，代價是 `WARN` 要另外從輸出裡讀（兩種都是推論，沒有實跑）。

沙箱的屬性寫在 `check.sh` 裡有一個代價：同一組屬性在主機自己的 timer unit 裡還有一份，收緊其中一份時漏改另一份，沒有任何訊號。替代做法是把屬性放在主機上的一支包裝腳本或一個靜態的 service unit 裡，`check.sh` 與 timer 都呼叫它，屬性只有一份（推論，沒有實跑）。

## 一台變成 WARN、一台清單格式錯、一台連不上：ansible 的 exit code 與每台的 rc

這一節依序製造門檻造成的 `WARN`、清單格式錯（被 `validate` 擋下的與在主機上手改的）、連不上的主機，每一種情形看 `ansible` 指令本身的 exit code，以及每台的標記與 `rc`。

**門檻讓 `mh-web1` 變成 `WARN`**。把 `host_vars/mh-web1.yml` 的 `min_free_bytes` 改成 1 TiB（`1099511627776`），行尾的註解 `# 這台的根檔案系統至少留 2 GiB` 一起改成 1 TiB，之後讀這個檔的人才不會被舊的註解誤導。部署之前先只對 template 預覽：

```bash
# 控制端容器裡
ansible all -i inventory.yml -b -m template -a "src=host.toml.j2 dest=/etc/host-check/host.toml" --check --diff
```

`mh-both1` 印 `SUCCESS`、`"changed": false`；`mh-web1` 印 `--- before: /etc/host-check/host.toml` 與 `+++ after:` 兩邊的差異，只有一行從 `-min_free_bytes = 2147483648` 換成 `+min_free_bytes = 1099511627776`，標成 `CHANGED`。這條指令的 exit code 是 0，有主機標成 `CHANGED` 時也是 0，所以拿它定期比對主機上的清單時，要讀輸出裡有沒有 `CHANGED`，只看 exit code 看不出哪一台的清單跟範本不同；判斷依據在 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈產生時驗證清單與比對主機上的清單〉。以 `ansible-playbook -i inventory.yml deploy.yml` 部署之後，再跑 `./check.sh`：

```text
mh-both1 | CHANGED | rc=0 | (stdout) …summary: 11 PASS, 0 WARN, 3 MANUAL…
mh-web1 | FAILED! => {"changed": true, … "rc": 1, … "msg": "non-zero return code", …}
```

`ansible` 的 exit code 是 2。`mh-web1` 的報告裡是 `WARN   filesystem/root  / 剩 77.7 GiB／共 117.6 GiB（下限 1024.0 GiB）`、`CHANGED filesystem/root  PASS→WARN` 與 `summary: 9 PASS, 1 WARN, 2 MANUAL`。`-o` 對成功的主機印一行 `CHANGED | rc=0 | (stdout) …`，對失敗的主機把整份結果印成一行 JSON，`rc` 是 JSON 裡的一個欄位，所以用 `grep` 分出每台的 `rc` 時，兩種形式都要比對。

**db 角色的 `exposure` 寫成 `private`，被 `validate` 擋下**。把 `group_vars/db.yml` 的 `admin-only` 改成 `private` 再跑 `ansible-playbook -i inventory.yml deploy.yml`：exit code 2，`mh-both1` 在 template 那一步失敗，`"msg": "failed to validate"`，stderr 的最後一行是 `hc.ManifestError: entrypoint[postgres]: exposure 要是 ['public', 'cdn-only', 'admin-only', 'loopback'] 之一，實際是 'private'`；`mh-web1` 不在 db 群組，`failed=0`。`mh-both1` 上的 `/etc/host-check/host.toml` 仍是上一版，三個 `exposure` 都沒有 `private`。把 `group_vars/db.yml` 改回 `admin-only`；主機上的清單沒有被改到，這裡不必重新部署。

**在主機上手改清單，檢查腳本以 exit code 2 結束**。`validate` 擋下的是 Ansible 寫出的那一份；有人在主機上直接改檔，或另一條部署路徑沒有 `validate` 時，壞掉的清單照樣在主機上。用 `sed` 把 `mh-both1` 清單裡的 `exposure = "admin-only"` 改成 `exposure = "private"`，ssh 與 postgres 兩個入口都改到：

```bash
# 開發機上執行：在 mh-both1 上直接改清單
docker exec mh-both1 sed -i 's/exposure = "admin-only"/exposure = "private"/' /etc/host-check/host.toml
```

`mh-web1` 維持 1 TiB 的門檻，再跑 `./check.sh`：

| 主機       | `-o` 的標記 | `rc` | 報告                                                                                                                                   |
| ---------- | ----------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `mh-both1` | `FAILED!`   | 2    | stderr 兩行 `manifest error: entrypoint[…]: exposure 要是 … 之一，實際是 'private'`，最後一行 `manifest error: 2 項，沒有執行任何檢查` |
| `mh-web1`  | `FAILED!`   | 1    | `summary: 9 PASS, 1 WARN, 2 MANUAL`                                                                                                    |

`ansible` 的 exit code 是 2。兩台都標成 `FAILED!`，`rc` 分別是 2 與 1：`mh-both1` 在修好清單之前一項檢查都沒有跑，`mh-web1` 跑完了檢查、有一項 `WARN`（這次是門檻寫錯）。整批的 exit code 與每台的 `rc` 各自用來決定什麼，判斷依據在概念文章〈用 Ansible 對多台主機執行檢查腳本：整批的 exit code、每台的 rc 與執行身分的代價〉。接著依序做四件事，把兩台帶回全部 `PASS`：

1. **比對主機上的清單**：用門檻那一段只對 template 跑的 `--check --diff` 指令。`mh-both1` 標成 `CHANGED`，差異是兩行 `-exposure = "private"` 換成 `+exposure = "admin-only"`；`mh-web1` 是 `SUCCESS`，範本與主機上的門檻都是 1 TiB。exit code 0。
2. **門檻改回 2 GiB**：`host_vars/mh-web1.yml` 的 `min_free_bytes` 與註解改回 `2147483648` 與 2 GiB。
3. **重新部署**：`ansible-playbook -i inventory.yml deploy.yml`。這一步同時照範本把 `mh-both1` 的清單寫回 `admin-only`。不重新部署、只在主機上改回時，替代做法是在開發機上跑反向的 `sed`：`docker exec mh-both1 sed -i 's/exposure = "private"/exposure = "admin-only"/' /etc/host-check/host.toml`；已經重新部署的話不必跑。
4. **再跑 `./check.sh`**：exit code 回到 0，`mh-web1` 的報告多一行 `CHANGED filesystem/root  WARN→PASS`。

**`mh-web1` 連不上**。在開發機上 `docker stop mh-web1` 之後跑 `./check.sh`：exit code 4，花 0.6 秒；`mh-web1` 印 `UNREACHABLE!: Failed to connect to the host via ssh: ssh: Could not resolve hostname mh-web1: Name or service not known`，沒有 `rc`；`mh-both1` 照常 `CHANGED | rc=0`。停掉的容器從 Docker network 的 DNS 消失，所以錯誤是解析不到主機名；真主機關機或網路斷了時，錯誤多半是連線逾時或被拒，exit code 同樣是 4（依 ansible-core 2.17.7 的原始碼 `lib/ansible/executor/task_queue_manager.py` 的 `RUN_*` 常數與這次的結果推論，真主機的訊息沒有實測）。同一次執行裡一台失敗、一台連不上時，依 ansible-core 2.17.7 的原始碼（`plugins/strategy/__init__.py`），有主機連不上時優先回 4，沒有才回 2；這次沒有實跑。照本文做不會同時出現兩種情形；排程裡同時有連不上與 `FAILED!` 時才用得到。

在開發機上 `docker start mh-web1`，等 systemd 啟動完成、sshd 開始接聽之後（`docker exec mh-web1 systemctl is-system-running --wait`），再跑一次 `./check.sh`：exit code 2，`mh-web1` 的 `rc` 是 1，報告是 `WARN   entrypoint/http:80/tcp  沒有程序在聽這個連接埠，exposure=cdn-only` 與 `CHANGED entrypoint/http:80/tcp  PASS→WARN`：代替 nginx 的 `stand-in-http` 是 `systemd-run` 建的暫時的 unit，容器重啟之後沒有被拉起來。這跟真主機重開機之後某個服務沒有設成開機啟動是同一種結果，清單裡寫了那個入口，它就被報出來。在開發機上重新起代替的接聽程式之後，`./check.sh` 回到 exit code 0：

```bash
# 開發機上執行
docker exec mh-web1 systemd-run --unit=stand-in-http python3 -m http.server 80
```

這次各情形的整批 exit code 與每台的結果：

| 情形                              | `ansible` 的 exit code（整批） | 每台的標記與 `rc`（每台）                          |
| --------------------------------- | ------------------------------ | -------------------------------------------------- |
| 全部 `PASS` 與 `MANUAL`           | 0                              | 兩台 `CHANGED`、`rc=0`                             |
| 一台的門檻造成 `WARN`             | 2                              | 該台 `FAILED!`、`rc` 1；另一台 `rc=0`              |
| 一台清單格式錯、另一台有 `WARN`   | 2                              | 兩台都 `FAILED!`，`rc` 分別是 2 與 1               |
| 一台連不上                        | 4                              | 該台 `UNREACHABLE!`、沒有 `rc`；另一台 `rc=0`      |
| 不加 `-b`，`systemd-run` 起不來   | 2（只對 `mh-web1` 跑）         | 該台 `FAILED!`、`rc` 1，輸出沒有 `summary:`        |
| `--check --diff` 比對出清單被改過 | 0                              | 該台 `CHANGED`，輸出有 `--- before` 與 `+++ after` |

## 容器跟真主機不同的地方，以及在真主機上要另外確認的項目

照著在容器上做完不需要這一節；要把同樣的部署搬到真主機時，逐項確認。這次的受管主機是容器，有幾項結果在真主機上會不同，照著做在真主機上時，下面每一項要另外確認一次：

- **沙箱有沒有套上**：這次的容器 `systemd-detect-virt` 印 `docker`，`ProtectSystem=strict` 底下 `touch /var/x` 回 `Read-only file system`。在 OrbStack 的 Linux machine 這類 LXC 環境裡同一條 `touch` 會成功、而且不報錯（[主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)〈只讀檢查腳本的白名單、輸出、exit code 與結果檔〉記錄的 OrbStack Linux machine 實測），所以真主機上照樣先跑 `systemd-detect-virt` 與 `touch /var/x` 那兩條，再執行檢查。
- **SELinux**：容器裡沒有 SELinux（[Mandatory Access Control（強制存取控制）：SELinux 與 AppArmor](/linux/dotfile/knowledge-cards/mandatory-access-control/)），`getenforce` 這類檢查與 SELinux 對 `systemd-run` 執行的程序的限制都沒有量到。Oracle Linux 與 RHEL 的真主機預設是 enforcing（依 RHEL 文件〈Using SELinux〉，這次沒有在真主機上確認），部署到 `/opt/host-check` 的腳本由 `systemd-run` 執行時，SELinux 是否拒絕它的存取，要在真主機上跑一次檢查，再用 `ausearch -m avc -ts recent` 查有沒有拒絕的紀錄。
- **`log/sshd` 被 Ansible 自己的紀錄滿足**：容器遮蔽了 `systemd-logind`，SSH 登入之後的程序留在 `sshd.service` 的 cgroup 裡，Ansible 模組寫進 journal 的紀錄因此算在 `sshd.service` 底下。真主機上 logind 會替每個登入建一個 `session-<編號>.scope`，那些紀錄落在 session 底下（從 logind 的機制推的，沒有在真主機上比對）；在真主機上用 `journalctl -u sshd -n 5` 看最新幾筆是 sshd 自己的紀錄還是 Ansible 的，確認這一項量的是 sshd。
- **雲端防火牆**：清單裡每個入口的 `cloud-firewall` 那一層都是 `MANUAL`，這次沒有任何雲端資源可以比對。主機與規則由 Terraform 建立時，`terraform plan` 比對得到與比對不到的範圍在 [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)〈清單裡要到主控台確認的項目與 terraform plan 的比對範圍〉。
- **主機防火牆**：容器裡沒有 firewalld，清單也沒有寫主機防火牆那一層；真主機的清單在 `enforced_by` 加上 `firewalld`，並在那一層的 `[[entrypoint.verify]]` 寫 `where = "host"` 與探針（`command` 欄位寫要執行的 `firewall-cmd --query-*` 指令，`expect_exit` 這類欄位寫什麼結果算通過）。
- **journal 只在記憶體裡**：這次的容器與 Oracle Cloud 的 Oracle Linux 10.2 映像檔預設都只把 journal 存在記憶體（[長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)〈journald 的紀錄存在記憶體還是磁碟〉），`/var/log/journal` 不存在，`accumulation/journal` 以 `missing_ok` 判成 `PASS`。開了 `Storage=persistent`、或發行版預設建了 `/var/log/journal` 的主機（Debian 系；同一節寫了 Debian 12、13 與 Ubuntu 24.04 的 systemd 套件在安裝時建立這個目錄，以及在 Oracle Cloud 的 Ubuntu 24.04 映像檔上的確認）上，這一項才量得到實際大小，1 GiB 的上限要照那台主機的磁碟與 `SystemMaxUse=` 重訂。
- **連線位址與延遲**：`ansible_host` 這次是容器名，部署 1.9 秒、檢查 0.9 秒都沒有經過真正的網路；真主機上 `ansible_host` 填 IP 或 DNS 名稱，時間會加上每台的 SSH 連線。
- **sudo 與 host key**：這次的 `ops` 是 `NOPASSWD: ALL`，`known_hosts` 由 `ssh-keyscan` 直接寫入，兩者在真主機上都要重新決定；host key 的做法在〈這一節的其他做法：自己的金鑰與寫入 known_hosts 的方式〉，sudo 要密碼時的做法在〈這一節的其他做法：容器或 VM、作業系統、遮蔽的 unit、privileged、sudo 密碼、安裝版本與雜湊、金鑰密碼〉。

## 清理：terraform destroy、容器、network、映像檔與金鑰

清理的順序是先 `terraform destroy`、再刪容器：destroy 要在控制端容器裡執行，控制端先刪掉的話 Terraform 不在了，State 留在工作目錄裡沒有人處理。這次 State 只記著一份本機檔案；真環境的 State 記著雲端主機，先 destroy 才不會留下還在計費的資源。

```bash
# 開發機上
docker exec -w /work/tf mh-ctl terraform destroy -auto-approve   # 印 Destroy complete! Resources: 1 destroyed.
docker rm -f mh-ctl mh-web1 mh-both1
docker network rm mh-net
docker rmi mh-host:ol10 mh-ctl:1
docker ps -a --filter name=mh- -q; docker network ls --filter name=mh- -q; docker images 'mh-*' -q; docker volume ls --filter name=mh- -q
rm -rf <工作目錄> <工作目錄的上一層>/host-image <工作目錄的上一層>/ctl-image <暫存目錄>/keys
```

`terraform destroy` 刪掉的是 `local_file.inventory`，之後在開發機上 `ls <工作目錄>/ansible/inventory.yml` 回 `No such file or directory`。`docker ps -a --filter name=mh- -q` 那一行的四條查詢都沒有輸出，代表這次建的容器、network、映像檔與 volume 都清掉了（這次的容器沒有掛 named volume，`docker volume ls` 那一條是確認沒有遺漏）。`docker build` 留下的建置快取沒有清：清快取要用 `docker builder prune`，它不分是哪一次建置留下的，會一起清掉開發機上其他專案的快取，所以這次留著。底層映像檔 `oraclelinux:10` 與 `python:3.12-slim` 也留著：開發機上可能有別的專案在用它們，要刪時執行 `docker rmi oraclelinux:10 python:3.12-slim`。工作目錄裡有 Terraform 的 State 與產生的清單、暫存目錄裡有私鑰，`host-image/` 與 `ctl-image/` 是兩個映像檔的建置目錄，`rm -rf` 那一行把它們一起刪掉；`<工作目錄>`、`<工作目錄的上一層>` 與 `<暫存目錄>` 換成這次實際用的路徑，刪之前先 `ls` 一次確認是這次建的目錄。

## 延伸閱讀：分層與合併的判斷依據、清單的欄位與檢查腳本、Terraform 與 Ansible 的卡

- [多台主機的維護清單：值的分層與合併的位置、用 Ansible 的 inventory 與範本產生每台的清單、由 Terraform 的輸出產生 inventory、跨主機執行的 exit code，以及單台清單的適用範圍](/operations/09-host-lifecycle/multi-host-manifest/)：每台相同、依角色不同、每台不同的分類、合併放在部署時的理由、`to_json` 的跳脫與 YAML 的隱式型別、exit code 2 與 4 的讀法與集中執行的安全代價
- [主機維護清單寫成 TOML：JSON、YAML、TOML 的取捨、TOML 1.0 與 1.1 的版本差異、清單的欄位設計與只讀檢查腳本](/operations/09-host-lifecycle/host-manifest-in-toml/)：清單每一段的欄位、檢查腳本的白名單、`systemd-run` 各屬性在 Oracle Linux 10 容器上的實測效果與結果檔
- [Configuration Management（組態管理）](/infra/knowledge-cards/configuration-management/)：inventory、群組變數與主機變數各放什麼；同一個變數在幾層都有值時的合併順序，在概念文章〈用 Ansible 的 inventory、群組變數與範本產生每台的清單〉
- [State（IaC 狀態檔）](/infra/knowledge-cards/state/)：IaC 工具記錄每個納管資源上一次 apply 之後樣貌的快照，以及它的存放位置、加密與鎖機制
- [terraform plan / apply](/infra/knowledge-cards/terraform-plan-apply/)：plan 比對 State、雲端現況與設定檔產出差異報告而不改動任何資源，apply 執行那份差異；手改的 inventory 被 plan 判成重新建立的機制，在概念文章〈主機由 Terraform 建立時由它的輸出產生 inventory〉
