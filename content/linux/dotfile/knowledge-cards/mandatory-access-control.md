---
title: "Mandatory Access Control（強制存取控制）：SELinux 與 AppArmor"
date: 2026-10-26
description: "檔案權限看起來正確、程式以 root 執行，存取仍然被拒絕；從備份還原或搬移檔案之後服務回 403；或在 log 裡讀到 avc: denied、apparmor=\"DENIED\" 時"
weight: 58
tags: ["dotfile", "linux", "security", "selinux", "knowledge-cards"]
---

強制存取控制（mandatory access control，MAC）是作業系統核心依一份系統層級的政策決定程序能存取什麼的機制：政策寫出「哪一類程序可以對哪一類檔案、連接埠做什麼」，核心在每一次存取時比對，政策沒有准許的一律拒絕，檔案的擁有者與 root 都不能自己放寬。Linux 一般的檔案權限（擁有者、群組、`rwx`）是自主存取控制（discretionary access control，DAC），由檔案的擁有者決定；兩層都通過，存取才成立。Linux 上常見的兩種實作是 SELinux（Oracle Linux、RHEL、Fedora 預設啟用）與 AppArmor（Ubuntu、Debian 預設啟用）。兩者的拒絕紀錄都要從 log 裡讀：SELinux 寫進 audit log，AppArmor 寫進核心訊息，核心訊息經由 [journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/) 用 `journalctl -k` 查得到。

## 概念位置

MAC 在一台對外服務的主機上負責的是程序被入侵之後的範圍：nginx 的程序被利用時，DAC 只看它以哪個使用者執行，MAC 另外把它限制在政策准許 web 伺服器碰的檔案與連接埠裡。代價是一類 DAC 看不出原因的拒絕：`ls -l` 的權限都對、程式也找得到檔案，存取照樣失敗。長期上線的主機上，拒絕紀錄要定期讀（AppArmor 的那一份在 [journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/) 收下的核心訊息裡），正常值是零，見 [長期上線主機的維護項目：會累積的資料、定期讀的 log、對外入口的盤點、安全更新、會到期的設定與檢查間隔的推算](/operations/09-host-lifecycle/long-running-host-maintenance/)〈定期讀的 log：每一份要看的欄位與它代表的狀態〉；從備份還原之後要核對的標籤，見 [服務暫停與恢復上線：只停服務、停止主機、終止主機到全部刪除各自保留的資源，暫停期間仍計費與仍被指向的資源，恢復前要查的漂移與恢復的順序](/operations/09-host-lifecycle/suspend-and-resume-service/)。

## 可觀察訊號

- 服務回 403 或 permission denied，而 `ls -l` 顯示的擁有者與權限允許這次存取。
- SELinux：`getenforce` 印出 `Enforcing`（拒絕並記錄）、`Permissive`（只記錄不拒絕）或 `Disabled`；拒絕紀錄寫進 audit log，`ausearch -m AVC -ts recent` 列出最近的 `avc: denied` 紀錄，每一筆寫出被拒絕的動作、程序的標籤（`scontext`）與目標的標籤（`tcontext`）。
- AppArmor：`aa-status` 列出載入的設定檔與它們的模式；拒絕紀錄在核心 log 裡，`journalctl -k | grep 'apparmor="DENIED"'` 列得出來。

## 設計責任

SELinux 的判斷依據是標籤：每個檔案、程序、連接埠都帶一個標籤，`ls -Z` 與 `ps -Z` 讀得到，政策寫的是標籤之間的規則（web 伺服器的程序 `httpd_t` 可以讀 `httpd_sys_content_t` 的檔案）。所以 SELinux 的拒絕多半是標籤不對，而標籤錯掉最常發生在檔案搬動的時候：

- **`mv` 保留原本的標籤**：從家目錄 `mv` 到 `/var/www` 的檔案仍然帶著家目錄的標籤，nginx 讀不到；`cp` 建的是新檔，取目的地目錄的預設標籤。
- **從備份還原**：`tar` 沒有帶 `--selinux` 這類保留延伸屬性的選項、或備份存在不支援延伸屬性的位置時，還原出來的檔案不帶原本的標籤。
- **修法是依政策重設標籤，不是關掉 SELinux**：`restorecon -Rv <目錄>` 依政策把檔案的標籤改回那個路徑的預設；網站放在政策不認得的路徑時，先用 `semanage fcontext` 登記那個路徑該有的標籤，再跑 `restorecon`。程序要做政策預設不准的事（nginx 往外連到後端）時，改的是對應的布林開關（`setsebool -P httpd_can_network_connect on`）。`setenforce 0` 把整台主機切到 Permissive，拒絕全部消失，防護也一起消失，只適合用來確認問題是不是 SELinux 造成的。

AppArmor 的判斷依據是路徑：每個程式的設定檔寫出它能存取哪些路徑，不帶標籤，所以搬動檔案不會改變它的判斷；網站放到設定檔沒寫的路徑時，改的是那個程式的設定檔。

這張卡的指令與行為取自 SELinux 與 AppArmor 的官方文件與 RHEL 的 SELinux 指南，沒有在本站的主機上逐一實跑。

## 鄰卡

- [journald（systemd-journald）](/linux/dotfile/knowledge-cards/journald/)
- [Docker Named Volume Ownership（掛載點擁有者）](/linux/dotfile/knowledge-cards/docker-named-volume-ownership/)
