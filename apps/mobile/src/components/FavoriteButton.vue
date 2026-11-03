<script setup lang="ts">
import { ref, watch } from 'vue';
import { Heart } from 'lucide-vue-next';

const props = withDefaults(
  defineProps<{
    isFavorite: boolean;
    size?: number;
    variant?: 'ghost' | 'bordered';
  }>(),
  {
    size: 19,
    variant: 'ghost',
  }
);

const emit = defineEmits<{
  toggle: [];
}>();

const animState = ref<'idle' | 'pop' | 'unpop'>('idle');
let timer: ReturnType<typeof setTimeout> | null = null;

watch(
  () => props.isFavorite,
  (newVal, oldVal) => {
    if (newVal === oldVal) return;
    if (timer) clearTimeout(timer);
    animState.value = newVal ? 'pop' : 'unpop';
    timer = setTimeout(() => {
      animState.value = 'idle';
    }, 450);
  }
);

function handleClick(event: MouseEvent) {
  event.stopPropagation();
  emit('toggle');
}
</script>

<template>
  <button
    type="button"
    @click="handleClick"
    :class="[
      'relative flex shrink-0 items-center justify-center transition-all duration-200 active:scale-90 cursor-pointer',
      variant === 'bordered' ? 'h-10 w-10 rounded-xl border' : 'h-9 w-9 rounded-full',
    ]"
    :style="{
      backgroundColor: variant === 'bordered' ? 'var(--bg-surface)' : 'transparent',
      borderColor:
        variant === 'bordered'
          ? isFavorite
            ? 'color-mix(in srgb, #ef4444 35%, var(--border-subtle))'
            : 'var(--border-subtle)'
          : 'transparent',
      color: isFavorite ? '#ef4444' : 'var(--text-muted)',
    }"
    :aria-label="isFavorite ? 'Remover dos favoritos' : 'Adicionar aos favoritos'"
    :aria-pressed="isFavorite"
  >
    <!-- Anel expansivo suave ao favoritar -->
    <span
      v-if="animState === 'pop'"
      class="pointer-events-none absolute inset-0 rounded-full animate-heart-ring"
    />

    <Heart
      :size="size"
      :fill="isFavorite ? '#ef4444' : 'none'"
      :class="[
        'transition-colors duration-200',
        animState === 'pop' ? 'animate-heart-pop' : '',
        animState === 'unpop' ? 'animate-heart-unpop' : '',
      ]"
    />
  </button>
</template>
