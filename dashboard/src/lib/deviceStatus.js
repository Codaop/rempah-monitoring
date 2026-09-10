// Definisi tunggal "perangkat online" untuk seluruh dashboard.
//
// Dua jalur data hidup berdampingan dan masing-masing bisa jadi satu-satunya
// bukti bahwa perangkat masih hidup:
//   - MQTT langsung (browser → HiveMQ): dibuktikan oleh `telemetry_at`, yaitu
//     stempel waktu pesan *telemetry*. Pesan `state` sengaja TIDAK dihitung
//     karena dikirim retained (broker mengirim ulang state lama ke setiap
//     browser yang baru subscribe) sehingga akan menandai perangkat mati
//     sebagai online.
//   - Bridge → Supabase: dibuktikan oleh `devices.last_seen_at`, yang ditulis
//     bridge setiap telemetry masuk.
//
// Sebelumnya tiap komponen punya definisi sendiri (beberapa memakai
// `received_at` yang terpolusi retained `state`, satu memakai `lastMessageAt`
// yang di-set auto-refresh tiap 10 detik) sehingga badge status bertentangan
// dengan metric card. Helper ini menjadi satu-satunya sumber kebenaran.
import { ref } from "vue";
import { liveByDevice } from "./mqtt";

// Konsisten dengan OFFLINE_AFTER_S di bridge (ticket 31).
export const OFFLINE_MS = 60000;

// ── Jam reaktif ─────────────────────────────────────────────────────────────
// Kesegaran adalah fungsi waktu, jadi computed yang bergantung padanya (mis.
// badge online) harus re-evaluasi saat waktu berjalan walau tak ada pesan baru
// — kalau tidak, badge "Online" akan tersangkut setelah telemetry berhenti.
// Detak berjalan selama modul hidup (aplikasi ini SPA) sehingga semua halaman
// membaca "sekarang" yang sama dan selalu segar.
export const statusNow = ref(Date.now());

setInterval(() => {
  statusNow.value = Date.now();
}, 5000);

// Umur (ms) telemetry live terakhir untuk sebuah device, atau -1 bila belum
// pernah menerima telemetry di sesi browser ini.
export function telemetryAge(deviceId, now = statusNow.value) {
  const at = liveByDevice[deviceId]?.telemetry_at;
  if (!at) return -1;
  return now - at;
}

// Perangkat punya telemetry live yang masih segar dari broker MQTT.
export function telemetryFresh(deviceId, now = statusNow.value) {
  if (!deviceId) return false;
  const age = telemetryAge(deviceId, now);
  return age >= 0 && age < OFFLINE_MS;
}

// Perangkat online = telemetry MQTT segar ATAU bridge menulis `last_seen_at`
// yang masih segar. Salah satu jalur saja sudah cukup.
export function deviceOnline(device, now = statusNow.value) {
  if (!device) return false;
  if (telemetryFresh(device.id, now)) return true;
  if (!device.last_seen_at) return false;
  const ms = now - new Date(device.last_seen_at).getTime();
  return ms >= 0 && ms < OFFLINE_MS;
}
