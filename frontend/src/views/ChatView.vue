<script setup>
import { onMounted, onUnmounted, ref, watch, computed } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import Sidebar from "@/components/Sidebar.vue";
import MessageBubble from "@/components/MessageBubble.vue";
import ComposeBox from "@/components/ComposeBox.vue";
import { onWsEvent } from "@/stores/auth";

const route = useRoute();
const auth = useAuthStore();
const chat = useChatStore();
const { groupMessages, dmConversations, dmMessages, typingPeer } = storeToRefs(chat);
const { me, typingNames } = storeToRefs(auth);

const scrollRef = ref(null);
const mobileSidebar = ref(false);
const loadingOlder = ref(false);
let wsUnsub = null;
let lastGroupLen = 0;

const isDm = computed(() => route.name === "dm");
const peerId = computed(() => (route.name === "dm" ? Number(route.params.userId) : null));
const peer = computed(() => auth.users.find((u) => u.id === peerId.value));
const dmMsgs = computed(() => (peerId.value ? dmMessages.value[peerId.value] || [] : []));
const showTyping = computed(() => {
  if (isDm.value) return typingPeer.value === peerId.value;
  return typingNames.value.length > 0;
});

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
  if (scrollRef.value && scrollRef.value.scrollTop < 80 && !isDm.value) {
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
  if (msg.type === "dm.new" && isDm.value && Number(route.params.userId) === msg.message.sender.id) {
    scrollToEnd();
  }
}

watch(
  () => route.name,
  async (name) => {
    if (name === "dm") {
      await chat.loadDmHistory(peerId.value);
      scrollToEnd(false);
    } else if (name === "chat") {
      scrollToEnd(false);
    }
  },
  { immediate: false }
);

onMounted(() => {
  wsUnsub = onWsEvent(handleWs);
  if (route.name === "chat") {
    requestAnimationFrame(() => scrollToEnd(false));
  }
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
        <button v-if="true" class="mobile-toggle" @click="mobileSidebar = true">☰</button>
        <template v-if="isDm">
          <span class="header-title">
            {{ peer?.display_name || "Direct message" }}
          </span>
          <span v-if="typingPeer === peerId" class="typing-indicator">typing…</span>
        </template>
        <template v-else>
          <span class="header-title">Group Chat</span>
          <span v-if="showTyping" class="typing-indicator">{{ typingNames.join(", ") }} typing…</span>
        </template>
      </header>

      <div ref="scrollRef" class="messages" @scroll="onScroll">
        <div v-if="!isDm && groupMessages.length === 0" class="empty-state">
          <div class="empty-icon">💬</div>
          <h2>Welcome to Community Chat!</h2>
          <p>Say hi to everyone — this is where our little corner of the internet lives.</p>
        </div>
        <template v-else>
          <MessageBubble
            v-for="msg in isDm ? dmMsgs : groupMessages"
            :key="msg.id"
            :message="msg"
            :channel="isDm ? 'dm' : 'group'"
            :peer-id="peerId"
            :is-own="msg.author?.id === me?.id"
          />
        </template>
      </div>

      <ComposeBox
        v-if="!isDm || peerId"
        :channel="isDm ? 'dm' : 'group'"
        :peer-id="peerId"
        @send-typing="scrollToEnd"
      />
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
