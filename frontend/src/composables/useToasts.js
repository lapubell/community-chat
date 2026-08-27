import { reactive } from "vue";

const state = reactive({ items: [] });
let id = 0;

export function toast(message, type = "info", duration = 3500) {
  const tid = ++id;
  state.items.push({ id: tid, message, type });
  setTimeout(() => {
    state.items = state.items.filter((t) => t.id !== tid);
  }, duration);
}

export function useToasts() {
  return state;
}
