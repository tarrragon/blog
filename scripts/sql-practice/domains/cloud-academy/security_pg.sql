-- 領域乙（cloud-academy）：PostgreSQL 18 正式環境角色、最小權限、PII 隔離與多租戶 RLS 參考腳本
-- 用途：補足 SQLite 無法演示的資料庫角色隔離、逾時護欄與企業多租戶列級安全政策

REVOKE CREATE ON SCHEMA public FROM PUBLIC;

CREATE ROLE academy_migrator    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE academy_app         NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE academy_bi_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE academy_audit_ro    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

ALTER ROLE academy_app         SET statement_timeout = '3s';
ALTER ROLE academy_app         SET lock_timeout      = '1s';
ALTER ROLE academy_bi_readonly SET statement_timeout = '30s';

GRANT USAGE ON SCHEMA public TO academy_app, academy_bi_readonly, academy_audit_ro;

-- 應用角色具業務表讀寫權，但不可改動或刪除權限稽核表
GRANT SELECT, INSERT, UPDATE, DELETE ON
  users, user_pii, user_credentials, user_sessions,
  organizations, org_memberships, roles, user_roles,
  courses, course_contents, tags, course_tags,
  subscriptions, invoices, lesson_progress, certificates, webhook_events
TO academy_app;

REVOKE UPDATE, DELETE, TRUNCATE ON permission_audit_logs FROM academy_app;
GRANT SELECT, INSERT ON permission_audit_logs TO academy_app;
GRANT SELECT ON permission_audit_logs TO academy_audit_ro;

-- BI 角色完全禁止讀取 user_credentials、user_sessions、user_pii 與含 email 的 users 原表
REVOKE ALL ON users, user_pii, user_credentials, user_sessions FROM academy_bi_readonly;
GRANT SELECT ON v_learner_analytics, courses, tags, course_tags, subscriptions, invoices, lesson_progress, certificates
TO academy_bi_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE academy_migrator IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;

-- 企業租戶 RLS：org_memberships 與企業 subscriptions 強制受目前請求的 app.current_org_id 隔離
ALTER TABLE org_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_memberships FORCE ROW LEVEL SECURITY;

CREATE POLICY p_org_memberships_tenant ON org_memberships
  FOR ALL TO academy_app
  USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer)
  WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;

CREATE POLICY p_subscriptions_tenant_or_self ON subscriptions
  FOR SELECT TO academy_app
  USING (
    user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
    OR (
      org_id IS NOT NULL
      AND org_id = NULLIF(current_setting('app.current_org_id', true), '')::integer
    )
  );
