<script setup>
import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import { api } from "@/api";
import { toast } from "@/composables/useToasts";
import Sidebar from "@/components/Sidebar.vue";
import Avatar from "@/components/Avatar.vue";

const router = useRouter();
const auth = useAuthStore();
const chat = useChatStore();
const { me, otherUsers } = storeToRefs(auth);
const mobileSidebar = ref(false);

const showInvite = ref(false);
const inviteCode = ref("");
const inviteMaxUses = ref(1);
const inviteNote = ref("");
const creatingInvite = ref(false);

onMounted(async () => {
  await auth.loadUsers().catch(() => {});
});

function timeStr(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" });
}

async function createInvite() {
  creatingInvite.value = true;
  try {
    const invite = await api.post("/api/invites", {
      max_uses: inviteMaxUses.value,
      note: inviteNote.value.trim() || null,
    });
    inviteCode.value = invite.code;
    inviteNote.value = "";
    toast("Invite created", "success");
  } catch (e) {
    toast(e.message, "error");
  } finally {
    creatingInvite.value = false;
  }
}

async function copyInvite() {
  if (!inviteCode.value) return;
  await navigator.clipboard.writeText(inviteCode.value);
  toast("Copied to clipboard", "success");
}

function inviteLink() {
  return `${window.location.origin}/login?code=${inviteCode.value}`;
}

async function copyLink() {
  await navigator.clipboard.writeText(inviteLink());
  toast("Copied link", "success");
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
        <button class="btn invite-cta" @click="showInvite = !showInvite">
          {{ showInvite ? "Close" : "➕ Invite a member" }}
        </button>
      </header>

      <div v-if="showInvite" class="invite-card card">
        <h2>Invite someone to join</h2>
        <p class="hint">
          Share this invite code (or the link) with a family member or friend. They use it on
          the <strong>Join with invite</strong> tab to create their account.
        </p>

        <div class="invite-form">
          <label>
            Max uses
            <input v-model.number="inviteMaxUses" type="number" min="1" max="100" class="invite-num" />
          </label>
          <label class="flex1">
            Note (optional)
            <input v-model="inviteNote" placeholder="e.g. for Grandma" maxlength="200" />
          </label>
          <button class="btn" :disabled="creatingInvite" @click="createInvite">
            {{ creatingInvite ? "Creating…" : "Create invite" }}
          </button>
        </div>

        <div v-if="inviteCode" class="invite-result">
          <div class="invite-code-row">
            <code class="invite-code">{{ inviteCode }}</code>
            <button class="btn btn-ghost btn-sm" @click="copyInvite">Copy code</button>
          </div>
          <div class="invite-link-row">
            <span class="invite-link-label">Link:</span>
            <code class="invite-link">{{ inviteLink() }}</code>
            <button class="btn btn-ghost btn-sm" @click="copyLink">Copy link</button>
          </div>
        </div>
      </div>

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
.count { color: var(--text-muted); font-size: 14px; margin-left: auto; }
.invite-cta { margin-left: 12px; }
.mobile-toggle { display: none; }
.invite-card {
  max-width: 640px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.invite-card h2 { font-size: 16px; }
.hint { color: var(--text-muted); font-size: 13px; line-height: 1.5; }
.invite-form {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}
.invite-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}
.invite-form label.flex1 { flex: 1; }
.invite-num { width: 80px; }
.invite-result {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--accent-soft);
  border-radius: var(--radius-sm);
}
.invite-code-row,
.invite-link-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.invite-code {
  font-family: monospace;
  font-size: 18px;
  letter-spacing: 0.1em;
  background: var(--bg);
  padding: 6px 12px;
  border-radius: 6px;
}
.invite-link-row {
  align-items: center;
}
.invite-link-label { font-size: 12px; color: var(--text-muted); }
.invite-link {
  flex: 1;
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: var(--bg);
  padding: 6px 10px;
  border-radius: 6px;
}
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
