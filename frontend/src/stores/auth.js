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

// Reconnect tuning. We keep retrying (with exponential backoff, capped) as long
// as the user is authenticated and the browser reports network connectivity, so
// a dropped socket — e.g. from a server rebuild — recovers automatically.
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 15000;
const PING_INTERVAL_MS = 25000;
const PONG_TIMEOUT_MS = 45000; // no pong within this window => socket is dead

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
    _reconnectDelay: RECONNECT_BASE_MS,
    _lastPong: 0,
    _intentionalClose: false,
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
      // Only one live/attempting socket at a time, and only when authenticated.
      if (this.ws || !this.token) return;
      this._intentionalClose = false;
      const ws = new WebSocket(wsUrl());
      this.ws = ws;
      this.wsStatus = "connecting";
      ws.onopen = () => {
        this.wsStatus = "connected";
        this._reconnectDelay = RECONNECT_BASE_MS; // reset backoff on success
        this._lastPong = Date.now();
        this._startPing();
      };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "pong") {
            this._lastPong = Date.now();
            return;
          }
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
        if (this.ws === ws) this.ws = null;
        // Reconnect unless the user logged out (intentional close).
        if (this.token && !this._intentionalClose) this._scheduleReconnect();
      };
      ws.onerror = () => {
        // onclose follows onerror; nothing to do here.
      };
    },
    _scheduleReconnect() {
      if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
      // Don't retry while the browser reports we're offline; the `online`
      // event (wired in App.vue) will nudge us when connectivity returns.
      if (typeof navigator !== "undefined" && navigator.onLine === false) {
        this.wsStatus = "offline";
        return;
      }
      const delay = this._reconnectDelay;
      this._reconnectDelay = Math.min(this._reconnectDelay * 2, RECONNECT_MAX_MS);
      this.wsStatus = "reconnecting";
      this._reconnectTimer = setTimeout(() => {
        this._reconnectTimer = null;
        this.connectWs();
      }, delay);
    },
    // Called when the app regains focus or the network returns: drop the
    // backoff and attempt an immediate reconnect if we're authenticated but
    // not connected.
    nudgeReconnect() {
      if (!this.token) return;
      if (this.ws && this.ws.readyState === WebSocket.OPEN) return; // already fine
      this._reconnectDelay = RECONNECT_BASE_MS;
      this._scheduleReconnect();
    },
    _startPing() {
      this._pingTimer = setInterval(() => {
        // Liveness: if we haven't heard a pong in a while, the socket is dead
        // (e.g. server restarted) — force-close it so onclose triggers a
        // reconnect. Otherwise, ping to keep it alive and refresh liveness.
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        if (Date.now() - this._lastPong > PONG_TIMEOUT_MS) {
          this.ws.close(); // triggers onclose -> reconnect
          return;
        }
        this.ws.send(JSON.stringify({ type: "ping" }));
      }, PING_INTERVAL_MS);
    },
    _stopPing() {
      if (this._pingTimer) clearInterval(this._pingTimer);
      this._pingTimer = null;
    },
    closeWs() {
      this._intentionalClose = true;
      this._stopPing();
      if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer);
        this._reconnectTimer = null;
      }
      if (this.ws) {
        this.ws.onclose = null;
        this.ws.onerror = null;
        this.ws.close();
        this.ws = null;
      }
      this.wsStatus = "disconnected";
    },
  },
});
