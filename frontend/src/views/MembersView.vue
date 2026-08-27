<script setup>
import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import Sidebar from "@/components/Sidebar.vue";
import Avatar from "@/components/Avatar.vue";

const router = useRouter();
const auth = useAuthStore();
const chat = useChatStore();
const { me, otherUsers } = storeToRefs(auth);
const mobileSidebar = ref(false);

onMounted(async () => {
  await auth.loadUsers().catch(() => {});
});

function timeStr(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" });
}
</script>

<template>
  <div class="members-layout">
    <Sidebar :mobile-open="mobileSidebar" @close="mobileSidebar = false" />

    <section class="members-main">
      <header class="page-header">
        <button class="mobile-toggle" @click="mobileSidebar = true">☰</button>
        <h1>Members</h1>
        <span class="count">{{ otherUsers.length + 1 }} member{{ otherUsers.length ? "s" : "" }}</span>
      </header>

      <div class="member-list">
        <div class="member-card card">
          <Avatar :user="me" size="lg" />
          <div class="member-info">
            <div class="member-name">{{ me?.display_name }} <span class="you-tag">You</span></div>
            <div class="member-handle">@{{ me?.handle }}</div>
            <p v-if="me?.bio" class="member-bio">{{ me.bio }}</p>
            <div class="member-meta">
              <span v-if="me?.email">✉️ {{ me.email }}</span>
              <span v-if="me?.phone">📞 {{ me.phone }}</span>
              <span>📅 Joined {{ timeStr(me?.created_at) }}</span>
            </div>
          </div>
        </div>

        <div
          v-for="u in otherUsers"
          :key="u.id"
          class="member-card card"
        >
          <Avatar :user="u" size="lg" />
          <div class="member-info">
            <div class="member-name">{{ u.display_name }}</div>
            <div class="member-handle">@{{ u.handle }}</div>
            <p v-if="u.bio" class="member-bio">{{ u.bio }}</p>
            <div class="member-meta">
              <span v-if="u.email">✉️ {{ u.email }}</span>
              <span v-if="u.phone">📞 {{ u.phone }}</span>
              <span>📅 Joined {{ timeStr(u.created_at) }}</span>
            </div>
          </div>
          <button class="btn msg-btn" @click="router.push({ name: 'dm', params: { userId: u.id } })">
            Message
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.members-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.members-main {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.page-header h1 { font-size: 22px; }
.count { color: var(--text-muted); font-size: 14px; }
.mobile-toggle { display: none; }
.member-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 640px;
}
.member-card {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding: 16px;
}
.member-info { flex: 1; min-width: 0; }
.member-name { font-weight: 600; font-size: 16px; }
.you-tag {
  background: var(--accent-soft);
  color: var(--accent-hover);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  margin-left: 6px;
}
.member-handle { font-size: 13px; color: var(--text-muted); }
.member-bio {
  margin-top: 8px;
  font-size: 14px;
  color: var(--text);
  white-space: pre-wrap;
}
.member-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-muted);
}
.msg-btn { align-self: center; }

@media (max-width: 768px) {
  .mobile-toggle { display: inline-block; font-size: 18px; color: var(--text); }
  .member-card { flex-wrap: wrap; }
  .msg-btn { width: 100%; }
}
</style>
