# 遠端機器的操作

這份分冊管在 VM 或本專案管理的遠端機器上驗證與部署時的規則：狀態的改動經由 dotfiles repo、SSH 的用途與禁用的選項、dotfiles 的部署工具，以及各類檔案的部署方式。推送照 `AGENTS.md`〈推送〉，dotfiles 也一樣直接推送。

## 遠端機器的操作

在 VM 或任何本專案管理的遠端機器上做驗證或部署時，狀態的改動一律經由 [dotfiles repo](https://github.com/tarrragon/dotfiles) 與 git 同步，不經由 SSH 手動放置持久的檔案或設定。機器的狀態要能從 repo 重現，手放的檔案下次重裝就消失，也沒有人記得它存在。

- **SSH 只用來做唯讀診斷與觸發**：`hyprctl`、`systemctl status`、讀 log、`pgrep`、執行 repo 內的部署腳本。
- **ssh 指令不帶 `-o ProxyCommand=…`、`-o LocalCommand=…` 與 `PermitLocalCommand=yes`**：這幾個選項會在本機這台開發機執行任意命令，而「遠端環境壞了可以重建」這個前提保護不到本機。Claude Code 另有 hook 攔下這幾個選項（見 CLAUDE.md），其他 agent 沒有，靠這一條。
- **該持久存在的檔案**（腳本、systemd unit、設定檔、cron、drop-in）先寫進 dotfiles repo、commit 與 push，再由遠端 `git pull` 加冪等的 deploy 部署。不用 scp、不用 heredoc 寫進 /tmp、不手動 `tee` 到 /etc。
- **一次性驗證用的暫時檔**（探測腳本、測試用的 systemd unit）可以臨時放，名稱一律用 `verify-` 開頭，測完清掉，正式版收回 repo。腳本放在 `/tmp/verify-…`；unit 檔放不進 `/tmp`（systemd 只從 `/etc/systemd/system/`、`~/.config/systemd/user/` 這類目錄載入，`systemctl link` 也會在那裡留下 symlink），所以只用名稱的前綴標記。收尾時跑兩條檢查，任一條有輸出就是還沒清的暫時檔：`ssh <host> 'find /tmp -maxdepth 1 -name "verify-*"'`（不用 `ls -d /tmp/verify-*`：遠端的預設 shell 是 zsh，沒有匹配時 zsh 自己印 `no matches found`，清乾淨了反而有輸出），與 `ssh <host> "systemctl list-unit-files 'verify-*' --no-legend"`（user unit 另外加 `--user` 跑一次）；清不掉的照 `AGENTS.md`〈延到工作結束之後的動作〉寫進最後一則總結。固定的前綴讓「暫時」是一個查得到的事實，不是放置者自己的標籤。

dotfiles repo 裡的工具：

| 工具                                         | 作用                                                                                                       |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `scripts/remote-sync.sh <host> [deploy-cmd]` | 本地先自己 commit；腳本 push → 遠端 `git pull --ff-only` → 遠端執行冪等的 deploy；本地有未提交的變更就中止 |
| `scripts/install.sh`                         | bootstrap：套件 → stow 部署 → zsh → Claude Code（家目錄層，冪等）                                          |
| `<pkg>/deploy.sh`                            | 系統層（`/etc`、`/usr/local`）的部署，stow 管不到的用這個（如 `monitoring/deploy.sh`）                     |

```bash
# 在 dotfiles clone 的根目錄執行；本地改動先 commit
scripts/remote-sync.sh <host>                                  # 跑完整的 install.sh
scripts/remote-sync.sh <host> 'sudo ./monitoring/deploy.sh'    # 只部署某個系統層套件
```

兩個引數：`<host>` 填 `~/.ssh/config` 裡那台機器的 `Host` 名稱；第二個引數是要在遠端執行的 deploy 指令，不給時跑完整的 `install.sh`。這支腳本在 dotfiles repo 裡，blog repo 的 `scripts/` 沒有它，所以要先切到 dotfiles 的 clone 再跑。

遠端停在 feature 分支、無法 fast-forward 時，在 repo 端把分支收斂：本地 checkout 該分支、`git merge main`、解衝突、push，遠端再 `git pull --ff-only`。不用 `git checkout <ref> -- <paths>` 把檔案放進遠端的工作區：它會把那些路徑 staged 進 index，下一次 ff-pull 會被「index 有未提交變更」擋下。stow 部署過的設定檔改內容不需要重新 stow，symlink 會自動反映。

檔案的分類：

- **家目錄檔**（`~/.config/...`、`~/.local/bin/...`）：做成 stow 套件，由 `install.sh` 部署。
- **系統檔**（`/etc/systemd/system/...`、`/usr/local/bin/...`，root 擁有、stow 管不到）：套件內附 `deploy.sh`，在目標機用 `sudo` 執行，冪等安裝。
- **私密值**（ntfy topic、healthcheck UUID、token）：不進 git。repo 只放 `.example` 佔位，deploy 只在目標不存在時建立佔位檔，真值手動填入或放在 gitignore 的本地檔。
- **app 自己以原子寫入管理的設定檔**（如 caelestia 的 `shell.json`：程式會把 stow 的 symlink 換成實檔，`stow --adopt` 還會把程式改寫過的內容複製回 repo）：不用 stow，改用複製部署。套件內附 `deploy.sh`，以一般使用者 `cp` repo 版蓋過 live 檔，並從 stow 套件清單移除該套件。repo 是唯一真實來源：持久的設定改 repo 再部署，不用該 app 的 GUI 改（會寫進 live 檔，下次部署被覆蓋）。判斷訊號：部署之後該檔從 symlink 變成實檔，或內容被程式重新排過。
