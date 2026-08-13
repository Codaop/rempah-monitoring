-- Migration 04: bucket storage `avatars` untuk foto profil operator
-- Prepared 2026-08-13 as part of UI revision (ticket 23).
--
-- Why this shape:
-- - Bucket privat (public = false): avatar hanya boleh diakses pemiliknya via
--   RLS, bukan publik. Dashboard mengambilnya dengan signed URL (createSignedUrl)
--   lewat client terautentikasi.
-- - Policy berbasis `owner = auth.uid()`: Supabase storage mengisi kolom owner
--   dengan uid pengguna yang mengunggah (client authenticated), jadi operator
--   hanya bisa membaca/menimpa foto profil miliknya sendiri.
-- - Batas ukuran 2 MB + whitelist mime image/* diterapkan di level bucket agar
--   upload tidak bisa menyalahgunakan penyimpanan.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('avatars', 'avatars', false, 2097152, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;

-- Operator hanya bisa membaca objek avatarnya sendiri.
create policy "avatars_select_own"
  on storage.objects for select
  using (bucket_id = 'avatars' and owner = auth.uid());

-- Operator hanya bisa mengunggah ke folder avatarnya sendiri.
create policy "avatars_insert_own"
  on storage.objects for insert
  with check (bucket_id = 'avatars' and owner = auth.uid());

-- Operator bisa menimpa avatar lama miliknya (upsert path yang sama).
create policy "avatars_update_own"
  on storage.objects for update
  using (bucket_id = 'avatars' and owner = auth.uid());

-- Operator bisa menghapus avatar miliknya.
create policy "avatars_delete_own"
  on storage.objects for delete
  using (bucket_id = 'avatars' and owner = auth.uid());
