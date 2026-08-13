# 23 — Upload foto profil operator

**What to build:** Operator dapat mengganti foto profil dari halaman profil: tombol edit pada avatar membuka pemilih file gambar, file terunggah ke penyimpanan yang aman, dan avatar langsung menampilkan foto baru — dengan fallback ke avatar default bila belum ada foto atau gambar gagal dimuat.

**Blocked by:** None — can start immediately

**Status:** done

- [x] Tombol edit pada avatar membuka pemilih file gambar (jpg/png/webp) dengan batasan ukuran yang wajar
- [x] File terunggah ke bucket penyimpanan khusus avatar dengan nama unik per operator; policy keamanan hanya mengizinkan operator mengunggah/membaca avatarnya sendiri (migration/DDL jika diperlukan)
- [x] URL foto tersimpan di metadata profil operator dan avatar menampilkan foto tersebut saat halaman dimuat ulang
- [x] Jika belum ada foto atau gambar gagal dimuat, avatar default (SVG) tetap tampil
- [x] Ada umpan balik proses: indikator sedang mengunggah, dan pesan sukses/gagal yang jelas
- [x] Build dashboard lulus

## Comments

- 2026-08-13: Migration `avatars_storage_bucket` DI-APPLY ke Supabase (bucket privat `avatars`, batas 2 MB + whitelist mime, policy RLS owner-only select/insert/update/delete). Profile.vue: tombol edit membuka file input tersembunyi, upload ke `avatars/{userId}.{ext}` (upsert), simpan `avatar_path` di user metadata, tampilkan via signed URL 1 jam, fallback SVG + pesan sukses/gagal. Diverifikasi via `npm run build`.
