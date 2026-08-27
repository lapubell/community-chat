<script setup>
import { onMounted, onUnmounted, ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import { onWsEvent } from "@/stores/auth";
import Sidebar from "@/components/Sidebar.vue";
import MessageBubble from "@/components/MessageBubble.vue";
import ComposeBox from "@/components/ComposeBox.vue";
import Avatar from "@/components/Avatar.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const chat = useChatStore();
const { me } = storeToRefs(auth);
const { dmMessages, typingPeer } = storeToRefs(chat);

const scrollRef = ref(null);
const mobileSidebar = ref(false);

const peerId = computed(() => Number(route.params.userId));
const peer = computed(() => auth.users.find((u) => u.id === peerId.value));
const messages = computed(() => dmMessages.value[peerId.value] || []);

function scrollToEnd(smooth = true) {
  requestAnimationFrame(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTo({ top: scrollRef.value.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    }
  });
}

async function markRead() {
  const msgs = messages.value.filter((m) => m.sender.id === peerId.value && !m.read_at);
  if (msgs.length) {
    const last = msgs[msgs.length - 1];
    await chat.markDmRead(peerId.value, last.id);
    for (const m of msgs) m.read_at = new Date().toISOString();
  }
}

function handleWs(msg) {
  if (msg.type === "dm.new" && Number(route.params.userId) === msg.message.sender.id) {
    scrollToEnd();
    markRead();
  }
  if (msg.type === "dm.read" && msg.peer_id === peerId.value) {
    const msgs = messages.value.filter((m) => m.sender.id === me.value?.id);
    for (const m of msgs) if (m.id <= msg.up_to_id) m.read_at = m.read_at || new Date().toISOString();
  }
}

watch(
  () => route.params.userId,
  async (id) => {
    if (id) {
      await chat.loadDmHistory(Number(id));
      scrollToEnd(false);
      markRead();
    }
  },
  { immediate: true }
);

let wsUnsub = null;
onMounted(() => {
  wsUnsub = onWsEvent(handleWs);
});
onUnmounted(() => {
  if (wsUnsub) wsUnsub();
});
</script>

<template>
  <div class="dm-layout">
    <Sidebar :mobile-open="mobileSidebar" @close="mobileSidebar = false" />

    <section class="dm-main">
      <header class="dm-header">
        <button class="mobile-toggle" @click="mobileSidebar = true">☰</button>
        <button class="back-btn" @click="router.push('/')">←</button>
        <Avatar :user="peer" />
        <div class="dm-header-info">
          <div class="dm-name">{{ peer?.display_name || "Direct message" }}</div>
          <div class="dm-handle">@{{ peer?.handle }}</div>
        </div>
        <span v-if="typingPeer === peerId" class="typing-indicator">typing…</span>
      </header>

      <div ref="scrollRef" class="dm-messages">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">✉️</div>
          <h2>No messages yet</h2>
          <p>Start the conversation with {{ peer?.display_name }}!</p>
        </div>
        <MessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
          channel="dm"
          :peer-id="peerId"
          :is-own="msg.sender.id === me?.id"
        />
      </div>

      <ComposeBox
        v-if="peerId"
        channel="dm"
        :peer-id="peerId"
        @send-typing="scrollToEnd"
      />
    </section>
  </div>
</template>

<style scoped>
.dm-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.dm-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.dm-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
}
.back-btn {
  font-size: 18px;
  color: var(--text-muted);
  padding: 4px 8px;
}
.back-btn:hover { color: var(--text); }
.dm-header-info { flex: 1; min-width: 0; }
.dm-name { font-weight: 600; }
.dm-handle { font-size: 12px; color: var(--text-muted); }
.typing-indicator { color: var(--accent-hover); font-size: 13px; font-style: italic; }
.mobile-toggle { display: none; }
.dm-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
}
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-muted);
}
.empty-icon { font-size: 56px; margin-bottom: 16px; }
.empty-state h2 { color: var(--text); margin-bottom: 8px; }

@media (max-width: 768px) {
  .mobile-toggle { display: inline-block; font-size: 18px; color: var(--text); }
}
</style>
