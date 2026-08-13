-- Migration 03: revoke EXECUTE on SECURITY DEFINER helpers not needed by RLS
-- Prepared 2026-08-12 in response to Security Advisor lints
--   0028_anon_security_definer_function_executable
--   0029_authenticated_security_definer_function_executable
--
-- Why this shape:
-- - rls_auto_enable() is an EVENT TRIGGER helper (auto-enables RLS on new tables).
--   Event triggers fire server-side and never need a client EXECUTE grant, and no
--   client code calls it. Revoking from every client role removes it from the
--   /rest/v1/rpc surface entirely.
-- - operator_producer_id() is referenced by ~35 RLS policies across all tables,
--   and those policies apply to the `public` role set (anon + authenticated).
--   Policy evaluation calls the function AS THE QUERYING ROLE, so anon and
--   authenticated MUST keep EXECUTE or every PostgREST query fails with
--   "permission denied for function". It is intentionally kept exposed; the
--   call is harmless (anon gets NULL, authenticated only its own producer_id).
--   Only the blanket PUBLIC default grant is removed.

-- Tutup exposure rls_auto_enable() dari semua role client (tidak dipakai policy).
revoke execute on function public.rls_auto_enable() from public, anon, authenticated, service_role;

-- operator_producer_id(): pertahankan EXECUTE untuk anon/authenticated (dipakai
-- policy RLS), cabut hanya grant default PUBLIC yang berlebihan.
revoke execute on function public.operator_producer_id() from public;

-- Cegah kambuh: fungsi baru di schema public tidak lagi otomatis dapat EXECUTE
-- dari anon/authenticated/PUBLIC. Jika helper RLS masa depan butuh dipanggil
-- policy, grant harus eksplisit.
alter default privileges for role postgres in schema public
  revoke execute on functions from anon, authenticated, service_role, public;
