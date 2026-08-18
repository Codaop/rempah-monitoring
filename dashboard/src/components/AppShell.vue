<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { supabase } from "../lib/supabase";
import { offlineSince } from "../lib/format";

const router = useRouter();

const navGroups = [
  {
    label: "Utama",
    items: [
      { name: "dashboard", label: "Dasbor" },
      { name: "analytics", label: "Analitik & Log" },
    ],
  },
  {
    label: "Pengaturan",
    items: [{ name: "settings", label: "Pengaturan" }],
  },
];

// ── Status batch aktif + perangkat tersedia (untuk tombol sidebar) ─────────
const hasActiveBatch = ref(false);
const devices = ref([]);
const POLL_MS = 30000;
let timer = null;

const anyDeviceAvailable = computed(() =>
  devices.value.some((d) => {
    if (!d.mode || d.mode !== "IDLE") return false;
    const ms = offlineSince(d.last_seen_at);
    return ms >= 0 && ms < 60000; // konsisten OFFLINE_AFTER_S bridge
  })
);

async function refreshBatchStatus() {
  const [batchRes, devRes, stateRes] = await Promise.all([
    supabase.from("batches").select("id").eq("status", "active").limit(1),
    supabase.from("devices").select("id, name, last_seen_at"),
    supabase.from("device_state").select("device_id, mode"),
  ]);
  hasActiveBatch.value = Boolean(batchRes.data?.[0]);
  const states = stateRes.data || [];
  devices.value = (devRes.data || []).map((d) => ({
    ...d,
    mode: (states.find((s) => s.device_id === d.id) || {}).mode || "IDLE",
  }));
}

function startNewBatch() {
  router.push({ name: "dashboard", query: { start: Date.now() } });
}

onMounted(async () => {
  await refreshBatchStatus();
  timer = setInterval(refreshBatchStatus, POLL_MS);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="logo-box">
          <img src="/logo.svg" alt="REMPAH" class="logo-img" />
        </div>
        <div>
          <div class="brand-name">REMPAH</div>
          <div class="brand-sub">Kontrol Distilasi</div>
        </div>
      </div>

      <nav class="nav">
        <template v-for="group in navGroups" :key="group.label">
          <div class="nav-group-label">{{ group.label }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.name"
            :to="{ name: item.name }"
            class="nav-item"
            active-class="active"
          >
            <!-- Dashboard icon -->
            <svg
              v-if="item.name === 'dashboard'"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect width="7" height="7" x="3" y="3" rx="1" />
              <rect width="7" height="7" x="14" y="3" rx="1" />
              <rect width="7" height="7" x="3" y="14" rx="1" />
              <rect width="7" height="7" x="14" y="14" rx="1" />
            </svg>
            <!-- Analytics icon -->
            <svg
              v-if="item.name === 'analytics'"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <!-- Settings (gear) icon -->
            <svg
              v-if="item.name === 'settings'"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path
                d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
              />
            </svg>
            <span>{{ item.label }}</span>
          </router-link>
        </template>
      </nav>

      <div class="side-foot" v-if="hasActiveBatch">
        <button
          class="batch-btn"
          :disabled="!anyDeviceAvailable"
          @click="startNewBatch"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="16" />
            <line x1="8" y1="12" x2="16" y2="12" />
          </svg>
          Mulai Batch Baru
        </button>
      </div>
    </aside>

    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}

.side {
  width: 220px;
  flex: 0 0 220px;
  background: #ffffff;
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  padding: 20px 16px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 0 4px 24px;
}

.logo-box {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--navy);
  display: grid;
  place-items: center;
  flex: 0 0 40px;
  overflow: hidden;
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.brand-name {
  font-weight: 700;
  color: var(--navy);
  font-size: 15px;
  line-height: 1.2;
}

.brand-sub {
  font-size: 11px;
  color: var(--muted);
  margin-top: 1px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.nav-group-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--muted);
  text-transform: uppercase;
  padding: 14px 12px 4px;
}
.nav-group-label:first-child {
  padding-top: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--navy);
  font-weight: 500;
  font-size: 13.5px;
  transition:
    background 0.12s,
    color 0.12s;
  text-decoration: none;
}

.nav-item:hover {
  background: var(--teal-soft);
  color: var(--teal);
  text-decoration: none;
}

.nav-item.active {
  background: var(--teal-soft);
  color: var(--teal);
  font-weight: 600;
}

.side-foot {
  padding-top: 16px;
  border-top: 1px solid var(--line);
  margin-top: 8px;
}

.batch-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--navy);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s;
}
.batch-btn:hover {
  filter: brightness(1.15);
}
.batch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  filter: none;
}

.main {
  flex: 1;
  padding: 24px 28px;
  min-width: 0;
  max-width: 1200px;
}

@media (max-width: 760px) {
  .shell {
    flex-direction: column;
  }
  .side {
    width: 100%;
    flex: none;
    height: auto;
    position: static;
    padding: 10px 12px;
    flex-direction: row;
    align-items: center;
    border-right: none;
    border-bottom: 1px solid var(--line);
    gap: 8px;
  }
  .brand {
    padding: 0 8px 0 0;
    flex: 0 0 auto;
  }
  .brand-sub {
    display: none;
  }
  .brand-name {
    font-size: 14px;
  }
  .logo-box {
    width: 36px;
    height: 36px;
    flex-basis: 36px;
  }
  .nav {
    flex-direction: row;
    overflow-x: auto;
    flex: 1;
    justify-content: flex-end;
  }
  .nav-group-label {
    display: none;
  }
  .nav-item {
    padding: 10px;
    min-width: 44px;
    justify-content: center;
  }
  .nav-item span {
    display: none;
  }
  .side-foot {
    display: none;
  }
  .main {
    padding: 16px;
  }
}

@media (max-width: 360px) {
  .side {
    padding: 8px 10px;
    gap: 4px;
  }
  .brand {
    gap: 6px;
  }
  .logo-box {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
  }
  .main {
    padding: 12px;
  }
}
</style>
