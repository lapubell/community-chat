<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const { wsStatus } = storeToRefs(auth);
</script>

<template>
  <nav class="navbar">
    <div class="brand">
      <span class="brand-icon">💬</span>
      <span class="brand-name">Community Chat</span>
    </div>
    <div class="status" :class="wsStatus">
      <span class="dot" :class="wsStatus === 'connected' ? 'dot-green' : 'dot-gray'" />
      {{ wsStatus }}
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.brand { display: flex; align-items: center; gap: 10px; font-weight: 600; }
.brand-icon { font-size: 20px; }
.status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
