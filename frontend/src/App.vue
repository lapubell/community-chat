<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore, onWsEvent } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import NavBar from "@/components/NavBar.vue";
import Toasts from "@/components/Toasts.vue";

const auth = useAuthStore();
const chat = useChatStore();
const route = useRoute();
const router = useRouter();

// Short git SHA of this build (injected at build time; "dev" locally).
const gitHash = import.meta.env.APP_GIT_HASH || "dev";

const installPrompt = ref(null);
const notifPermission = ref("Notification" in window ? Notification.permission : "denied");
let unsub = null;

function beforeInstallPrompt(e) {
  e.preventDefault();
  installPrompt.value = e;
}

function handleInstall() {
  if (!installPrompt.value) return;
  installPrompt.value.prompt();
  installPrompt.value = null;
}

function requestNotifPermission() {
  if (!("Notification" in window) || notifPermission.value === "denied") return;
  Notification.requestPermission().then((p) => (notifPermission.value = p));
}

function notify(title, body, url = "/") {
  if (notifPermission.value !== "granted") return;
  try {
    const n = new Notification(title, { body, icon: "/icon-192.png", tag: title + body });
    n.onclick = () => {
      window.focus();
      window.location.href = url;
    };
  } catch {}
}

function handleWsMessage(event, msg) {
  if (!auth.user) return;
  if (msg.type === "message.new" && msg.channel === "group" && msg.message.author.id !== auth.user.id) {
    const text = msg.message.text || "sent an attachment";
    notify("Group message", `${msg.message.author.display_name}: ${text}`, "/");
  }
  if (msg.type === "dm.new") {
    const sender = msg.message.sender;
    if (sender.id !== auth.user.id) {
      const text = msg.message.text || "sent an attachment";
      notify(`Family room`, `${sender.display_name}: ${text}`, `/room/${msg.message.room_id}`);
    }
    // Refresh the sidebar room list (last message / ordering).
    chat.loadRooms().catch(() => {});
  }
}

onMounted(async () => {
  window.addEventListener("beforeinstallprompt", beforeInstallPrompt);
  chat.initWs();
  unsub = onWsEvent(handleWsMessage);

  if (auth.isAuthenticated) {
    await auth.refreshUser().catch(() => {});
    await auth.loadUsers().catch(() => {});
    auth.connectWs();
    await chat.loadGroupMessages().catch(() => {});
    await chat.loadRooms().catch(() => {});
    requestNotifPermission();
  }
});
</script>

<template>
  <div class="app-shell">
    <NavBar
      v-if="auth.isAuthenticated"
      :can-install="!!installPrompt"
      @install="handleInstall"
      @logout="() => { auth.logout(); router.push('/login'); }"
    />
    <main class="app-main">
      <RouterView />
    </main>
    <footer class="app-footer">
      <span>&copy; 2026 &middot; Community Chat</span>
      <span class="app-version" :title="'Build ' + gitHash">v{{ gitHash }}</span>
    </footer>
    <Toasts />
    <button v-if="installPrompt" class="btn install-banner" @click="handleInstall">
      Install app
    </button>
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-main {
  flex: 1;
  overflow: hidden;
  display: flex;
}
.install-banner {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  box-shadow: var(--shadow);
  padding: 12px 24px;
}
.app-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 16px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.app-version {
  font-family: monospace;
  letter-spacing: 0.02em;
}
</style>
