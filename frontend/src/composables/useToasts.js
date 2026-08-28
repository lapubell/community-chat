import { reactive } from "vue";

const state = reactive({ items: [] });
let id = 0;

function dismiss(id) {
  state.items = state.items.filter((t) => t.id !== id);
}

export function toast(message, type = "info", duration = 3500) {
  const tid = ++id;
  state.items.push({ id: tid, message, type });
  setTimeout(() => {
    dismiss(tid);
  }, duration);
}

export function useToasts() {
  return {
    get items() {
      return state.items;
    },
    dismiss,
  };
}
