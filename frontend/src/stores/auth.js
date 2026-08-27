import { defineStore } from "pinia";
import { api, wsUrl } from "@/api";

const TYPING_TIMEOUT = 4000;
let _eventListeners = [];

function emit(event, payload) {
  for (const fn of _eventListeners) fn(event, payload);
}

export function onWsEvent(fn) {
  _eventListeners.push(fn);
  return () => {
    _eventListeners = _eventListeners.filter((f) => f !== fn);
  };
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("token"),
    user: null,
    users: [],
    ws: null,
    wsStatus: "disconnected",
    typingUsers: {},
    _pingTimer: null,
    _reconnectTimer: null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.token,
    me: (s) => s.user,
    otherUsers: (s) => (s.users || []).filter((u) => u.id !== s.user?.id),
    typingNames: (s) => {
      const now = Date.now();
      return Object.entries(s.typingUsers)
        .filter(([, t]) => now - t < TYPING_TIMEOUT)
        .map(([id]) => s.users.find((u) => u.id === Number(id))?.display_name)
        .filter(Boolean);
    },
  },
  actions: {
    async register(payload) {
      const data = await api.post("/api/auth/register", payload);
      this.token = data.token;
      this.user = data.user;
      localStorage.setItem("token", data.token);
      return data;
    },
    async login(payload) {
      const data = await api.post("/api/auth/login", payload);
      this.token = data.token;
      this.user = data.user;
      localStorage.setItem("token", data.token);
      await this.loadUsers();
      return data;
    },
    async logout() {
      this.closeWs();
      this.token = null;
      this.user = null;
      this.users = [];
      localStorage.removeItem("token");
    },
    async loadUsers() {
      this.users = await api.get("/api/auth/users");
    },
    async refreshUser() {
      this.user = await api.get("/api/auth/me");
    },
    connectWs() {
      if (this.ws || !this.token) return;
      const ws = new WebSocket(wsUrl());
      this.ws = ws;
      this.wsStatus = "connecting";
      ws.onopen = () => {
        this.wsStatus = "connected";
        this._startPing();
      };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "typing" && msg.channel === "group") {
            this.typingUsers[msg.peer_id] = Date.now();
            setTimeout(() => {
              const t = this.typingUsers[msg.peer_id];
              if (t && Date.now() - t > TYPING_TIMEOUT) delete this.typingUsers[msg.peer_id];
            }, TYPING_TIMEOUT);
          }
          emit("ws-message", msg);
        } catch {}
      };
      ws.onclose = () => {
        this.wsStatus = "disconnected";
        this._stopPing();
        if (this.token && this.ws === ws) {
          this._reconnectTimer = setTimeout(() => this.connectWs(), 3000);
        }
      };
      ws.onerror = () => {};
    },
    _startPing() {
      this._pingTimer = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    },
    _stopPing() {
      if (this._pingTimer) clearInterval(this._pingTimer);
      this._pingTimer = null;
    },
    closeWs() {
      this._stopPing();
      if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
      if (this.ws) {
        this.ws.onclose = null;
        this.ws.close();
        this.ws = null;
      }
      this.wsStatus = "disconnected";
    },
  },
});
