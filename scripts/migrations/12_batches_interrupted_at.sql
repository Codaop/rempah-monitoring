-- Migration 12: status batch interrupted & interrupted_at (ticket 57)
--
-- Saat mesin mati mendadak / disconnect, batch tidak boleh "nyangkut" sebagai
-- active selamanya. Bridge menandai batch active yang perangkatnya diam >
-- OFFLINE_AFTER_S menjadi status 'interrupted' + mencatat kapan pemutusan
-- terjadi. Status 'interrupted' hanyalah nilai teks baru pada kolom status
-- (text bebas, tanpa check constraint), sehingga tidak butuh alter tipe.
--
--   interrupted_at timestamptz — waktu pemutusan terdeteksi (untuk durasi
--                                jujur di laporan: started_at → interrupted_at)

alter table public.batches
  add column if not exists interrupted_at timestamptz;
