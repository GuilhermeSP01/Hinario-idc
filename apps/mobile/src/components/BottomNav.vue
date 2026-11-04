<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';
import { BookOpen, Heart, ListMusic, Settings } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';

const route = useRoute();
const router = useRouter();
const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();

const tabs = [
  { name: 'home', path: '/', label: 'Início', icon: ListMusic },
  { name: 'hymn', path: '/hymn', label: 'Hino', icon: BookOpen },
  { name: 'favorites', path: '/favorites', label: 'Salvos', icon: Heart },
  { name: 'settings', path: '/settings', label: 'Ajustes', icon: Settings },
] as const;

function navigateTo(path: string) {
  if (route.path !== path) {
    router.push(path);
  }
}
</script>

<template>
  <nav
    class="fixed bottom-0 left-0 right-0 z-40 border-t safe-bottom transition-colors duration-200"
    style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
    aria-label="Navegação Principal"
  >
    <div class="mx-auto flex max-w-xl items-center justify-around h-16 px-2">
      <button
        v-for="tab in tabs"
        :key="tab.name"
        type="button"
        @click="navigateTo(tab.path)"
        class="relative flex flex-1 flex-col items-center justify-center h-full gap-1 transition-colors cursor-pointer"
        :style="{
          color: route.path === tab.path ? 'var(--accent-primary)' : 'var(--text-muted)',
        }"
      >
        <div class="relative flex h-6 w-6 items-center justify-center">
          <component
            :is="tab.icon"
            :size="22"
            :stroke-width="route.path === tab.path ? 2.4 : 1.9"
          />
          <Transition name="badge-pop" mode="out-in">
            <span
              v-if="tab.name === 'hymn' && hymnsStore.currentHymn"
              :key="hymnsStore.currentHymn.number"
              class="pointer-events-none absolute -top-1.5 left-full ml-0.5 whitespace-nowrap rounded-full px-1.5 py-0.2 text-[10px] font-bold leading-tight"
              style="background-color: var(--accent-soft); color: var(--accent-primary)"
            >
              #{{ hymnsStore.currentHymn.number }}
            </span>
          </Transition>
          <Transition name="badge-pop" mode="out-in">
            <span
              v-if="tab.name === 'favorites' && favoritesStore.favoriteIds.length > 0"
              :key="favoritesStore.favoriteIds.length"
              class="pointer-events-none absolute -top-1.5 left-full ml-0.5 whitespace-nowrap rounded-full px-1.5 py-0.2 text-[10px] font-bold leading-tight"
              style="background-color: var(--accent-soft); color: var(--accent-primary)"
            >
              {{ favoritesStore.favoriteIds.length }}
            </span>
          </Transition>
        </div>
        <span class="text-xs font-medium tracking-tight">
          {{ tab.label }}
        </span>
      </button>
    </div>
  </nav>
</template>
