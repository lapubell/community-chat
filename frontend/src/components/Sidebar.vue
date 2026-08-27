<script setup>
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import Avatar from "./Avatar.vue";

defineProps({
  mobileOpen: { type: Boolean, default: false },
});
const emit = defineEmits(["close"]);

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const chat = useChatStore();
const { dmConversations } = storeToRefs(chat);
const { me } = storeToRefs(auth);

function isNavActive(name) {
  return route.name === name;
}

function go(name, userId) {
  emit("close");
  if (name === "dm" && userId) router.push({ name: "dm", params: { userId } });
  else router.push({ name });
}

watch(
  () => route.name,
  () => emit("close")
);
</script>

<template>
  <aside class="sidebar" :class="{ open: mobileOpen }">
    <button class="mobile-close" @click="emit('close')">✕</button>
    <div class="me-card">
      <Avatar :user="me" size="lg" />
      <div class="me-info">
        <div class="me-name">{{ me?.display_name }}</div>
        <div class="me-handle">@{{ me?.handle }}</div>
      </div>
    </div>

    <nav class="nav">
      <button class="nav-item" :class="{ active: isNavActive('chat') }" @click="go('chat')">
        <span class="nav-icon">🌐</span> Group Chat
      </button>
      <button class="nav-item" :class="{ active: isNavActive('members') }" @click="go('members')">
        <span class="nav-icon">👥</span> Members
      </button>
      <button class="nav-item" :class="{ active: isNavActive('families') }" @click="go('families')">
        <span class="nav-icon">🏠</span> Families
      </button>
      <button class="nav-item" :class="{ active: isNavActive('gallery') }" @click="go('gallery')">
        <span class="nav-icon">🖼️</span> Gallery
      </button>
      <button class="nav-item" :class="{ active: isNavActive('settings') }" @click="go('settings')">
        <span class="nav-icon">⚙️</span> Settings
      </button>
    </nav>

    <div class="dms-section">
      <div class="dms-header">Direct Messages</div>
      <button
        v-for="c in dmConversations"
        :key="c.peer.id"
        class="dm-item"
        :class="{ active: isNavActive('dm') && Number(route.params.userId) === c.peer.id }"
        @click="go('dm', c.peer.id)"
      >
        <Avatar :user="c.peer" />
        <div class="dm-info">
          <div class="dm-name">{{ c.peer.display_name }}</div>
          <div class="dm-preview">{{ c.last_message?.text || "No messages yet" }}</div>
        </div>
        <span v-if="c.unread_count > 0" class="badge">{{ c.unread_count }}</span>
      </button>
      <div v-if="dmConversations.length === 0" class="dms-empty">
        No conversations yet.
        <router-link to="/members">Message someone →</router-link>
      </div>
    </div>
  </aside>
  <button v-if="mobileOpen" class="mobile-overlay" @click="emit('close')"></button>
</template>

<style scoped>
.sidebar {
  width: 280px;
  background: var(--bg-elevated);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
}
.me-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border);
  align-items: center;
}
.me-info { min-width: 0; }
.me-name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.me-handle { font-size: 12px; color: var(--text-muted); }
.nav { padding: 12px 8px; border-bottom: 1px solid var(--border); }
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 14px;
  transition: background 0.15s;
  text-align: left;
}
.nav-item:hover { background: var(--bg-hover); }
.nav-item.active { background: var(--accent-soft); color: var(--accent-hover); }
.nav-icon { font-size: 16px; width: 20px; text-align: center; }
.dms-section { flex: 1; padding: 12px 8px; overflow-y: auto; }
.dms-header {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  padding: 4px 12px 8px;
}
.dm-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
  text-align: left;
}
.dm-item:hover { background: var(--bg-hover); }
.dm-item.active { background: var(--accent-soft); }
.dm-info { flex: 1; min-width: 0; }
.dm-name { font-weight: 500; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dm-preview {
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dms-empty {
  padding: 16px 12px;
  font-size: 13px;
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    inset: 0;
    z-index: 40;
    transform: translateX(-100%);
    transition: transform 0.2s;
    width: 280px;
  }
  .sidebar.open { transform: translateX(0); }
  .mobile-close {
    position: absolute;
    top: 12px;
    right: 12px;
    font-size: 16px;
    color: var(--text-muted);
    z-index: 2;
  }
  .mobile-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 39;
    border: none;
  }
}
</style>
