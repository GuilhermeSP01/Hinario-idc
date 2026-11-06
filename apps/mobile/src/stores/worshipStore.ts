import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import {
  getStoredWorshipEditedByUser,
  getStoredWorshipIds,
  setStoredWorshipEditedByUser,
  setStoredWorshipIds,
} from '@/services/preferences';

export const useWorshipStore = defineStore('worship', () => {
  const worshipIds = ref<string[]>([]);
  const isEditedByUser = ref<boolean>(false);
  const isWorshipViewOpen = ref<boolean>(false);
  const pendingImportedIds = ref<string[] | null>(null);

  // Estado em memória da sessão para a toast de dica de reordenação
  const hasShownReorderHintInSession = ref<boolean>(false);
  const isReorderToastVisible = ref<boolean>(false);
  let reorderToastTimeout: ReturnType<typeof setTimeout> | null = null;

  const worshipSet = computed(() => new Set(worshipIds.value));

  function showReorderHintToast(durationMs = 4200): void {
    if (reorderToastTimeout) {
      clearTimeout(reorderToastTimeout);
    }
    isReorderToastVisible.value = true;
    reorderToastTimeout = setTimeout(() => {
      isReorderToastVisible.value = false;
      reorderToastTimeout = null;
    }, durationMs);
  }

  function dismissReorderToast(): void {
    if (reorderToastTimeout) {
      clearTimeout(reorderToastTimeout);
      reorderToastTimeout = null;
    }
    isReorderToastVisible.value = false;
  }

  async function initWorship(): Promise<void> {
    const [storedIds, edited] = await Promise.all([
      getStoredWorshipIds(),
      getStoredWorshipEditedByUser(),
    ]);
    worshipIds.value = storedIds;
    isEditedByUser.value = storedIds.length > 0 ? edited : false;
  }

  function hasHymn(hymnId: string): boolean {
    return worshipSet.value.has(hymnId);
  }

  function getOrderNumber(hymnId: string): number | null {
    const idx = worshipIds.value.indexOf(hymnId);
    return idx >= 0 ? idx + 1 : null;
  }

  async function persistUserChange(nextIds: string[]): Promise<void> {
    worshipIds.value = nextIds;
    isEditedByUser.value = nextIds.length > 0;
    await Promise.all([
      setStoredWorshipIds(nextIds),
      setStoredWorshipEditedByUser(isEditedByUser.value),
    ]);
  }

  async function addHymn(hymnId: string): Promise<void> {
    if (worshipSet.value.has(hymnId)) return;
    const nextIds = [...worshipIds.value, hymnId];
    await persistUserChange(nextIds);
    if (nextIds.length > 1 && !hasShownReorderHintInSession.value) {
      hasShownReorderHintInSession.value = true;
      showReorderHintToast();
    }
  }

  async function removeHymn(hymnId: string): Promise<void> {
    if (!worshipSet.value.has(hymnId)) return;
    await persistUserChange(worshipIds.value.filter((id) => id !== hymnId));
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
      await persistUserChange(updated);
    }
  }

  async function clearWorship(): Promise<void> {
    worshipIds.value = [];
    isEditedByUser.value = false;
    await Promise.all([
      setStoredWorshipIds([]),
      setStoredWorshipEditedByUser(false),
    ]);
  }

  /**
   * Aplica imediatamente uma lista de hinos importada via link/seed,
   * marcando `isEditedByUser = false` para indicar que a lista atual veio de importação.
   */
  async function applyImportedWorship(ids: string[]): Promise<void> {
    worshipIds.value = ids;
    isEditedByUser.value = false;
    pendingImportedIds.value = null;
    isWorshipViewOpen.value = true;
    await Promise.all([
      setStoredWorshipIds(ids),
      setStoredWorshipEditedByUser(false),
    ]);
  }

  /**
   * Recebe os IDs decodificados de uma seed compartilhada:
   * - Se a lista atual estiver vazia, for idêntica ou tiver sido apenas importada antes
   *   (`!isEditedByUser`), aplica imediatamente sem pedir confirmação.
   * - Se houver hinos na lista E o usuário os editou manualmente (`isEditedByUser`),
   *   solicita confirmação antes de substituir.
   */
  async function handleIncomingSharedWorship(ids: string[]): Promise<'applied' | 'confirm_needed'> {
    const isSameList =
      ids.length === worshipIds.value.length &&
      ids.every((id, idx) => id === worshipIds.value[idx]);

    if (worshipIds.value.length === 0 || !isEditedByUser.value || isSameList) {
      await applyImportedWorship(ids);
      return 'applied';
    }

    pendingImportedIds.value = ids;
    isWorshipViewOpen.value = true;
    return 'confirm_needed';
  }

  async function confirmPendingImport(): Promise<void> {
    if (!pendingImportedIds.value) return;
    await applyImportedWorship(pendingImportedIds.value);
  }

  function cancelPendingImport(): void {
    pendingImportedIds.value = null;
  }

  return {
    worshipIds,
    isEditedByUser,
    isWorshipViewOpen,
    pendingImportedIds,
    isReorderToastVisible,
    initWorship,
    hasHymn,
    getOrderNumber,
    addHymn,
    removeHymn,
    toggleHymn,
    moveHymn,
    clearWorship,
    applyImportedWorship,
    handleIncomingSharedWorship,
    confirmPendingImport,
    cancelPendingImport,
    showReorderHintToast,
    dismissReorderToast,
  };
});
