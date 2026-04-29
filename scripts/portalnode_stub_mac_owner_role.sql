-- One-time per Postgres cluster (roles are cluster-global).
-- Mac-origin pg_dump files often contain AUTHORIZATION "2ndopinionmd" / OWNER TO "2ndopinionmd".
-- Run before portalnode4090_restore_mkg.sh when using dumps created *without* --no-owner:
--
--   sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -f scripts/portalnode_stub_mac_owner_role.sql
--
-- New dumps from mkg_dump_for_4090.sh use --no-owner --no-acl and do not need this stub.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '2ndopinionmd') THEN
    EXECUTE 'CREATE ROLE "2ndopinionmd" NOLOGIN';
  END IF;
END$$;

-- portalnode must be a member of "2ndopinionmd" to run CREATE SCHEMA … AUTHORIZATION "2ndopinionmd" without superuser.
GRANT "2ndopinionmd" TO portalnode;
