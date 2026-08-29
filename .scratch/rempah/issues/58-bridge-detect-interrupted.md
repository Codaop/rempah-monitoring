# 58 — Deteksi pemutusan di bridge: batch otomatis `interrupted`

**What to build:** Ketika sebuah perangkat berhenti mengirim data (mati mendadak
/ disconnect) lebih dari ambang offline (60 detik, `OFFLINE_AFTER_S`) dan
perangkat itu sedang punya batch `active`, bridge otomatis menandai batch
tersebut `interrupted` + mencatat `interrupted_at` — tanpa campur tangan manual
operator. Pemutusan tercatat dengan jujur, bukan dibiarkan "nyangkut" sebagai
`active` selamanya.

**Blocked by:** 57 — Fondasi data: status `interrupted` + `interrupted_at`

**Status:** ready-for-agent

- [ ] Device diam > `OFFLINE_AFTER_S` dan punya batch `active` → batch di-set
      `interrupted` + `interrupted_at` tercatat (satu kali, tidak berulang)
- [ ] Device diam tapi TIDAK punya batch `active` → tidak ada yang berubah
- [ ] `close_active_batch` tidak menyentuh batch `interrupted` (hanya mencari
      `status = 'active'`) — transisi terminal nanti tidak menimpa status
- [ ] Unit test bridge mencakup: deteksi terputus, non-deteksi saat tidak ada
      batch aktif, dan idempotensi (tidak menandai ulang batch yang sudah
      `interrupted`)
