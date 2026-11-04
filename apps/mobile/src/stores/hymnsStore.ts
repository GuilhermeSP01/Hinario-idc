import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { HymnSearchEngine, type Hymn, type HymnSearchResult } from '@hinario/core';
import {
  fetchHymnsDelta,
  fetchRemoteMetadata,
  getOrInitFirestore,
  INITIAL_HINARIO_VERSION,
  INITIAL_HYMNS_SEED,
} from '@hinario/firebase';
import { localDb } from '@/db/localDatabase';
import {
  getStoredLastHymnId,
  getStoredLocalVersion,
  setStoredLastHymnId,
  setStoredLocalVersion,
} from '@/services/preferences';

const SEARCH_CACHE_ID = 'main';

export const useHymnsStore = defineStore('hymns', () => {
  const hymns = ref<Hymn[]>([]);
  const currentHymnId = ref<string | null>(null);
  const searchQuery = ref<string>('');
  const localVersion = ref<number>(0);
  const isReady = ref<boolean>(false);

  const searchEngine = new HymnSearchEngine();

  const hymnsById = computed(() => {
    const map = new Map<string, Hymn>();
    for (const h of hymns.value) {
      if (!h.deleted) {
        map.set(h.id, h);
      }
    }
    return map;
  });

  const sortedHymns = computed(() =>
    [...hymns.value]
      .filter((h) => !h.deleted)
      .sort((a, b) => a.number - b.number || a.title.localeCompare(b.title, 'pt-BR'))
  );

  const currentHymn = computed<Hymn | null>(() => {
    if (currentHymnId.value && hymnsById.value.has(currentHymnId.value)) {
      return hymnsById.value.get(currentHymnId.value) ?? null;
    }
    return sortedHymns.value[0] ?? null;
  });

  const currentHymnIndex = computed(() => {
    if (!currentHymn.value) return -1;
    return sortedHymns.value.findIndex((h) => h.id === currentHymn.value?.id);
  });

  const previousHymn = computed<Hymn | null>(() => {
    const idx = currentHymnIndex.value;
    return idx > 0 ? (sortedHymns.value[idx - 1] ?? null) : null;
  });

  const nextHymn = computed<Hymn | null>(() => {
    const idx = currentHymnIndex.value;
    return idx >= 0 && idx < sortedHymns.value.length - 1
      ? (sortedHymns.value[idx + 1] ?? null)
      : null;
  });

  const searchResults = computed<HymnSearchResult[]>(() => {
    return searchEngine.search(searchQuery.value, hymnsById.value);
  });

  /**
   * Carrega ou reconstrói o índice de busca, utilizando o cache no IndexedDB
   * caso a versão e quantidade de hinos não tenham mudado.
   */
  async function loadOrBuildSearchIndex(activeHymns: Hymn[], version: number): Promise<void> {
    const cached = await localDb.searchCache.get(SEARCH_CACHE_ID);
    if (
      cached &&
      cached.version === version &&
      cached.hymnCount === activeHymns.length &&
      searchEngine.loadSerializedIndex(cached.serializedIndex)
    ) {
      return;
    }

    searchEngine.buildIndex(activeHymns);
    await localDb.searchCache.put({
      id: SEARCH_CACHE_ID,
      version,
      hymnCount: activeHymns.length,
      serializedIndex: searchEngine.serializeIndex(),
      updatedAt: new Date().toISOString(),
    });
  }

  /**
   * Inicializa a camada local (IndexedDB + Seed inicial) e dispara a sincronização
   * silenciosa em background com o Firestore quando conectado à internet.
   */
  async function initHymns(): Promise<void> {
    let version = await getStoredLocalVersion();
    let storedHymns = await localDb.hymns.toArray();

    // Primeiro uso ou atualização do seed embutido no app: popula/atualiza o IndexedDB
    if (storedHymns.length === 0 || version < INITIAL_HINARIO_VERSION) {
      await localDb.transaction('rw', localDb.hymns, async () => {
        await localDb.hymns.clear();
        await localDb.hymns.bulkPut(INITIAL_HYMNS_SEED);
      });
      storedHymns = [...INITIAL_HYMNS_SEED];
      version = INITIAL_HINARIO_VERSION;
      await setStoredLocalVersion(version);
    }

    const activeHymns = storedHymns.filter((h) => !h.deleted);
    hymns.value = activeHymns;
    localVersion.value = version;

    await loadOrBuildSearchIndex(activeHymns, version);

    // Restaura o último hino aberto ou seleciona o primeiro hino
    const lastId = await getStoredLastHymnId();
    if (lastId && activeHymns.some((h) => h.id === lastId)) {
      currentHymnId.value = lastId;
    } else if (activeHymns.length > 0) {
      const first = [...activeHymns].sort((a, b) => a.number - b.number)[0];
      if (first) {
        currentHymnId.value = first.id;
      }
    }

    isReady.value = true;

    // Dispara a verificação silenciosa em background (sem bloquear a UI)
    void syncWithFirestoreInBackground();

    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        void syncWithFirestoreInBackground();
      });
    }
  }

  /**
   * Verifica silenciosamente a versão atual no Firestore e baixa apenas o delta de hinos.
   */
  async function syncWithFirestoreInBackground(): Promise<void> {
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return;
    }

    const db = getOrInitFirestore({
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
    });

    if (!db) return;

    try {
      const remoteMeta = await fetchRemoteMetadata(db);
      if (!remoteMeta || remoteMeta.currentVersion <= localVersion.value) {
        return;
      }

      const deltaHymns = await fetchHymnsDelta(db, localVersion.value);
      if (deltaHymns.length > 0) {
        const toDeleteIds = deltaHymns.filter((h) => h.deleted).map((h) => h.id);
        const toUpsert = deltaHymns.filter((h) => !h.deleted);

        await localDb.transaction('rw', localDb.hymns, async () => {
          if (toDeleteIds.length > 0) {
            await localDb.hymns.bulkDelete(toDeleteIds);
          }
          if (toUpsert.length > 0) {
            await localDb.hymns.bulkPut(toUpsert);
          }
        });
      }

      const updatedHymns = (await localDb.hymns.toArray()).filter((h) => !h.deleted);
      hymns.value = updatedHymns;
      localVersion.value = remoteMeta.currentVersion;
      await setStoredLocalVersion(remoteMeta.currentVersion);

      // Atualiza o índice em memória e persiste o novo cache no IndexedDB
      searchEngine.buildIndex(updatedHymns);
      await localDb.searchCache.put({
        id: SEARCH_CACHE_ID,
        version: remoteMeta.currentVersion,
        hymnCount: updatedHymns.length,
        serializedIndex: searchEngine.serializeIndex(),
        updatedAt: new Date().toISOString(),
      });
    } catch {
      // Falha de rede ou permissão ignorada silenciosamente para não interromper o uso offline
    }
  }

  async function selectHymn(hymnId: string): Promise<void> {
    if (!hymnsById.value.has(hymnId)) return;
    currentHymnId.value = hymnId;
    await setStoredLastHymnId(hymnId);
  }

  return {
    hymns,
    sortedHymns,
    hymnsById,
    currentHymnId,
    currentHymn,
    previousHymn,
    nextHymn,
    searchQuery,
    searchResults,
    localVersion,
    isReady,
    initHymns,
    selectHymn,
    syncWithFirestoreInBackground,
  };
});
