<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import AppShell from "../components/AppShell.vue";
import { supabase } from "../lib/supabase";

const router = useRouter();
const profile = ref(null);
const displayName = ref("");
const emailVal = ref("");
const phone = ref("");
const saving = ref(false);
const saved = ref("");
const error = ref("");
const operatorId = ref("—");

onMounted(async () => {
  const { data: user } = await supabase.auth.getUser();
  profile.value = user.user || null;

  if (profile.value) {
    emailVal.value = profile.value.email || "";
    displayName.value =
      profile.value.user_metadata?.display_name ||
      profile.value.email?.split("@")[0] ||
      "";
    phone.value = profile.value.user_metadata?.phone || "";

    const { data: op } = await supabase
      .from("operators")
      .select("id, producer_id")
      .eq("id", profile.value.id)
      .maybeSingle();
    if (op) {
      operatorId.value = "KPLG-" + op.id.slice(0, 5).toUpperCase();
    }
  }
});

async function save() {
  saving.value = true;
  saved.value = "";
  error.value = "";
  const { error: err } = await supabase.auth.updateUser({
    data: { display_name: displayName.value, phone: phone.value },
  });
  saving.value = false;
  if (err) error.value = err.message;
  else saved.value = "Profil diperbarui.";
}

async function signOut() {
  await supabase.auth.signOut();
  router.push({ name: "login" });
}
</script>

<template>
  <AppShell>
    <div class="page-head">
      <h1 class="page-title">Pengaturan Profil</h1>
      <p class="page-sub">Kelola detail akun dan akses operasional.</p>
    </div>

    <!-- Profile card -->
    <div class="card profile-card">
      <div class="avatar-col">
        <div class="avatar-circle">
          <svg
            viewBox="0 0 100 100"
            xmlns="http://www.w3.org/2000/svg"
            width="80"
            height="80"
          >
            <circle cx="50" cy="35" r="22" fill="#94a3b8" />
            <ellipse cx="50" cy="85" rx="32" ry="22" fill="#94a3b8" />
          </svg>
          <div class="avatar-edit">
            <svg
              width="11"
              height="11"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              stroke-width="2.5"
              stroke-linecap="round"
            >
              <path
                d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
              />
              <path
                d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
              />
            </svg>
          </div>
        </div>
        <span class="role-badge">OPERATOR</span>
        <span class="op-id">ID: {{ operatorId }}</span>
      </div>

      <form class="form-col" @submit.prevent="save">
        <div class="field">
          <label class="field-label">Nama Tampilan</label>
          <input
            v-model="displayName"
            class="input"
            type="text"
            placeholder="Nama Anda"
          />
        </div>
        <div class="field">
          <label class="field-label">Alamat Email</label>
          <input class="input" :value="emailVal" disabled />
        </div>
        <div class="field">
          <label class="field-label"
            >Telepon Kontak Darurat (Teknisi Ahli)</label
          >
          <input
            v-model="phone"
            class="input"
            type="tel"
            placeholder="+62 812 3456 7890"
          />
        </div>

        <p v-if="saved" class="ok-msg">{{ saved }}</p>
        <p v-if="error" class="err-msg">{{ error }}</p>

        <div class="form-actions">
          <button class="btn-save" type="submit" :disabled="saving">
            {{ saving ? "Menyimpan…" : "Simpan Profil" }}
          </button>
        </div>
      </form>
    </div>

    <!-- Session card -->
    <div class="card session-card">
      <div class="session-body">
        <div>
          <h2 class="session-title">Manajemen Sesi</h2>
          <p class="session-sub">
            Akhiri sesi Anda dengan aman di semua terminal.
          </p>
        </div>
        <button class="btn-logout" @click="signOut">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Keluar
        </button>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.page-head {
  margin-bottom: 20px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--navy);
}
.page-sub {
  font-size: 13px;
  color: var(--muted);
  margin: 4px 0 0;
}

.profile-card {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  margin-bottom: 20px;
}

@media (max-width: 700px) {
  .profile-card {
    flex-direction: column;
    align-items: center;
  }
}

.avatar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  min-width: 140px;
}

.avatar-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: #e2e8f0;
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-edit {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--teal);
  display: grid;
  place-items: center;
}

.role-badge {
  display: inline-block;
  padding: 3px 14px;
  border-radius: 999px;
  background: var(--teal-soft);
  color: var(--teal);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.op-id {
  font-size: 12px;
  color: var(--muted);
}

.form-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text);
}

.ok-msg {
  color: var(--ok);
  font-size: 13px;
  margin: 0;
}
.err-msg {
  color: var(--danger);
  font-size: 13px;
  margin: 0;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.btn-save {
  padding: 11px 22px;
  background: var(--navy);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s;
}
.btn-save:hover:not(:disabled) {
  filter: brightness(1.15);
}
.btn-save:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.session-card {
  border: 1px solid var(--danger);
  background: #fff8f8;
}

.session-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.session-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--navy);
  margin-bottom: 4px;
}

.session-sub {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--danger);
  color: #fff;
  border: none;
  border-radius: 999px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: filter 0.15s;
}
.btn-logout:hover {
  filter: brightness(1.08);
}
</style>
