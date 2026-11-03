<script setup lang="ts">
import { onMounted } from 'vue';
import { RouterView } from 'vue-router';
import BottomNav from '@/components/BottomNav.vue';
import { useSettingsStore } from '@/stores/settingsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import { useHymnsStore } from '@/stores/hymnsStore';

const settingsStore = useSettingsStore();
const favoritesStore = useFavoritesStore();
const hymnsStore = useHymnsStore();

onMounted(async () => {
  await Promise.all([
    settingsStore.initSettings(),
    favoritesStore.initFavorites(),
    hymnsStore.initHymns(),
  ]);
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
