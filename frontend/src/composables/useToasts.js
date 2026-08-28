import { reactive } from "vue";

const state = reactive({ items: [] });
let id = 0;

// Dismiss a single toast by id. Uses the module-level `state` directly so it
// works no matter how it's called (it's exposed on the reactive object so
// the component can destructure it alongside `items`, but must not rely on
// `this` — a bare call would leave `this` undefined).
function dismiss(tid) {
  state.items = state.items.filter((t) => t.id !== tid);
}

state.dismiss = dismiss;

export function toast(message, type = "info", duration = 3500) {
  const tid = ++id;
  state.items.push({ id: tid, message, type });
  setTimeout(() => {
    dismiss(tid);
  }, duration);
}

// Returns the reactive state object itself (not a copy), so destructuring
// `items` yields a reactive property that the template tracks, and `dismiss`
// is available as a plain method.
export function useToasts() {
  return state;
}
