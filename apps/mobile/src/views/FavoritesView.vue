<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { Heart } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import HymnListItem from '@/components/HymnListItem.vue';

const router = useRouter();
const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();

const favoriteHymns = computed(() =>
  hymnsStore.sortedHymns.filter((hymn) => favoritesStore.isFavorite(hymn.id))
);

async function openHymn(hymnId: string) {
  await hymnsStore.selectHymn(hymnId);
  await router.push('/hymn');
}
</script>

<template>
  <div class="mx-auto max-w-xl px-4 pb-24 pt-4">
    <header class="mb-4 flex items-baseline justify-between">
      <h1 class="text-xl font-bold tracking-tight" style="color: var(--text-primary)">
        Hinos Favoritos
      </h1>
      <span class="text-xs font-medium" style="color: var(--text-muted)">
        {{ favoriteHymns.length }} {{ favoriteHymns.length === 1 ? 'salvo' : 'salvos' }}
      </span>
    </header>

    <TransitionGroup
      v-if="favoriteHymns.length > 0"
      name="fav-list"
      tag="div"
      class="relative flex flex-col gap-2.5"
    >
      <HymnListItem
        v-for="hymn in favoriteHymns"
        :key="hymn.id"
        :hymn="hymn"
        :is-favorite="true"
        :is-current="hymnsStore.currentHymnId === hymn.id"
        @select="openHymn"
        @toggle-favorite="favoritesStore.toggleFavorite"
      />
    </TransitionGroup>

    <div
      v-else
      class="mt-12 flex flex-col items-center justify-center rounded-2xl border p-8 text-center transition-all duration-300"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
    >
      <div
        class="mb-3 flex h-12 w-12 items-center justify-center rounded-full"
        style="background-color: var(--bg-elevated); color: var(--text-muted)"
      >
        <Heart :size="22" />
      </div>
      <p class="text-base font-medium" style="color: var(--text-primary)">
        Nenhum hino favorito ainda
      </p>
      <p class="mt-1 text-xs" style="color: var(--text-muted)">
        Toque no ícone de coração em qualquer hino para acessá-lo rapidamente aqui.
      </p>
      <button
        type="button"
        @click="router.push('/')"
        class="mt-4 rounded-lg px-4 py-2 text-xs font-semibold cursor-pointer"
        style="background-color: var(--accent-soft); color: var(--accent-primary)"
      >
        Explorar hinário
      </button>
    </div>
  </div>
</template>
