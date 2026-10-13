# observability-stack 版本紀錄

新到舊。版號的兩個住址是本檔與 `SKILL.md` frontmatter 的 `metadata.version`。

**Version**: 1.5.2 — 虛擬機裡掛入的主機磁碟：大小差固定倍數也是主機的磁碟，位元組不可信、只用剩餘比例（OrbStack 2.2.3 的 virtiofs 區塊大小欄位與區塊數單位不同，node_exporter 的位元組放大 256 倍）

**Version**: 1.5.1 — 翻譯探針指出的歧義：探測類 `host` 填被探測端點所在的主機、`relabel_configs` 的句構、Kubernetes 上 `node` 標籤加到哪一側的序列

**Version**: 1.5.0 — 多輪審查 Round 4：主機飽和改用 5 分鐘平均的 load（原始 load1 加 for 實測不成立）；原因與症狀在觸發與恢復兩端對齊，原因加 `keep_firing_for`；延遲探測改看慢探測比例（15 分鐘 30 個樣本取分位數近於取最慢的幾次）；嚴重度分工寫明（可用性與 burn rate 通知值班、固定門檻延遲為 warning）與分組的代價；`host` 指症狀發生的主機，layer-signals 新增〈主機標籤〉（本機 exporter、探測、Pushgateway、Kubernetes 兩側）；Watchdog route 補 `group_interval`；合成告警的標籤從各規則運算式查、對照組用不帶篩選的查詢確認；容器停止的標籤查詢改列全部容器並改寫 `min` 的說明；外部探測的通知與 Alertmanager 分工；Kubernetes 分支修正 cAdvisor 的理由與 AlertmanagerConfig 的 namespace 比對；Windows CPU 改用不受語言影響的指令；PSI 不限實體主機；監控資源的估算方法

**Version**: 1.4.0 — 多輪審查 Round 3：盤點加「元件歸誰管」（第三方軟體的延遲從入口取、受管服務一層）；主機外的訊號寫明跑在哪裡、單位是被監控的整個範圍，估算監控自己的資源；驗收前先跑主機檢查，門檻使用者沒給時不自訂；告警加來源失效三條、間歇條件先聚合再 `for`、主機飽和以 `or` 納入 steal 並排除 throttling、抑制只壓 warning 症狀而 critical 改 `group_by`、原因 `for` 不長於症狀、多台主機用 relabel 的 `host` 標籤（`instance` 不是主機）、Watchdog route 的 `repeat_interval`、容器停止看不到沒有序列的服務；Kubernetes 的分支移到 layer-signals；verification 改為比較基準來自部署設定、注入前中後三個值、移除「或調低門檻」、合成告警標籤從實際告警抄並送不該被抑制的對照、加主機外通知與 Watchdog 兩列、驗收紀錄的「未驗」一節

**Version**: 1.3.0 — 多輪審查 Round 2 修正：入口檔寫明從流程表第一列開始、驗收三項寫出成員、實作列補 Prometheus 的 `rule_files` 與 `alerting`；盤點表補「看不到」欄；盲區段引言與條目數對齊，前置檢查獨立成〈量測前的主機檢查〉並補核心數與 Windows 的看法；Watchdog 寫明 `vector(1)` 與送出者；依原因抑制拆成盲區、多台主機（附 `equal` 範例）、嚴重度、只擋通知四項；steal 與 `rate()`；檢查、重新載入、確認的順序；〈讀數字〉改名並補 `rate()` 範例；description 補告警內容與觸發詞。layer-signals：連接埠綁定寫成部署設定、重新建立與重新啟動用語一致、語法檢查在重新載入之前、未實測環境的 socket 查法、做完的去處。verification：CPU 注入的 exec 寫法與無 sh 映像的替代、開連線的指令與加總、還原指令、磁碟告警一列、合成告警的完整指令、注入期間雜訊的判斷、做完的去處

**Version**: 1.2.0 — 多輪審查 Round 1 修正：容器停止規則補 PromQL 區塊並寫明 `min` 套在差值上；抑制補多台主機的 `equal` 與嚴重度方向；盲區拆成 CPU、磁碟、主機前置檢查三條（磁碟改給列出各顆的查法，主機磁碟寫滿停機限定為 OrbStack 實測）；Prometheus 全停改用心跳消失偵測；盤點表欄位寫明；layer-signals 補應用程式層的盲區、containerd-debug.sock、Alertmanager 以 `/-/reload` 重新載入；verification 改用只列被抑制告警的查詢、補合成告警的標籤條件與注入秒數的依據、範例去專案名

**Version**: 1.1.0 — 修正盲區的磁碟說法：虛擬機裡可能看得到主機的磁碟（OrbStack 以 virtiofs 掛入），磁碟告警依裝置分組、涵蓋主機那一顆；容器停止的規則依服務取最小值（重建時舊序列停止前進，取最大值會誤報，實測 161 秒對 10 秒）；layer-signals 補磁碟告警分組與規則的重新載入；verification 補重建不誤報與以合成告警驗證抑制規則

**Version**: 1.0.0 — 初版：自架指標監控的設計、實作與驗收。流程（盤點訊號、決定監控位置、實作、驗收、告警）、各層訊號與看不到的範圍、監控所在層的盲區（虛擬機、共用主機）、告警（可用性與延遲分開、條件持續、依原因抑制與其盲區、序列消失不能當停止訊號）、讀數字的兩條規則；references 收各層 exporter 的接法與實測遇到的問題、三項驗收與故障注入。來源是一次在 Docker Compose（OrbStack）上接 Prometheus 3.15.0、Grafana 13.2.3、cAdvisor v0.55.1、node_exporter 1.12.1、postgres_exporter 0.20.1、redis_exporter 1.93.0、nginx-prometheus-exporter 1.5.0 的實作與驗收
