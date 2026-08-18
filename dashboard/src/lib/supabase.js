import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  console.error(
    "[REMPAH] ⚠ Konfigurasi Supabase tidak ditemukan.\n" +
      "Buat file dashboard/.env dengan isi:\n" +
      "  VITE_SUPABASE_URL=https://<ref>.supabase.co\n" +
      "  VITE_SUPABASE_ANON_KEY=<anon-key>\n" +
      "Lihat docs/ops.md untuk panduan lengkap."
  );
}

export const supabase = createClient(
  url ?? "https://placeholder.supabase.co",
  anonKey ?? "placeholder-anon-key",
  { auth: { persistSession: true, autoRefreshToken: true } }
);
