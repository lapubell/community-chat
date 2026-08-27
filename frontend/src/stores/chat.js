import { defineStore } from "pinia";
import { api } from "@/api";
import { onWsEvent, useAuthStore } from "./auth";

export const useChatStore = defineStore("chat", {
  state: () => ({
    groupMessages: [],
    dmConversations: [],
    dmMessages: {},
    typingPeer: null,
    _typingTimer: null,
    _wsUnsub: null,
  }),
  getters: {
    unreadDmTotal: (s) => s.dmConversations.reduce((sum, c) => sum + c.unread_count, 0),
  },
  actions: {
    initWs() {
      if (this._wsUnsub) return;
      this._wsUnsub = onWsEvent((event, msg) => this._handleWs(msg));
    },
    _handleWs(msg) {
      switch (msg.type) {
        case "message.new":
          if (msg.channel === "group") this._addGroupMessage(msg.message);
          break;
        case "message.edited":
          this._editGroupMessage(msg.message);
          break;
        case "message.deleted":
          this._deleteGroupMessage(msg.message_id);
          break;
        case "dm.new":
          this._addDmMessage(msg.message);
          break;
        case "dm.read":
          this._markDmReadLocally(msg);
          break;
        case "reaction.changed":
          this._updateReaction(msg);
          break;
        case "typing":
          if (msg.channel === "dm") this._setTypingPeer(msg.peer_id);
          break;
      }
    },
    async loadGroupMessages(beforeId = null, limit = 50) {
      const qs = new URLSearchParams({ limit: String(limit) });
      if (beforeId) qs.set("before_id", String(beforeId));
      const messages = await api.get(`/api/messages?${qs}`);
      if (beforeId) this.groupMessages = [...messages, ...this.groupMessages];
      else this.groupMessages = messages;
      return messages;
    },
    _addGroupMessage(message) {
      if (this.groupMessages.some((m) => m.id === message.id)) return;
      this.groupMessages.push(message);
    },
    _editGroupMessage(message) {
      const idx = this.groupMessages.findIndex((m) => m.id === message.id);
      if (idx >= 0) this.groupMessages.splice(idx, 1, message);
    },
    _deleteGroupMessage(id) {
      this.groupMessages = this.groupMessages.filter((m) => m.id !== id);
    },
    async sendGroupMessage({ text, fileUrl, fileName, fileContentType, replyToId }) {
      const message = await api.post("/api/messages", {
        text,
        file_url: fileUrl,
        file_name: fileName,
        file_content_type: fileContentType,
        reply_to_id: replyToId,
      });
      this._addGroupMessage(message);
      return message;
    },
    async editGroupMessage(id, text) {
      const message = await api.patch(`/api/messages/${id}`, { text });
      this._editGroupMessage(message);
      return message;
    },
    async deleteGroupMessage(id) {
      await api.del(`/api/messages/${id}`);
      this._deleteGroupMessage(id);
    },
    async addReaction(messageId, emoji) {
      const result = await api.post(`/api/messages/${messageId}/reactions/${encodeURIComponent(emoji)}`);
      this._applyReaction(this.groupMessages.find((m) => m.id === messageId), result);
      return result;
    },
    async removeReaction(messageId, emoji) {
      const result = await api.del(`/api/messages/${messageId}/reactions/${encodeURIComponent(emoji)}`);
      const msg = this.groupMessages.find((m) => m.id === messageId);
      if (msg) msg.reactions = msg.reactions.filter((r) => r.emoji !== emoji);
      return result;
    },
    _applyReaction(message, result) {
      if (!message) return;
      const existing = message.reactions.find((r) => r.emoji === result.emoji);
      if (existing) {
        existing.user_ids = result.user_ids;
        existing.count = result.count;
      } else {
        message.reactions.push(result);
      }
    },
    async loadDmConversations() {
      this.dmConversations = await api.get("/api/dms/conversations");
    },
    async loadDmHistory(userId) {
      const messages = await api.get(`/api/dms/with/${userId}`);
      this.dmMessages[userId] = messages;
      return messages;
    },
    _addDmMessage(message) {
      const peerId = message.sender.id === this._meId ? message.recipient_id : message.sender.id;
      if (!this.dmMessages[peerId]) this.dmMessages[peerId] = [];
      if (this.dmMessages[peerId].some((m) => m.id === message.id)) return;
      this.dmMessages[peerId].push(message);
      const convo = this.dmConversations.find((c) => c.peer.id === peerId);
      if (convo) {
        convo.last_message = message;
        convo.last_at = message.created_at;
        if (message.sender.id !== this._meId) convo.unread_count += 1;
      } else {
        this.loadDmConversations();
      }
    },
    _markDmReadLocally(msg) {
      const convo = this.dmConversations.find((c) => c.peer.id === msg.peer_id);
      if (convo) {
        const dmMsgs = this.dmMessages[msg.peer_id] || [];
        for (const m of dmMsgs) if (m.id <= msg.up_to_id && m.sender.id === msg.peer_id) m.read_at = m.read_at || new Date().toISOString();
        if (msg.peer_id === this._meId) convo.unread_count = 0;
      }
    },
    async sendDmMessage(userId, { text, fileUrl, fileName, fileContentType }) {
      const message = await api.post(`/api/dms/with/${userId}`, {
        text,
        file_url: fileUrl,
        file_name: fileName,
        file_content_type: fileContentType,
      });
      if (!this.dmMessages[userId]) this.dmMessages[userId] = [];
      this.dmMessages[userId].push(message);
      const convo = this.dmConversations.find((c) => c.peer.id === userId);
      if (convo) {
        convo.last_message = message;
        convo.last_at = message.created_at;
      }
      return message;
    },
    async markDmRead(userId, upToId) {
      await api.post(`/api/dms/${upToId}/read`);
      const convo = this.dmConversations.find((c) => c.peer.id === userId);
      if (convo) convo.unread_count = 0;
    },
    async addDmReaction(messageId, emoji) {
      const result = await api.post(`/api/dms/${messageId}/reactions/${encodeURIComponent(emoji)}`);
      for (const key in this.dmMessages) {
        const msg = this.dmMessages[key].find((m) => m.id === messageId);
        if (msg) this._applyReaction(msg, result);
      }
      return result;
    },
    _setTypingPeer(peerId) {
      this.typingPeer = peerId;
      clearTimeout(this._typingTimer);
      this._typingTimer = setTimeout(() => (this.typingPeer = null), 3000);
    },
    sendTyping(channel, peerId) {
      const auth = useAuthStore();
      if (auth.ws?.readyState === WebSocket.OPEN) {
        auth.ws.send(JSON.stringify({ type: "typing", channel, peer_id: peerId }));
      }
    },
    get _meId() {
      return useAuthStore().user?.id;
    },
  },
});
