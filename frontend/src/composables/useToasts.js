import { reactive } from "vue";

const state = reactive({ items: [] });
let id = 0;

// Dismiss a single toast by id. Uses the module-level `state` directly so it
// works no matter how it's called (it's exposed on the reactive object so
// the component can destructure it alongside `items`, but must not rely on
// `this` — a bare call would leave `this` undefined).
//
// IMPORTANT: mutate the array IN PLACE (splice) rather than reassigning
// state.items. The component destructures `items` once at setup, so the
// template holds a reference to the original array; reassigning state.items
// to a new array would leave the template pointing at the old (stale) one and
// the toast would never disappear.
function dismiss(tid) {
  const i = state.items.findIndex((t) => t.id === tid);
  if (i !== -1) state.items.splice(i, 1);
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
