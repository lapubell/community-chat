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

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const chat = useChatStore();
const { me } = storeToRefs(auth);
const { roomMessages } = storeToRefs(chat);

const scrollRef = ref(null);
const mobileSidebar = ref(false);

const roomId = computed(() => Number(route.params.roomId));
const messages = computed(() => roomMessages.value[roomId.value] || []);

const metaFamilies = computed(() => {
  const room = chat.rooms.find((r) => r.id === roomId.value);
  if (room?.families) return room.families;
  return chat.roomMeta[roomId.value]?.families || [];
});

const myFamilyId = me.value?.family_id;

function scrollToEnd(smooth = true) {
  requestAnimationFrame(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTo({ top: scrollRef.value.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    }
  });
}

function isOwn(m) {
  return m.sender?.id === me.value?.id;
}

function handleWs(msg) {
  if (msg.type === "dm.new" && msg.message.room_id === roomId.value) {
    scrollToEnd();
  }
}

watch(
  () => route.params.roomId,
  async (id) => {
    if (id) {
      await chat.loadRoomHistory(Number(id));
      scrollToEnd(false);
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
  <div class="room-layout">
    <Sidebar :mobile-open="mobileSidebar" @close="mobileSidebar = false" />

    <section class="room-main">
      <header class="room-header">
        <button class="mobile-toggle" @click="mobileSidebar = true">☰</button>
        <button class="back-btn" @click="router.push('/families')">←</button>
        <div class="room-families">
          <div
            v-for="f in metaFamilies"
            :key="f.id"
            class="room-family-chip"
            :class="{ self: f.id === myFamilyId }"
          >
            <img v-if="f.avatar_url" :src="f.avatar_url" class="chip-avatar" :alt="f.name" />
            <span v-else class="chip-avatar placeholder">🏠</span>
            <span class="chip-name">{{ f.name }}</span>
          </div>
        </div>
      </header>

      <div ref="scrollRef" class="room-messages">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">💬</div>
          <h2>No messages yet</h2>
          <p>Start the conversation with your family members!</p>
        </div>
        <MessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
          channel="room"
          :is-own="isOwn(msg)"
        />
      </div>

      <ComposeBox
        v-if="roomId"
        channel="room"
        :peer-id="roomId"
        @send-typing="scrollToEnd"
      />
    </section>
  </div>
</template>

<style scoped>
.room-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.room-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.room-header {
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
.room-families { display: flex; gap: 8px; flex-wrap: wrap; }
.room-family-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  background: var(--bg-hover);
  font-size: 13px;
  font-weight: 500;
}
.room-family-chip.self { background: var(--accent-soft); color: var(--accent-hover); }
.chip-avatar {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  object-fit: cover;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.chip-avatar.placeholder { background: var(--bg); font-size: 12px; }
.room-messages {
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
.mobile-toggle { display: none; }

@media (max-width: 768px) {
  .mobile-toggle { display: inline-block; font-size: 18px; color: var(--text); }
}
</style>
