<script setup>
import { useToasts } from "@/composables/useToasts";
const { items, dismiss } = useToasts();
</script>

<template>
  <div class="toast-container">
    <div
      v-for="t in items"
      :key="t.id"
      class="toast"
      :class="`toast-${t.type}`"
      role="status"
    >
      <span class="toast-msg">{{ t.message }}</span>
      <button class="toast-close" aria-label="Dismiss" @click="dismiss(t.id)">✕</button>
    </div>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1000;
  max-width: min(360px, calc(100vw - 40px));
}
.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow);
  font-size: 14px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  animation: toast-in 0.18s ease-out;
}
.toast-msg { flex: 1; }
.toast-success { border-color: var(--success, #2e7d32); }
.toast-error { border-color: var(--danger); }
.toast-close {
  flex-shrink: 0;
  font-size: 14px;
  line-height: 1;
  color: var(--text-muted);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}
.toast-close:hover { color: var(--text); background: var(--bg-hover); }

@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
