# 59 — Command resume batch dari dashboard (RESUME_BATCH)

**What to build:** Operator dapat melanjutkan batch yang terputus. Bridge
memahami command `RESUME_BATCH` yang mengembalikan batch `interrupted` ke
`active` (membersihkan `interrupted_at`, `started_at` tetap sehingga durasi
total jujur dari awal proses), lalu perangkat dinyalakan ulang. Sensor logs
yang masuk setelah resume tetap menumpuk ke batch yang sama — satu batch utuh
untuk satu proses distilasi.

**Blocked by:** 58 — Deteksi pemutusan di bridge: batch otomatis `interrupted`

**Status:** ready-for-agent

- [ ] Command `RESUME_BATCH` (dari dashboard) diterima bridge: batch
      `interrupted` → `active`, `interrupted_at` dibersihkan
- [ ] `RESUME_BATCH` hanya valid untuk batch `interrupted` pada device tersebut;
      selain itu ditolak (mis. `rejected`)
- [ ] Setelah resume, perintah pemanasan (`POWER_ON` / `mulai`) terkirim ke
      perangkat dan telemetry baru masuk ke batch yang sama
- [ ] Siklus command (pending → dispatched → succeeded/failed) berjalan seperti
      command lain; unit test bridge mencakup resume + penolakan kasus salah
