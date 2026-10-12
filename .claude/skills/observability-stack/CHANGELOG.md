# observability-stack 版本紀錄

新到舊。版號的兩個住址是本檔與 `SKILL.md` frontmatter 的 `metadata.version`。

**Version**: 1.0.0 — 初版：自架指標監控的設計、實作與驗收。流程（盤點訊號、決定監控位置、實作、驗收、告警）、各層訊號與看不到的範圍、監控所在層的盲區（虛擬機、共用主機）、告警（可用性與延遲分開、條件持續、依原因抑制與其盲區、序列消失不能當停止訊號）、讀數字的兩條規則；references 收各層 exporter 的接法與實測遇到的問題、三項驗收與故障注入。來源是一次在 Docker Compose（OrbStack）上接 Prometheus 3.15.0、Grafana 13.2.3、cAdvisor v0.55.1、node_exporter 1.12.1、postgres_exporter 0.20.1、redis_exporter 1.93.0、nginx-prometheus-exporter 1.5.0 的實作與驗收
