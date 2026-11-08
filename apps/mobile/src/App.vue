<script setup lang="ts">
import { log, reportError, operationId, normalizeError } from '@hinario/observability';
import { onMounted } from 'vue';
import { RouterView, useRouter } from 'vue-router';
import { App as CapApp } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';
import BottomNav from '@/components/BottomNav.vue';
import { useSettingsStore } from '@/stores/settingsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import { useWorshipStore } from '@/stores/worshipStore';
import { useHymnsStore } from '@/stores/hymnsStore';
import { decodeWorshipSeed, extractWorshipSeedFromUrl } from '@/services/worshipShare';

const router = useRouter();
const settingsStore = useSettingsStore();
const favoritesStore = useFavoritesStore();
const worshipStore = useWorshipStore();
const hymnsStore = useHymnsStore();

async function processSharedUrlIfPresent(rawUrlOrSearch: string): Promise<void> {
  const seed = extractWorshipSeedFromUrl(rawUrlOrSearch);
  if (!seed) return;

  const numbers = decodeWorshipSeed(seed);
  if (!numbers || numbers.length === 0) return;

  const resolvedIds = hymnsStore.resolveHymnIdsByNumbers(numbers);
  if (resolvedIds.length === 0) return;

  await worshipStore.handleIncomingSharedWorship(resolvedIds);
  await router.replace({ path: '/', query: {} });
}

onMounted(async () => {
  const start = performance.now();
  const context = { operationId: operationId() };
  log('app.init.started', context);
  try {
    await Promise.all([
      settingsStore.initSettings(),
      favoritesStore.initFavorites(),
      worshipStore.initWorship(),
      hymnsStore.initHymns(),
    ]);

    if (typeof window !== 'undefined' && window.location.search) {
      await processSharedUrlIfPresent(window.location.search);
    }

    if (Capacitor.isNativePlatform()) {
      try {
        const launchUrl = await CapApp.getLaunchUrl();
        if (launchUrl?.url) {
          await processSharedUrlIfPresent(launchUrl.url);
        }
        await CapApp.addListener('appUrlOpen', (event) => {
          if (event.url) {
            void processSharedUrlIfPresent(event.url);
          }
        });
      } catch (error) {
        if (['UNIMPLEMENTED', 'UNAVAILABLE'].includes(normalizeError(error).errorCode)) {
          log('native.plugin.unavailable', { plugin: 'deep_link' });
        } else {
          reportError('native.plugin.failed', error, { plugin: 'deep_link' });
        }
        // Preserve fallback when a native feature cannot be initialized.
      }
    }
    log('app.init.succeeded', { ...context, durationMs: performance.now() - start });
  } catch (error) {
    reportError('app.init.failed', error, { ...context, durationMs: performance.now() - start });
    throw error;
  }
});
</script>

<template>
  <div class="min-h-dvh safe-top">
    <main v-if="hymnsStore.isReady">
      <RouterView v-slot="{ Component }">
        <KeepAlive>
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>

    <BottomNav />
  </div>
</template>
