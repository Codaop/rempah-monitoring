<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'

const router = useRouter()
const user = ref(null)
const nav = [
  { name: 'dashboard', label: 'Dashboard', icon: '◈' },
  { name: 'analytics', label: 'Analitik & Log', icon: '▤' },
  { name: 'profile', label: 'Profil', icon: '●' },
]

onMounted(async () => {
  const { data } = await supabase.auth.getUser()
  user.value = data.user
})

async function logout() {
  await supabase.auth.signOut()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="shell">
    <aside class="side">
      <div class="brand">
        <div class="logo">R</div>
        <div>
          <div class="brand-name">REM-PAH</div>
          <div class="brand-sub">Monitoring Kapulaga</div>
        </div>
      </div>
      <nav class="nav">
        <router-link
          v-for="item in nav"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-item"
          active-class="active"
        >
          <span class="nav-icon">{{ item.icon }}</span>{{ item.label }}
        </router-link>
      </nav>
      <div class="side-foot">
        <div class="user-chip">
          <div class="avatar">{{ (user?.email || '?')[0].toUpperCase() }}</div>
          <div class="user-meta">
            <div class="user-mail">{{ user?.email }}</div>
            <div class="muted">Operator</div>
          </div>
        </div>
        <button class="btn btn-ghost btn-sm full" @click="logout">Keluar</button>
      </div>
    </aside>

    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100vh; }

.side {
  width: 240px;
  flex: 0 0 240px;
  background: var(--navy);
  color: #cbd5e1;
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
  position: sticky;
  top: 0;
  height: 100vh;
}

.brand { display: flex; gap: 10px; align-items: center; padding: 4px 6px 18px; }
.logo {
  width: 38px; height: 38px; border-radius: 10px;
  background: var(--teal); color: #fff;
  display: grid; place-items: center;
  font-weight: 800; font-size: 19px;
}
.brand-name { font-weight: 700; color: #fff; font-size: 16px; }
.brand-sub { font-size: 11.5px; color: #94a3b8; }

.nav { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 9px;
  color: #cbd5e1; font-weight: 500; font-size: 14px;
  transition: background 0.15s;
}
.nav-item:hover { background: rgba(255, 255, 255, 0.06); text-decoration: none; color: #fff; }
.nav-item.active { background: var(--teal); color: #fff; }
.nav-icon { width: 18px; text-align: center; opacity: 0.9; }

.side-foot { display: flex; flex-direction: column; gap: 10px; padding-top: 14px; border-top: 1px solid rgba(255, 255, 255, 0.1); }
.user-chip { display: flex; gap: 10px; align-items: center; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--teal); color: #fff;
  display: grid; place-items: center; font-weight: 700;
}
.user-mail { font-size: 13px; color: #fff; max-width: 150px; overflow: hidden; text-overflow: ellipsis; }
.full { width: 100%; }

.main { flex: 1; padding: 24px; max-width: 1180px; min-width: 0; }

@media (max-width: 760px) {
  .shell { flex-direction: column; }
  .side {
    width: 100%; flex: none; height: auto; position: static;
    flex-direction: row; align-items: center; padding: 10px 14px;
  }
  .brand { padding: 0 12px 0 0; }
  .brand-sub, .side-foot { display: none; }
  .nav { flex-direction: row; overflow-x: auto; }
  .nav-item { white-space: nowrap; padding: 8px 10px; }
  .main { padding: 14px; }
}
</style>
