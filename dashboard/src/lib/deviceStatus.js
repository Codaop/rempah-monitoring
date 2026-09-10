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
import { ref, watch } from "vue";
import { liveByDevice } from "./mqtt";
import { offlineSince } from "./format";

// Konsisten dengan OFFLINE_AFTER_S di bridge (ticket 31).
export const OFFLINE_MS = 60000;

// ── Kesegaran tanpa auto-refresh ────────────────────────────────────────────
// Kesegaran adalah fungsi waktu, tapi kita TIDAK memakai timer periodik (jam
// yang tick tiap beberapa detik akan membuat halaman terus re-render dan
// terlihat seperti auto-refresh). Sebagai gantinya, satu `setTimeout` sekali
// dijadwalkan tepat saat telemetry segar berikutnya kedaluwarsa, dan
// dijadwalkan ulang hanya ketika telemetry baru tiba (event-driven).
// Tidak ada telemetry segar → tidak ada timer sama sekali.
export const statusNow = ref(Date.now());
let expiryTimer = null;

function jadwalkanKedaluwarsa() {
  if (expiryTimer) {
    clearTimeout(expiryTimer);
    expiryTimer = null;
  }

  const now = Date.now();
  let tercepat = Infinity;
  for (const id in liveByDevice) {
    const at = liveByDevice[id]?.telemetry_at;
    if (!at) continue;
    const deadline = at + OFFLINE_MS;
    if (deadline > now && deadline < tercepat) tercepat = deadline;
  }

  if (!Number.isFinite(tercepat)) return;

  expiryTimer = setTimeout(
    () => {
      expiryTimer = null;
      statusNow.value = Date.now();
      jadwalkanKedaluwarsa();
    },
    tercepat - now + 1000
  );
}

// Telemetry baru masuk → jadwalkan ulang ambang kedaluwarsanya.
watch(liveByDevice, jadwalkanKedaluwarsa, { deep: true });

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
// yang masih segar. Salah satu jalur saja sudah cukup. Jalur `last_seen_at`
// memakai jam nyata (bukan statusNow) dan bereaksi lewat pembaruan data,
// bukan lewat timer.
export function deviceOnline(device) {
  if (!device) return false;
  if (telemetryFresh(device.id)) return true;
  const ms = offlineSince(device.last_seen_at);
  return ms >= 0 && ms < OFFLINE_MS;
}
