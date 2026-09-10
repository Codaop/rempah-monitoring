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
// Umur telemetry SELALU dihitung dari jam nyata (Date.now()), bukan dari nilai
// yang disimpan di sebuah ref: ref seperti itu beku di antara pembaruan, dan
// setiap `telemetry_at` yang lebih baru akan menghasilkan umur negatif sehingga
// perangkat segar terbaca basi (card menampilkan 0 walau broker aktif).
//
// Yang tetap perlu reaktif hanyalah TRANSISI segar → basi. Itu ditangani satu
// `setTimeout` sekali jalan yang dijadwalkan tepat pada ambang kedaluwarsa
// terdekat, dan dijadwalkan ulang hanya ketika telemetry baru tiba. Saat
// menyala, `staleTick` dinaikkan sehingga setiap computed yang membaca
// kesegaran dihitung ulang. Tidak ada telemetry segar → tidak ada timer sama
// sekali, sehingga halaman tidak pernah ter-refresh berkala.
export const staleTick = ref(0);
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
      staleTick.value += 1;
      jadwalkanKedaluwarsa();
    },
    tercepat - now + 1000
  );
}

// Telemetry baru masuk → jadwalkan ulang ambang kedaluwarsanya.
watch(liveByDevice, jadwalkanKedaluwarsa, { deep: true });

// Umur (ms) telemetry live terakhir untuk sebuah device, atau -1 bila belum
// pernah menerima telemetry di sesi browser ini.
export function telemetryAge(deviceId, now = Date.now()) {
  const at = liveByDevice[deviceId]?.telemetry_at;
  if (!at) return -1;
  return now - at;
}

// Perangkat punya telemetry live yang masih segar dari broker MQTT.
export function telemetryFresh(deviceId, now = Date.now()) {
  // Baca staleTick agar computed yang memakai helper ini ikut dihitung ulang
  // tepat pada transisi segar → basi (satu-satunya pembaruan reaktif umur).
  void staleTick.value;
  if (!deviceId) return false;
  const age = telemetryAge(deviceId, now);
  return age >= 0 && age < OFFLINE_MS;
}

// Perangkat online = telemetry MQTT segar ATAU bridge menulis `last_seen_at`
// yang masih segar. Salah satu jalur saja sudah cukup. Keduanya memakai jam
// nyata dan bereaksi lewat pembaruan data, bukan lewat timer berkala.
export function deviceOnline(device) {
  if (!device) return false;
  if (telemetryFresh(device.id)) return true;
  const ms = offlineSince(device.last_seen_at);
  return ms >= 0 && ms < OFFLINE_MS;
}
