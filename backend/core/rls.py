"""Migration helper that puts a tenant table under PostgreSQL Row-Level Security."""

from django.db import migrations

POLICY = """
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON {table}
  USING (
    organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid
    OR current_setting('app.bypass_rls', true) = 'on'
  )
  WITH CHECK (
    organization_id = NULLIF(current_setting('app.current_org', true), '')::uuid
    OR current_setting('app.bypass_rls', true) = 'on'
  );
"""

REVERSE = """
DROP POLICY IF EXISTS tenant_isolation ON {table};
ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
"""


def enable_rls(table: str) -> migrations.RunSQL:
    """Append to the operations of the migration that creates a TenantModel table."""
    return migrations.RunSQL(POLICY.format(table=table), REVERSE.format(table=table))
