<script setup>
import { watch, onBeforeUnmount } from "vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: "" },
  maxWidth: { type: String, default: "440px" },
  closeOnOverlay: { type: Boolean, default: true },
});
const emit = defineEmits(["close"]);

function onKeydown(e) {
  if (e.key === "Escape" && props.open) emit("close");
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      document.addEventListener("keydown", onKeydown);
      document.body.style.overflow = "hidden";
    } else {
      document.removeEventListener("keydown", onKeydown);
      document.body.style.overflow = "";
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-overlay"
      :class="{ 'no-close': !closeOnOverlay }"
      @click.self="closeOnOverlay && emit('close')"
    >
      <div
        class="modal-panel"
        :style="{ maxWidth }"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
      >
        <div class="modal-head">
          <h2 class="modal-title">{{ title }}</h2>
          <button
            type="button"
            class="modal-x"
            aria-label="Tutup"
            @click="emit('close')"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
        <div v-if="$slots.actions" class="modal-actions">
          <slot name="actions" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(28, 43, 58, 0.45);
  display: grid;
  place-items: center;
  z-index: 1000;
  padding: 16px;
}

.modal-panel {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  width: 100%;
  max-height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px 0;
  gap: 12px;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--navy);
  margin: 0;
}

.modal-x {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: none;
  background: var(--teal-soft);
  color: var(--teal);
  display: grid;
  place-items: center;
  cursor: pointer;
  flex: 0 0 30px;
  transition: filter 0.15s;
}
.modal-x:hover {
  filter: brightness(0.95);
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  min-height: 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 20px 18px;
  flex-wrap: wrap;
}
</style>
