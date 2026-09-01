<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

// Reusable centered modal. Wrap any content in the default slot.
//
//   <Modal v-model:open="show" title="Preview">
//     <img :src="url" class="preview-img" />
//   </Modal>
//
// Closes via the ✕ button, clicking the backdrop, or pressing Escape.
// Content is capped at `maxWidth`/`maxHeight` (default 500px) and 85% of the
// viewport, whichever is smaller.
const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: "" },
  // Upper bound for the content box. Kept below 85vw/85vh via CSS too.
  maxWidth: { type: Number, default: 500 },
  maxHeight: { type: Number, default: 500 },
  // Hide the header (and its ✕) for content-only modals.
  showHeader: { type: Boolean, default: true },
});

const emit = defineEmits(["update:open", "close"]);
const panel = ref(null);

function close() {
  emit("update:open", false);
  emit("close");
}

function onKeydown(e) {
  if (e.key === "Escape") close();
}

// Lock body scroll while open; focus the panel for keyboard users.
watch(
  () => props.open,
  (open) => {
    if (open) {
      document.body.style.overflow = "hidden";
      // Focus after the element is in the DOM.
      requestAnimationFrame(() => panel.value?.focus());
    } else {
      document.body.style.overflow = "";
    }
  }
);

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-backdrop"
      @click.self="close"
      role="dialog"
      aria-modal="true"
      :aria-label="title || undefined"
    >
      <div
        ref="panel"
        class="modal"
        :style="{
          maxWidth: `min(85vw, ${maxWidth}px)`,
          maxHeight: `min(85vh, ${maxHeight}px)`,
        }"
        tabindex="-1"
      >
        <div v-if="showHeader" class="modal-header">
          <span v-if="title" class="modal-title">{{ title }}</span>
          <button class="modal-close" aria-label="Close" @click="close">✕</button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.7);
  animation: modal-fade 0.15s ease-out;
}
.modal {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  outline: none;
  animation: modal-in 0.15s ease-out;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.modal-title { font-size: 15px; font-weight: 600; }
.modal-close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}
.modal-close:hover { color: var(--text); background: var(--bg-hover); }
.modal-body {
  padding: 14px;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}
@keyframes modal-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes modal-in {
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
