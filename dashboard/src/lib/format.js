export function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("id-ID", {
    maximumFractionDigits: digits,
    // Digit desimal selalu tampil (28,50 bukan 28,5) agar nilai live terlihat
    // bergerak tiap tick — operator yakin alat masih berjalan (ticket 45/46).
    minimumFractionDigits: digits,
  });
}

export function fmtTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.toLocaleDateString("id-ID", { day: "2-digit", month: "short" })} ${d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}`;
}

export function fmtDuration(ms) {
  if (!ms || ms < 0) return "—";
  const s = Math.round(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}j ${m}m`;
  return `${m}m ${s % 60}d`;
}

export function offlineSince(lastSeen) {
  if (!lastSeen) return -1;
  return Date.now() - new Date(lastSeen).getTime();
}
