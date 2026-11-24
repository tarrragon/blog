-- 領域乙（cloud-academy）：PostgreSQL 18 正式環境角色、最小權限、PII 隔離與多租戶 RLS 參考腳本
-- 用途：補足 SQLite 無法演示的資料庫角色隔離、逾時護欄與企業多租戶列級安全政策
-- 對照教材：1.21〈資安、權限與合規決定的資料表設計〉
-- 執行前提：已由管理帳號執行 schema_pg.sql；第 3 節把所有物件的擁有者移交給遷移角色。
-- 驗證：verify_pg.py 會在 PostgreSQL 實跑本檔並檢查權限與 RLS 行為。

-- 1. 收緊 public schema 預設權限（PG 15+ 新建資料庫預設已撤銷，舊版升級或還原 dump 仍須顯式執行）
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 2. 依職責切分群組角色（NOLOGIN）與實際連線帳號（LOGIN）
CREATE ROLE academy_migrator    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE academy_app         NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE academy_bi_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE academy_audit_ro    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE academy_view_owner  NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; -- 受控檢視表擁有者（見 bookstore/security_pg.sql 第 2 節）

CREATE ROLE academy_migrator_login LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE IN ROLE academy_migrator;
CREATE ROLE academy_app_login      LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE academy_app;
CREATE ROLE academy_bi_login       LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE academy_bi_readonly;
CREATE ROLE academy_audit_login    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS IN ROLE academy_audit_ro;

-- 備份專用唯讀帳號：因表啟用 FORCE ROW LEVEL SECURITY，預設 pg_dump（SET row_security = off）
-- 對 NOBYPASSRLS 角色會直接報錯中止，須以專用 BYPASSRLS 唯讀帳號執行備份
CREATE ROLE academy_backup_ro      LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;

-- 3. 物件擁有者：資料表、序列與函式歸遷移角色，受控檢視表歸檢視表擁有者
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE %I OWNER TO academy_migrator', r.tablename);
  END LOOP;
END;
$$;
ALTER FUNCTION reject_audit_mutation() OWNER TO academy_migrator;
ALTER VIEW v_learner_analytics OWNER TO academy_view_owner;
ALTER VIEW v_valid_sessions    OWNER TO academy_view_owner;
GRANT USAGE ON SCHEMA public TO academy_view_owner;
GRANT SELECT ON users, user_sessions, user_credentials TO academy_view_owner;

-- 4. 依可登入角色（LOGIN）設定 SQL 層 DoS 執行逾時與交易閒置護欄
-- ALTER ROLE ... SET 僅於 LOGIN 角色建立新連線當下套用（NOLOGIN 群組不繼承、不影響既有池連線）
-- （以下秒數皆為示範值，正式環境須依服務 P99 延遲與報表長尾耗時量測決定）
ALTER ROLE academy_app_login      SET statement_timeout                   = '3s';
ALTER ROLE academy_app_login      SET lock_timeout                        = '1s';
ALTER ROLE academy_app_login      SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE academy_bi_login       SET statement_timeout                   = '30s';
ALTER ROLE academy_bi_login       SET lock_timeout                        = '2s';
ALTER ROLE academy_migrator_login SET statement_timeout                   = '0';
ALTER ROLE academy_migrator_login SET lock_timeout                        = '2s';

-- 5. 最小權限授權：應用角色具業務表讀寫權，但不可改動或刪除權限稽核表
GRANT USAGE ON SCHEMA public TO academy_app, academy_bi_readonly, academy_audit_ro, academy_backup_ro;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  users, user_pii, user_credentials, user_sessions,
  organizations, org_memberships, roles, permissions, role_permissions, user_roles,
  courses, course_contents, tags, course_tags,
  subscriptions, invoices, lesson_progress, certificates, webhook_events
TO academy_app;
GRANT SELECT ON v_valid_sessions TO academy_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO academy_app;

REVOKE UPDATE, DELETE, TRUNCATE ON permission_audit_logs FROM academy_app;
GRANT SELECT, INSERT ON permission_audit_logs TO academy_app;
GRANT SELECT ON permission_audit_logs TO academy_audit_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO academy_backup_ro;

-- 6. BI 角色完全禁止讀取 user_credentials、user_sessions、user_pii 與含 email 的 users 原表
-- 含列過濾條件的受控檢視表（v_valid_sessions）加上 security_barrier = true；v_learner_analytics 只投影欄位，不需要
REVOKE ALL ON users, user_pii, user_credentials, user_sessions FROM academy_bi_readonly;
ALTER VIEW v_valid_sessions SET (security_barrier = true);
GRANT SELECT ON v_learner_analytics, courses, tags, course_tags, subscriptions, invoices, lesson_progress, certificates
TO academy_bi_readonly;

-- 7. 新建物件預設權限（PG 18 TABLES 預設已對 PUBLIC 零權限；撤銷 FUNCTIONS 預設對 PUBLIC 開放的 EXECUTE）
ALTER DEFAULT PRIVILEGES FOR ROLE academy_migrator_login IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- 8. 企業租戶 RLS：org_memberships 與企業 subscriptions 強制受目前請求的 app.current_org_id 隔離
-- 連線池環境中每次請求須於明確交易（BEGIN ... COMMIT）內執行 SET LOCAL app.current_org_id = '<verified_id>';
-- 若要求漏設租戶變數時當場報錯（fail-loud）而非靜默回 0 列，可改省略 NULLIF(..., '') 直接轉型。
ALTER TABLE org_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_memberships FORCE ROW LEVEL SECURITY;

CREATE POLICY p_org_memberships_tenant ON org_memberships
  FOR ALL TO academy_app
  USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer)
  WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;

CREATE POLICY p_subscriptions_tenant_or_self ON subscriptions
  FOR ALL TO academy_app
  USING (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
    OR (
      org_id IS NOT NULL
      AND org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
    )
  )
  WITH CHECK (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
    OR (
      org_id IS NOT NULL
      AND org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
    )
  );

-- BI 已被授與 subscriptions 的 SELECT，但表啟用了 FORCE RLS：沒有任何政策適用於 BI 角色時，預設拒絕會讓 BI 靜默讀到 0 列。
-- 平台分析需要跨租戶的訂閱彙總（以 user_id 假名串接，不含個資），所以顯式給 BI 一條唯讀政策。
CREATE POLICY p_subscriptions_bi_read ON subscriptions
  FOR SELECT TO academy_bi_readonly
  USING (true);
