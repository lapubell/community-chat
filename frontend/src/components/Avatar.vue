<script setup>
defineProps({
  user: { type: Object, default: () => ({}) },
  size: { type: String, default: "md" },
});

function initials(user) {
  const name = user?.display_name || user?.handle || "?";
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function hue(name) {
  let h = 0;
  for (const c of name || "") h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}
</script>

<template>
  <div
    class="avatar"
    :class="[`avatar-${size}`]"
    :style="user?.avatar_url ? {} : { background: `hsl(${hue(user?.handle)}, 60%, 45%)` }"
  >
    <img v-if="user?.avatar_url" :src="user.avatar_url" :alt="user.display_name" />
    <template v-else>{{ initials(user) }}</template>
  </div>
</template>
