<script setup>
import { ref } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";

const props = defineProps({
  reactions: { type: Array, default: () => [] },
  messageId: Number,
  channel: { type: String, default: "group" },
});

const auth = useAuthStore();
const chat = useChatStore();
const pickerOpen = ref(false);

const EMOJIS = ["👍", "❤️", "😂", "😮", "😢", "🙏", "🎉", "👀", "🥳", "😍", "🤔", "👎", "🔥", "✨", "💪", "🥰"];

function hasReacted(emoji) {
  const r = props.reactions.find((x) => x.emoji === emoji);
  return r ? r.user_ids.includes(auth.user?.id) : false;
}

async function toggle(emoji) {
  if (props.channel === "group") {
    if (hasReacted(emoji)) await chat.removeReaction(props.messageId, emoji);
    else await chat.addReaction(props.messageId, emoji);
  }
}

function pick(emoji) {
  pickerOpen.value = false;
  toggle(emoji);
}
</script>

<template>
  <div class="reactions" v-if="reactions.length || true">
    <div class="reaction-row">
      <button
        v-for="r in reactions"
        :key="r.emoji"
        class="reaction-pill"
        :class="{ mine: r.user_ids.includes(auth.user?.id) }"
        @click="channel === 'group' && toggle(r.emoji)"
        :title="r.user_ids.length + ' reaction(s)'"
      >
        {{ r.emoji }} {{ r.count }}
      </button>
      <button class="reaction-add" @click="pickerOpen = !pickerOpen" title="Add reaction">
        😊+
      </button>
    </div>
    <div v-if="pickerOpen && channel === 'group'" class="picker">
      <button v-for="e in EMOJIS" :key="e" class="picker-emoji" @click="pick(e)">{{ e }}</button>
    </div>
  </div>
</template>

<style scoped>
.reactions { margin-top: 4px; position: relative; }
.reaction-row { display: flex; flex-wrap: wrap; gap: 4px; }
.reaction-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--bg-hover);
  font-size: 13px;
  border: 1px solid transparent;
  transition: border-color 0.15s;
}
.reaction-pill:hover { border-color: var(--text-muted); }
.reaction-pill.mine { background: var(--accent-soft); border-color: var(--accent); }
.reaction-add {
  font-size: 13px;
  padding: 2px 8px;
  border-radius: 10px;
  color: var(--text-muted);
  border: 1px dashed var(--border);
}
.reaction-add:hover { border-color: var(--text-muted); }
.picker {
  position: absolute;
  bottom: 100%;
  left: 0;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
  box-shadow: var(--shadow);
  z-index: 10;
}
.picker-emoji {
  font-size: 18px;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.1s;
}
.picker-emoji:hover { background: var(--bg-hover); }
</style>
