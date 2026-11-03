import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { getStoredFavoriteIds, setStoredFavoriteIds } from '@/services/preferences';

export const useFavoritesStore = defineStore('favorites', () => {
  const favoriteIds = ref<string[]>([]);

  const favoriteSet = computed(() => new Set(favoriteIds.value));

  async function initFavorites(): Promise<void> {
    favoriteIds.value = await getStoredFavoriteIds();
  }

  function isFavorite(hymnId: string): boolean {
    return favoriteSet.value.has(hymnId);
  }

  async function toggleFavorite(hymnId: string): Promise<void> {
    if (favoriteSet.value.has(hymnId)) {
      favoriteIds.value = favoriteIds.value.filter((id) => id !== hymnId);
    } else {
      favoriteIds.value = [...favoriteIds.value, hymnId];
    }
    await setStoredFavoriteIds(favoriteIds.value);
  }

  return {
    favoriteIds,
    initFavorites,
    isFavorite,
    toggleFavorite,
  };
});
