# 起一個可拋棄的乾淨環境

golden-path-validation 階段 3 的冷讀執行,需要每個目標一個**可拋棄的乾淨環境**——起得快、丟得掉、每次都從同一個乾淨起點。這份講怎麼起、有哪些坑,最後給一個公開的 reference implementation。

## 兩種 flavor,別搞混

- **bare(給 cold-read 用)**:純淨 base image、什麼工具都沒預裝。cold-read 測試的整個重點是「陌生人在一台全新機器上照指引能不能成功」——若環境已經預裝了指引要裝的東西,就測不到那些安裝步驟成不成立。**cold-read fixture 一定要 bare。**
- **provisioned(給操作者當 scratch 用)**:先跑專案自己的可重現 setup(裝好工具鏈)、得到一個「可用」的拋棄式環境,給你臨時試東西 / debug 用。這**不是** cold-read fixture(它已經不乾淨了),是操作便利。

## 硬規則

- **原生、非模擬**:架構敏感的行為(sandbox、seccomp、LSM、syscall)在 CPU 模擬層跟原生不同。別隨手拉一個非本機架構的 image 走模擬(很多 image 只發布單一架構、docker 會 warning 但照跑)。明確挑目標架構的原生 image。理由見 `principles/native-not-emulated.md`。
- **命名 + 清理**:`docker run --rm`(退出即刪)給一次性;要重複進就給名字、用完 `docker rm -f`。別留一堆 `scratch-*` 容器。
- **非互動**:自動化裡起的環境沒有 TTY,互動提示(apt、pacman、chsh)會 hang。設 `DEBIAN_FRONTEND=noninteractive`、套件管理器用 `--noconfirm` / `-y`、每步加 timeout、hang 記為 finding。

## 容器專屬的坑(會遮住真結果)

容器的安全 profile 跟真機不同,有些失敗只在容器出現、真機無關——要隔離,別當成指引的 bug(見 `principles/native-not-emulated.md` 末段):

- **pacman 7 在容器內 Landlock sandbox 失敗**:`switching to sandbox user 'alpm' failed` / `Landlock ruleset could not be applied`。在 `/etc/pacman.conf` 加 `DisableSandbox`(只在容器 fixture、別進真機設定)。
- **root 容器無 sudo**:base image 常以 root 起手且無 sudo,指引 / 腳本硬編 `sudo` 會 `command not found`(exit 127)。這本身可能是指引的 bug(該偵測 root),但起環境時要知道這個常態。

## 一步 provision:用專案的可重現 setup

若受測專案本身是可重現的(一個 repo + 一支冪等 install 腳本),起一個 bare 容器、在裡面 clone 該 repo + 跑它的 install,就得到一個 provisioned scratch——這正好也順手驗了那支 install 腳本在乾淨環境跑不跑得起來。

**Concrete reference implementation(公開)**:[`tarrragon/dotfiles`](https://github.com/tarrragon/dotfiles) 有兩支可讀範例。`scripts/scratch.sh <debian|arch> [--provision] [--keep]` 起單一可拋棄環境:預設 bare(給 cold-read),`--provision` 則裝好該 repo 得到可用環境;arch 在 arm64 主機自動選原生 Arch Linux ARM image、並處理上面那些容器坑(DisableSandbox、`-Syu`)。`scripts/validate.sh [all|debian|arch]` 則把整個「執行核心」串起來:對每個目標起 bare 容器、用 `git archive HEAD` 把 repo 放進去(只含 tracked 檔、天然排除機密)、跑 install + verify、assert 綠燈、exit code 回報——這支就是本方法「可執行核心」對一個真實 repo 的實現(那個 repo 把自己當成本 skill 的 reference implementation)。要在別的專案複用,把它當骨架、把 install / verify 那兩行換成你自己專案的可重現 setup 與檢查即可——pattern 通用,repo 只是公開範例。
