<script setup>
import { onMounted, onUnmounted, ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import Sidebar from "@/components/Sidebar.vue";
import MessageBubble from "@/components/MessageBubble.vue";
import ComposeBox from "@/components/ComposeBox.vue";
import { onWsEvent } from "@/stores/auth";

const auth = useAuthStore();
const chat = useChatStore();
const { groupMessages } = storeToRefs(chat);
const { me, typingNames } = storeToRefs(auth);

const scrollRef = ref(null);
const mobileSidebar = ref(false);
const loadingOlder = ref(false);
let wsUnsub = null;

const showTyping = computed(() => typingNames.value.length > 0);

function scrollToEnd(smooth = true) {
  requestAnimationFrame(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTo({ top: scrollRef.value.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    }
  });
}

async function loadOlder() {
  if (loadingOlder.value) return;
  const first = groupMessages.value[0];
  if (!first) return;
  loadingOlder.value = true;
  const el = scrollRef.value;
  const prevHeight = el?.scrollHeight;
  const prevTop = el?.scrollTop;
  await chat.loadGroupMessages(first.id, 50);
  requestAnimationFrame(() => {
    if (el) el.scrollTop = el.scrollHeight - prevHeight + prevTop;
  });
  loadingOlder.value = false;
}

function onScroll() {
  if (scrollRef.value && scrollRef.value.scrollTop < 80) {
    loadOlder();
  }
}

function handleWs(msg) {
  if (msg.type === "message.new" && msg.channel === "group") {
    const el = scrollRef.value;
    const nearBottom = el ? el.scrollHeight - el.scrollTop - el.clientHeight < 120 : true;
    if (nearBottom || msg.message.author.id === me.value?.id) {
      scrollToEnd();
    }
  }
}

onMounted(() => {
  wsUnsub = onWsEvent(handleWs);
  requestAnimationFrame(() => scrollToEnd(false));
});

onUnmounted(() => {
  if (wsUnsub) wsUnsub();
});
</script>

<template>
  <div class="chat-layout">
    <Sidebar :mobile-open="mobileSidebar" @close="mobileSidebar = false" />

    <section class="chat-main">
      <header class="chat-header">
        <button class="mobile-toggle" @click="mobileSidebar = true">☰</button>
        <span class="header-title">Group Chat</span>
        <span v-if="showTyping" class="typing-indicator">{{ typingNames.join(", ") }} typing…</span>
      </header>

      <div ref="scrollRef" class="messages" @scroll="onScroll">
        <div v-if="groupMessages.length === 0" class="empty-state">
          <div class="empty-icon">💬</div>
          <h2>Welcome to Community Chat!</h2>
          <p>Say hi to everyone — this is where our little corner of the internet lives.</p>
        </div>
        <MessageBubble
          v-for="msg in groupMessages"
          :key="msg.id"
          :message="msg"
          channel="group"
          :is-own="msg.author?.id === me?.id"
        />
      </div>

      <ComposeBox channel="group" @send-typing="scrollToEnd" />
    </section>
  </div>
</template>

<style scoped>
.chat-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elevated);
}
.header-title { font-weight: 600; font-size: 16px; }
.typing-indicator { color: var(--accent-hover); font-size: 13px; font-style: italic; }
.mobile-toggle { display: none; }
.messages {
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
  padding: 40px;
}
.empty-icon { font-size: 56px; margin-bottom: 16px; }
.empty-state h2 { color: var(--text); margin-bottom: 8px; }

@media (max-width: 768px) {
  .mobile-toggle {
    display: inline-block;
    font-size: 18px;
    color: var(--text);
  }
  .bubble-col { max-width: 85% !important; }
}
</style>
