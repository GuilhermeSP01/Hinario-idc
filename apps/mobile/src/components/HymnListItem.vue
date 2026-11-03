<script setup lang="ts">
import type { Hymn } from '@hinario/core';
import FavoriteButton from '@/components/FavoriteButton.vue';

defineProps<{
  hymn: Hymn;
  matchedSnippet?: string;
  isFavorite: boolean;
  isCurrent?: boolean;
}>();

const emit = defineEmits<{
  select: [hymnId: string];
  toggleFavorite: [hymnId: string];
}>();
</script>

<template>
  <div
    role="button"
    tabindex="0"
    @click="emit('select', hymn.id)"
    @keydown.enter="emit('select', hymn.id)"
    class="group flex items-center justify-between gap-3 rounded-xl border px-4 py-3.5 transition-all active:scale-[0.99] cursor-pointer"
    :style="{
      backgroundColor: 'var(--bg-surface)',
      borderColor: isCurrent ? 'var(--accent-primary)' : 'var(--border-subtle)',
    }"
  >
    <div class="flex items-start gap-3.5 min-w-0 flex-1">
      <div
        class="flex h-10 min-w-10 shrink-0 items-center justify-center rounded-lg px-2 text-sm font-bold"
        style="background-color: var(--accent-soft); color: var(--accent-primary)"
      >
        {{ hymn.number }}
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <h3
            class="truncate text-base font-semibold leading-snug"
            style="color: var(--text-primary)"
          >
            {{ hymn.title }}
          </h3>
        </div>

        <p
          v-if="matchedSnippet"
          class="mt-1 line-clamp-1 text-xs italic"
          style="color: var(--text-secondary)"
        >
          “{{ matchedSnippet }}”
        </p>
        <p
          v-else-if="hymn.sections[0]?.lines[0]"
          class="mt-0.5 truncate text-xs"
          style="color: var(--text-muted)"
        >
          {{ hymn.sections[0].lines[0] }}
        </p>
      </div>
    </div>

    <FavoriteButton
      :is-favorite="isFavorite"
      :size="19"
      variant="ghost"
      @toggle="emit('toggleFavorite', hymn.id)"
    />
  </div>
</template>
