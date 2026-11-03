<script setup lang="ts">
import { onActivated, onDeactivated, onMounted, onUnmounted, watch } from 'vue';
import { ChevronLeft, ChevronRight, Heart } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { updateKeepAwakeState } from '@/services/keepAwake';

const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();
const settingsStore = useSettingsStore();

function syncWakeLock(active: boolean) {
  void updateKeepAwakeState(active && settingsStore.keepAwake);
}

onMounted(() => syncWakeLock(true));
onActivated(() => syncWakeLock(true));
onDeactivated(() => syncWakeLock(false));
onUnmounted(() => syncWakeLock(false));

watch(
  () => settingsStore.keepAwake,
  (enabled) => {
    void updateKeepAwakeState(enabled);
  }
);

async function goToPrevious() {
  if (!hymnsStore.previousHymn) return;
  await hymnsStore.selectHymn(hymnsStore.previousHymn.id);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function goToNext() {
  if (!hymnsStore.nextHymn) return;
  await hymnsStore.selectHymn(hymnsStore.nextHymn.id);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>

<template>
  <div class="mx-auto max-w-xl px-4 pb-28 pt-4">
    <template v-if="hymnsStore.currentHymn">
      <!-- Cabeçalho do Hino -->
      <header
        class="mb-6 flex items-start justify-between gap-4 border-b pb-4"
        style="border-color: var(--border-subtle)"
      >
        <div>
          <span
            class="inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider"
            style="background-color: var(--accent-soft); color: var(--accent-primary)"
          >
            Hino {{ hymnsStore.currentHymn.number }}
          </span>
          <h1
            class="mt-2 text-2xl font-bold leading-tight"
            style="color: var(--text-primary)"
          >
            {{ hymnsStore.currentHymn.title }}
          </h1>
        </div>

        <button
          type="button"
          @click="favoritesStore.toggleFavorite(hymnsStore.currentHymn.id)"
          class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border transition-colors cursor-pointer"
          :style="{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-subtle)',
            color: favoritesStore.isFavorite(hymnsStore.currentHymn.id)
              ? '#ef4444'
              : 'var(--text-muted)',
          }"
          :aria-label="
            favoritesStore.isFavorite(hymnsStore.currentHymn.id)
              ? 'Remover dos favoritos'
              : 'Adicionar aos favoritos'
          "
        >
          <Heart
            :size="22"
            :fill="favoritesStore.isFavorite(hymnsStore.currentHymn.id) ? '#ef4444' : 'none'"
          />
        </button>
      </header>

      <!-- Corpo do Hino (Estrofes e Coro tipados) -->
      <article class="hymn-reading-typography flex flex-col gap-6 select-text">
        <section
          v-for="(section, idx) in hymnsStore.currentHymn.sections"
          :key="idx"
          :class="[
            'transition-colors',
            section.type === 'chorus' ? 'rounded-xl border-l-4 py-3.5 pl-4 pr-3 italic' : '',
          ]"
          :style="
            section.type === 'chorus'
              ? {
                  backgroundColor: 'var(--bg-chorus)',
                  borderColor: 'var(--chorus-border)',
                }
              : {}
          "
        >
          <div
            v-if="section.type === 'chorus'"
            class="mb-1.5 text-xs font-bold uppercase tracking-wider not-italic"
            style="color: var(--accent-primary)"
          >
            Coro
          </div>
          <div
            v-else-if="section.number"
            class="mb-1 text-xs font-bold uppercase tracking-wider"
            style="color: var(--text-muted)"
          >
            Estrofe {{ section.number }}
          </div>

          <p
            v-for="(line, lineIdx) in section.lines"
            :key="lineIdx"
            class="m-0"
            style="color: var(--text-primary)"
          >
            {{ line }}
          </p>
        </section>
      </article>

      <!-- Navegação Anterior / Próximo -->
      <footer
        class="mt-10 flex items-center justify-between gap-3 border-t pt-5"
        style="border-color: var(--border-subtle)"
      >
        <button
          type="button"
          :disabled="!hymnsStore.previousHymn"
          @click="goToPrevious"
          class="flex flex-1 items-center gap-2 rounded-xl border px-3.5 py-3 text-left transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
        >
          <ChevronLeft :size="18" class="shrink-0" style="color: var(--accent-primary)" />
          <div class="min-w-0">
            <span class="block text-[11px] font-medium" style="color: var(--text-muted)">
              Anterior
            </span>
            <span
              class="block truncate text-xs font-semibold"
              style="color: var(--text-primary)"
            >
              {{
                hymnsStore.previousHymn
                  ? `#${hymnsStore.previousHymn.number} ${hymnsStore.previousHymn.title}`
                  : 'Início do hinário'
              }}
            </span>
          </div>
        </button>

        <button
          type="button"
          :disabled="!hymnsStore.nextHymn"
          @click="goToNext"
          class="flex flex-1 items-center justify-end gap-2 rounded-xl border px-3.5 py-3 text-right transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
        >
          <div class="min-w-0">
            <span class="block text-[11px] font-medium" style="color: var(--text-muted)">
              Próximo
            </span>
            <span
              class="block truncate text-xs font-semibold"
              style="color: var(--text-primary)"
            >
              {{
                hymnsStore.nextHymn
                  ? `#${hymnsStore.nextHymn.number} ${hymnsStore.nextHymn.title}`
                  : 'Fim do hinário'
              }}
            </span>
          </div>
          <ChevronRight :size="18" class="shrink-0" style="color: var(--accent-primary)" />
        </button>
      </footer>
    </template>
  </div>
</template>
