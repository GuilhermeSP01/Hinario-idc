<script setup lang="ts">
import { useRouter } from 'vue-router';
import { Search, X } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import HymnListItem from '@/components/HymnListItem.vue';

const router = useRouter();
const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();

async function openHymn(hymnId: string) {
  await hymnsStore.selectHymn(hymnId);
  await router.push('/hymn');
}

function clearSearch() {
  hymnsStore.searchQuery = '';
}

function onSearchInput(event: Event) {
  hymnsStore.searchQuery = (event.target as HTMLInputElement).value;
}
</script>

<template>
  <div class="mx-auto max-w-xl px-4 pb-24 pt-4">
    <!-- Cabeçalho fixo com título e barra de busca -->
    <header
      class="sticky top-0 z-20 -mx-4 px-4 pb-3 pt-2 backdrop-blur-md transition-colors"
      style="background-color: color-mix(in srgb, var(--bg-primary) 92%, transparent)"
    >
      <div class="mb-3 flex items-baseline justify-between">
        <h1 class="text-xl font-bold tracking-tight" style="color: var(--text-primary)">
          Hinário IDC
        </h1>
        <span class="text-xs font-medium" style="color: var(--text-muted)">
          {{ hymnsStore.searchResults.length }}
          {{ hymnsStore.searchResults.length === 1 ? 'hino' : 'hinos' }}
        </span>
      </div>

      <div
        class="flex items-center gap-2.5 rounded-xl border px-3.5 py-2.5 shadow-2xs transition-colors"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <Search :size="18" class="shrink-0" style="color: var(--text-muted)" />
        <input
          :value="hymnsStore.searchQuery"
          @input="onSearchInput"
          type="text"
          inputmode="search"
          autocomplete="off"
          autocorrect="off"
          autocapitalize="off"
          spellcheck="false"
          placeholder="Buscar por número, título ou trecho..."
          class="w-full bg-transparent text-sm outline-none placeholder:opacity-65"
          style="color: var(--text-primary)"
        />
        <button
          v-if="hymnsStore.searchQuery"
          type="button"
          @click="clearSearch"
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full cursor-pointer"
          style="background-color: var(--bg-elevated); color: var(--text-secondary)"
          aria-label="Limpar busca"
        >
          <X :size="14" />
        </button>
      </div>
    </header>

    <!-- Lista de Hinos -->
    <div v-if="hymnsStore.searchResults.length > 0" class="mt-2 flex flex-col gap-2.5">
      <HymnListItem
        v-for="item in hymnsStore.searchResults"
        :key="item.hymn.id"
        :hymn="item.hymn"
        :matched-snippet="item.matchedSnippet"
        :is-favorite="favoritesStore.isFavorite(item.hymn.id)"
        :is-current="hymnsStore.currentHymnId === item.hymn.id"
        @select="openHymn"
        @toggle-favorite="favoritesStore.toggleFavorite"
      />
    </div>

    <!-- Estado vazio na busca -->
    <div
      v-else
      class="mt-12 flex flex-col items-center justify-center rounded-2xl border p-8 text-center"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
    >
      <p class="text-base font-medium" style="color: var(--text-primary)">
        Nenhum hino encontrado
      </p>
      <p class="mt-1 text-xs" style="color: var(--text-muted)">
        Tente buscar por outro número, palavra do título ou trecho da letra.
      </p>
      <button
        type="button"
        @click="clearSearch"
        class="mt-4 rounded-lg px-4 py-2 text-xs font-semibold cursor-pointer"
        style="background-color: var(--accent-soft); color: var(--accent-primary)"
      >
        Limpar filtro
      </button>
    </div>
  </div>
</template>
