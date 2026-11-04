import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { getStoredWorshipIds, setStoredWorshipIds } from '@/services/preferences';

export const useWorshipStore = defineStore('worship', () => {
  const worshipIds = ref<string[]>([]);

  const worshipSet = computed(() => new Set(worshipIds.value));

  async function initWorship(): Promise<void> {
    worshipIds.value = await getStoredWorshipIds();
  }

  function hasHymn(hymnId: string): boolean {
    return worshipSet.value.has(hymnId);
  }

  function getOrderNumber(hymnId: string): number | null {
    const idx = worshipIds.value.indexOf(hymnId);
    return idx >= 0 ? idx + 1 : null;
  }

  async function addHymn(hymnId: string): Promise<void> {
    if (worshipSet.value.has(hymnId)) return;
    worshipIds.value = [...worshipIds.value, hymnId];
    await setStoredWorshipIds(worshipIds.value);
  }

  async function removeHymn(hymnId: string): Promise<void> {
    if (!worshipSet.value.has(hymnId)) return;
    worshipIds.value = worshipIds.value.filter((id) => id !== hymnId);
    await setStoredWorshipIds(worshipIds.value);
  }

  async function toggleHymn(hymnId: string): Promise<void> {
    if (worshipSet.value.has(hymnId)) {
      await removeHymn(hymnId);
    } else {
      await addHymn(hymnId);
    }
  }

  async function moveHymn(fromIndex: number, toIndex: number): Promise<void> {
    if (
      fromIndex === toIndex ||
      fromIndex < 0 ||
      toIndex < 0 ||
      fromIndex >= worshipIds.value.length ||
      toIndex >= worshipIds.value.length
    ) {
      return;
    }
    const updated = [...worshipIds.value];
    const [moved] = updated.splice(fromIndex, 1);
    if (moved !== undefined) {
      updated.splice(toIndex, 0, moved);
      worshipIds.value = updated;
      await setStoredWorshipIds(worshipIds.value);
    }
  }

  async function clearWorship(): Promise<void> {
    worshipIds.value = [];
    await setStoredWorshipIds([]);
  }

  return {
    worshipIds,
    initWorship,
    hasHymn,
    getOrderNumber,
    addHymn,
    removeHymn,
    toggleHymn,
    moveHymn,
    clearWorship,
  };
});
