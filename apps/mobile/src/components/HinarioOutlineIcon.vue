<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number;
  }>(),
  {
    size: 18,
  }
);
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    :width="size"
    :height="size"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- Nota musical discreta no topo -->
    <circle cx="10.5" cy="6.5" r="1.5" />
    <path d="M12 6.5V2.5c1.6 0.2 2.8 1 3.2 2.2" />

    <!-- Livro/Hinário aberto em outline -->
    <path d="M3 10.2c2.5-.3 5.5.3 9 2.1 3.5-1.8 6.5-2.4 9-2.1v8.8c-2.5-.3-5.5.3-9 2.1-3.5-1.8-6.5-2.4-9-2.1V10.2Z" />
    <path d="M12 12.3v8.8" />
    <path d="M5.8 13.5c1.5-.1 3 .2 4.2.8" />
    <path d="M5.8 16.2c1.5-.1 3 .2 4.2.8" />
    <path d="M18.2 13.5c-1.5-.1-3 .2-4.2.8" />
    <path d="M18.2 16.2c-1.5-.1-3 .2-4.2.8" />
  </svg>
</template>
