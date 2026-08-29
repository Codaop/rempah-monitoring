-- Migration 13: fungsi RPC `delete_device` (tiket 62)
-- Menghapus device beserta seluruh data turunannya secara transaksional.
-- Dikeluarkan sebagai SECURITY DEFINER supaya operator cukup memanggil
-- satu RPC dari dashboard — tanpa perlu tahu urutan DELETE anak-anak
-- tabel yang bergantung pada FK dan risiko partial-delete.
--
-- Urutan penghapusan mengikuti dependensi FK agar tidak melanggar
-- constraint RESTRICT:
--   1. device_state      (PK = device_id)
--   2. session_devices   (junction table, FK → devices)
--   3. commands          (FK → devices)
--   4. alerts            (FK → devices)
--   5. sensor_logs       (FK → devices + batches, device_id column)
--   6. batch_logs        (via batches.device_id, JOIN DELETE)
--   7. batches           (FK → devices)
--   ---
--   Terakhir: baris devices sendiri dihapus di sini.
--
-- Pengaman (bagian 1): verifikasi kepemilikan + blokir jika ada batch
-- aktif. Jika salah satu gagal, fungsi mengembalikan JSON error tanpa
-- mengubah database sama sekali.

DROP FUNCTION IF EXISTS public.delete_device(uuid);

CREATE OR REPLACE FUNCTION public.delete_device(p_device_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_owner_match boolean;
  v_active_count integer := 0;
  -- Counter setiap tahap (diisi GET DIAGNOSTICS ROW_COUNT)
  v_ds int;
  v_sd int;
  v_cmd int;
  v_alr int;
  v_sl int;
  v_bl int;
  v_bat int;
BEGIN
  -- ============================================================
  -- BAGIAN 1 — Verifikasi keamanan (READ ONLY)
  -- Tidak ada perubahan DB sampai bagian 2.
  -- ============================================================

  -- Pastikan device ada dan dipanggil oleh operator yang memilikinya.
  -- Pengecekan producer_id eksplisit menjaga akses dari pihak lain
  -- tetap ditolak meskipun fungsi berjalan sebagai SECURITY DEFINER.
  SELECT TRUE INTO v_owner_match
  FROM public.devices
  WHERE id = p_device_id AND producer_id = operator_producer_id();

  IF NOT v_owner_match THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', 'Perangkat tidak ditemukan atau Anda bukan pemilik perangkat.',
      'counts', '{}'::jsonb
    );
  END IF;

  -- Blokir penghapusan saat masih ada batch aktif (keselamatan).
  SELECT count(*) INTO v_active_count
  FROM public.batches
  WHERE device_id = p_device_id AND status = 'active';

  IF v_active_count > 0 THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', 'Device masih memiliki ' || v_active_count || ' batch aktif — harus diselesaikan atau dihentikan terlebih dahulu.',
      'active_batches', v_active_count,
      'counts', '{}'::jsonb
    );
  END IF;

  -- ============================================================
  -- BAGIAN 2 — Penghapusan anak (urut sesuai dependensi FK)
  -- Semua berjalan dalam satu transaksi karena ini body fungsi.
  -- Baris devices itu sendiri dihapus DI AKHIR (setelah semua anak
  -- bersih), agar FK constraint tidak menghalangi proses.
  -- ============================================================

  -- 1. device_state (baris unik per device, PK = device_id)
  DELETE FROM public.device_state WHERE device_id = p_device_id;
  GET DIAGNOSTICS v_ds = ROW_COUNT;

  -- 2. session_devices (tabel junction, FK → devices)
  DELETE FROM public.session_devices WHERE device_id = p_device_id;
  GET DIAGNOSTICS v_sd = ROW_COUNT;

  -- 3. commands (instruksi dashboard untuk perangkat)
  DELETE FROM public.commands WHERE device_id = p_device_id;
  GET DIAGNOSTICS v_cmd = ROW_COUNT;

  -- 4. alerts (catatan peringatan / alarm dari perangkat)
  DELETE FROM public.alerts WHERE device_id = p_device_id;
  GET DIAGNOSTICS v_alr = ROW_COUNT;

  -- 5. sensor_logs (telemetry mentah per batch dan idle, FK → devices)
  DELETE FROM public.sensor_logs WHERE device_id = p_device_id;
  GET DIAGNOSTICS v_sl = ROW_COUNT;

  -- 6. batch_logs (hanya log batch yang berasal dari device ini)
  DELETE FROM public.batch_logs bl
  USING public.batches b
  WHERE bl.batch_id = b.id AND b.device_id = p_device_id;
  GET DIAGNOSTICS v_bl = ROW_COUNT;

  -- 7. batches (record batch — dilakukan setelah batch_logs aman)
  DELETE FROM public.batches WHERE device_id = p_device_id;
  GET DIAGNOSTICS v_bat = ROW_COUNT;

  -- --- Sekarang semua anak bersih. Hapus baris devices sendiri. ---
  DELETE FROM public.devices WHERE id = p_device_id;

  -- ============================================================
  -- BAGIAN 3 — Ringkasan jumlah baris terhapus
  -- ============================================================
  RETURN jsonb_build_object(
    'success', true,
    'deleted_device_id', p_device_id,
    'counts', jsonb_build_object(
      'device_state', coalesce(v_ds, 0),
      'session_devices', coalesce(v_sd, 0),
      'commands', coalesce(v_cmd, 0),
      'alerts', coalesce(v_alr, 0),
      'sensor_logs', coalesce(v_sl, 0),
      'batch_logs', coalesce(v_bl, 0),
      'batches', coalesce(v_bat, 0),
      'total_rows', coalesce(v_ds, 0) + coalesce(v_sd, 0) +
                     coalesce(v_cmd, 0) + coalesce(v_alr, 0) +
                     coalesce(v_sl, 0) + coalesce(v_bl, 0) +
                     coalesce(v_bat, 0)
    )
  );
END;
$$;

-- ==========================================
-- Test manual (jalankan di Supabase SQL editor)
-- ==========================================

-- -- Uji sukses (device tanpa data turunan):
-- SELECT * FROM public.delete_device('test-device-uuid-here');
--
-- -- Uji tolak — batch aktif:
-- SELECT * FROM public.delete_device('device-with-active-batch-uuid');
--
-- -- Uji tolak — bukan pemilik:
-- SELECT * FROM public.delete_device('other-producer-device-uuid');
