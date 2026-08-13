# 16 — MCP Supabase: isi token asli & verifikasi koneksi

**What to build:** Konfigurasi MCP Supabase di `%APPDATA%\Roaming\Zed\settings.json` sudah diperbaiki (kunci `context_servers` yang benar + nama paket resmi `@supabase/mcp-server-supabase`, v0.10.0 — server terverifikasi merespons handshake MCP). Tugas Anda: mengganti placeholder token dan memastikan koneksi aktif di Zed.

**Blocked by:** None — can start immediately

**Status:** ready-for-human

- [x] Generate personal access token (`sbp_...`) di https://supabase.com/dashboard/account/tokens
- [x] Ganti `sbp_xxxxxxxxxxxxxx` di `"SUPABASE_ACCESS_TOKEN"` dalam `context_servers.supabase.env` di settings.json
- [ ] Restart Zed (context server dimuat saat start)
- [ ] Cek Settings → AI → MCP Servers → indikator hijau "Server is active"
- [ ] (Opsional) Konfirmasi via UI: Settings → AI → MCP Servers → Add Server → Add Local Server

## Comments

- 2026-08-12: Fix diterapkan oleh agent: `experimental.mcp_servers` (kunci yang diabaikan Zed) dipindah ke `context_servers`; nama paket dikoreksi dari `@supabase/mcp-server` (404 di npm) ke `@supabase/mcp-server-supabase`.
- 2026-08-12: Test koneksi nyata dengan token asli LULUS: initialize OK (server supabase v0.10.0), 29 tools tersedia, `list_projects` mengembalikan 2 project (ParuKuat App + REMPAH qjroojbtquvrdgawxcrw). Tinggal restart Zed + cek indikator hijau di Settings → AI → MCP Servers.
- 2026-08-12: ⚠️ Keamanan: paket `mcp-server-supabase` (tanpa scope `@supabase/`) di npm adalah "security research canary" typo-squat — jangan pernah menjalankan `npx mcp-server-supabase` tanpa scope. Selalu gunakan `@supabase/mcp-server-supabase`.
