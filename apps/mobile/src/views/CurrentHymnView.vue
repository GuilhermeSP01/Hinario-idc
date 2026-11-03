<script setup lang="ts">
import { onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue';
import { ChevronLeft, ChevronRight } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { updateKeepAwakeState } from '@/services/keepAwake';
import FavoriteButton from '@/components/FavoriteButton.vue';

const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();
const settingsStore = useSettingsStore();

const transitionName = ref<'hymn-slide-next' | 'hymn-slide-prev'>('hymn-slide-next');

watch(
  () => hymnsStore.currentHymn?.number,
  (newNum, oldNum) => {
    if (typeof newNum === 'number' && typeof oldNum === 'number' && newNum !== oldNum) {
      transitionName.value = newNum > oldNum ? 'hymn-slide-next' : 'hymn-slide-prev';
    }
  },
  { flush: 'sync' }
);

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
  <div class="mx-auto max-w-xl px-4 pb-28 pt-4 overflow-x-hidden">
    <Transition :name="transitionName" mode="out-in">
      <div v-if="hymnsStore.currentHymn" :key="hymnsStore.currentHymn.id">
        <!-- Cabeçalho do Hino: "X. Título" alinhado com o botão de favorito -->
        <header
          class="mb-6 flex items-center justify-between gap-4 border-b pb-4"
          style="border-color: var(--border-subtle)"
        >
          <h1
            class="text-xl sm:text-2xl font-bold leading-snug tracking-tight"
            style="color: var(--text-primary)"
          >
            <span style="color: var(--accent-primary)">{{ hymnsStore.currentHymn.number }}.</span>
            {{ ' ' + hymnsStore.currentHymn.title }}
          </h1>

          <FavoriteButton
            :is-favorite="favoritesStore.isFavorite(hymnsStore.currentHymn.id)"
            :size="20"
            variant="bordered"
            @toggle="favoritesStore.toggleFavorite(hymnsStore.currentHymn.id)"
          />
        </header>

        <!-- Corpo do Hino (Estrofes e Coro em negrito com contraste reforçado) -->
        <article class="hymn-reading-typography flex flex-col gap-6 select-text">
          <section
            v-for="(section, idx) in hymnsStore.currentHymn.sections"
            :key="idx"
            :class="section.type === 'chorus' ? 'hymn-chorus-section' : 'hymn-verse-section'"
          >
            <p v-for="(line, lineIdx) in section.lines" :key="lineIdx" class="m-0">
              {{ line }}
            </p>
          </section>
        </article>

        <!-- Navegação Anterior / Próximo -->
        <footer
          class="mt-10 grid grid-cols-2 gap-3 border-t pt-5"
          style="border-color: var(--border-subtle)"
        >
          <button
            type="button"
            :disabled="!hymnsStore.previousHymn"
            @click="goToPrevious"
            class="flex min-w-0 items-center gap-2 overflow-hidden rounded-xl border px-3.5 py-3 text-left transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
          >
            <ChevronLeft :size="18" class="shrink-0" style="color: var(--accent-primary)" />
            <div class="min-w-0 flex-1">
              <span class="block text-[11px] font-medium" style="color: var(--text-muted)">
                Anterior
              </span>
              <span
                class="block truncate text-xs font-semibold"
                style="color: var(--text-primary)"
              >
                {{
                  hymnsStore.previousHymn
                    ? `${hymnsStore.previousHymn.number}. ${hymnsStore.previousHymn.title}`
                    : 'Início do hinário'
                }}
              </span>
            </div>
          </button>

          <button
            type="button"
            :disabled="!hymnsStore.nextHymn"
            @click="goToNext"
            class="flex min-w-0 items-center justify-end gap-2 overflow-hidden rounded-xl border px-3.5 py-3 text-right transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
          >
            <div class="min-w-0 flex-1">
              <span class="block text-[11px] font-medium" style="color: var(--text-muted)">
                Próximo
              </span>
              <span
                class="block truncate text-xs font-semibold"
                style="color: var(--text-primary)"
              >
                {{
                  hymnsStore.nextHymn
                    ? `${hymnsStore.nextHymn.number}. ${hymnsStore.nextHymn.title}`
                    : 'Fim do hinário'
                }}
              </span>
            </div>
            <ChevronRight :size="18" class="shrink-0" style="color: var(--accent-primary)" />
          </button>
        </footer>
      </div>
    </Transition>
  </div>
</template>
