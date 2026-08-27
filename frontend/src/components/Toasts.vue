<script setup>
import { useToasts } from "@/composables/useToasts";
const { items } = useToasts();
</script>

<template>
  <div class="toast-container">
    <div v-for="t in items" :key="t.id" class="toast" :class="`toast-${t.type}`">
      {{ t.message }}
    </div>
  </div>
</template>
