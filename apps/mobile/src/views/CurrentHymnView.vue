<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue';
import { Check, ChevronLeft, ChevronRight, Share2 } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { updateKeepAwakeState } from '@/services/keepAwake';
import FavoriteButton from '@/components/FavoriteButton.vue';
import ShareHymnModal from '@/components/ShareHymnModal.vue';

const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();
const settingsStore = useSettingsStore();

const scrollContainerRef = ref<HTMLElement | null>(null);
const transitionName = ref<'hymn-slide-next' | 'hymn-slide-prev'>('hymn-slide-next');

// Estado do modo de seleção para compartilhamento
const isSelectingBlocks = ref<boolean>(false);
const selectedBlockIndices = ref<number[]>([]);
const isShareModalOpen = ref<boolean>(false);

const selectedSet = computed(() => new Set(selectedBlockIndices.value));

const allBlocksSelected = computed(() => {
  const total = hymnsStore.currentHymn?.sections.length ?? 0;
  return total > 0 && selectedBlockIndices.value.length === total;
});

function exitSelectionMode() {
  isSelectingBlocks.value = false;
  selectedBlockIndices.value = [];
  isShareModalOpen.value = false;
}

function toggleSelectionMode() {
  if (isSelectingBlocks.value) {
    exitSelectionMode();
  } else {
    isSelectingBlocks.value = true;
    selectedBlockIndices.value = [];
  }
}

function toggleBlockSelection(index: number) {
  if (!isSelectingBlocks.value) return;
  if (selectedSet.value.has(index)) {
    selectedBlockIndices.value = selectedBlockIndices.value.filter((i) => i !== index);
  } else {
    selectedBlockIndices.value = [...selectedBlockIndices.value, index];
  }
}

function toggleSelectAllBlocks() {
  const total = hymnsStore.currentHymn?.sections.length ?? 0;
  if (total === 0) return;
  if (allBlocksSelected.value) {
    selectedBlockIndices.value = [];
  } else {
    selectedBlockIndices.value = Array.from({ length: total }, (_, idx) => idx);
  }
}

function openSharePreview() {
  if (selectedBlockIndices.value.length === 0) return;
  isShareModalOpen.value = true;
}

watch(
  () => [hymnsStore.currentHymnIndex, hymnsStore.currentHymn?.number] as const,
  ([newIdx, newNum], [oldIdx, oldNum]) => {
    if (
      typeof newIdx === 'number' &&
      typeof oldIdx === 'number' &&
      newIdx >= 0 &&
      oldIdx >= 0 &&
      newIdx !== oldIdx
    ) {
      transitionName.value = newIdx > oldIdx ? 'hymn-slide-next' : 'hymn-slide-prev';
      exitSelectionMode();
    } else if (typeof newNum === 'number' && typeof oldNum === 'number' && newNum !== oldNum) {
      transitionName.value = newNum > oldNum ? 'hymn-slide-next' : 'hymn-slide-prev';
      exitSelectionMode();
    }
  },
  { flush: 'sync' }
);

function syncWakeLock(active: boolean) {
  void updateKeepAwakeState(active && settingsStore.keepAwake);
}

onMounted(() => syncWakeLock(true));
onActivated(() => syncWakeLock(true));
onDeactivated(() => {
  syncWakeLock(false);
  exitSelectionMode();
});
onUnmounted(() => syncWakeLock(false));

watch(
  () => settingsStore.keepAwake,
  (enabled) => {
    void updateKeepAwakeState(enabled);
  }
);

function scrollToTop() {
  scrollContainerRef.value?.scrollTo({ top: 0, behavior: 'smooth' });
}

async function goToPrevious() {
  if (!hymnsStore.previousHymn) return;
  await hymnsStore.selectHymn(hymnsStore.previousHymn.id);
  scrollToTop();
}

async function goToNext() {
  if (!hymnsStore.nextHymn) return;
  await hymnsStore.selectHymn(hymnsStore.nextHymn.id);
  scrollToTop();
}
</script>

<template>
  <div
    class="mx-auto flex max-w-xl flex-col overflow-hidden"
    style="height: calc(100dvh - 4rem - env(safe-area-inset-bottom, 0px) - env(safe-area-inset-top, 0px))"
  >
    <template v-if="hymnsStore.currentHymn">
      <!-- Área rolável apenas para o conteúdo do hino -->
      <div
        ref="scrollContainerRef"
        class="flex-1 overflow-y-auto overflow-x-hidden px-4 pt-4 pb-6"
      >
        <Transition :name="transitionName" mode="out-in">
          <div :key="hymnsStore.currentHymn.id">
            <!-- Cabeçalho do Hino: "X. Título" alinhado com os botões de compartilhar e favorito -->
            <header
              class="mb-5 flex items-center justify-between gap-3 border-b pb-4"
              style="border-color: var(--border-subtle)"
            >
              <h1
                class="min-w-0 flex-1 text-xl sm:text-2xl font-bold leading-snug tracking-tight"
                style="color: var(--text-primary)"
              >
                <span style="color: var(--accent-primary)">
                  {{ hymnsStore.currentHymn.number }}.
                </span>
                {{ ' ' + hymnsStore.currentHymn.title }}
              </h1>

              <div class="flex shrink-0 items-center gap-2">
                <!-- Botão de Compartilhar (mesmo formato do botão de Favoritar) -->
                <button
                  type="button"
                  @click="toggleSelectionMode"
                  class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border transition-all duration-200 active:scale-90 cursor-pointer"
                  :style="{
                    backgroundColor: isSelectingBlocks
                      ? 'var(--accent-soft)'
                      : 'var(--bg-surface)',
                    borderColor: isSelectingBlocks
                      ? 'var(--accent-primary)'
                      : 'var(--border-subtle)',
                    color: isSelectingBlocks
                      ? 'var(--accent-primary)'
                      : 'var(--text-muted)',
                  }"
                  :aria-label="
                    isSelectingBlocks
                      ? 'Cancelar seleção de compartilhamento'
                      : 'Selecionar trechos para compartilhar'
                  "
                  :aria-pressed="isSelectingBlocks"
                >
                  <Share2 :size="19" />
                </button>

                <FavoriteButton
                  :is-favorite="favoritesStore.isFavorite(hymnsStore.currentHymn.id)"
                  :size="20"
                  variant="bordered"
                  @toggle="favoritesStore.toggleFavorite(hymnsStore.currentHymn.id)"
                />
              </div>
            </header>

            <!-- Corpo do Hino (Estrofes e Coro) -->
            <article
              class="hymn-reading-typography flex flex-col transition-all"
              :class="isSelectingBlocks ? 'gap-3 select-none' : 'gap-6 select-text'"
            >
              <section
                v-for="(section, idx) in hymnsStore.currentHymn.sections"
                :key="idx"
                :role="isSelectingBlocks ? 'button' : undefined"
                :tabindex="isSelectingBlocks ? 0 : undefined"
                @click="toggleBlockSelection(idx)"
                @keydown.enter.prevent="toggleBlockSelection(idx)"
                @keydown.space.prevent="toggleBlockSelection(idx)"
                :class="[
                  section.type === 'chorus' ? 'hymn-chorus-section' : 'hymn-verse-section',
                  isSelectingBlocks
                    ? 'relative rounded-xl border p-3.5 pr-10 transition-all duration-150 active:scale-[0.99] cursor-pointer'
                    : '',
                ]"
                :style="
                  isSelectingBlocks
                    ? {
                        backgroundColor: selectedSet.has(idx)
                          ? 'color-mix(in srgb, var(--accent-soft) 55%, var(--bg-surface))'
                          : 'var(--bg-surface)',
                        borderColor: selectedSet.has(idx)
                          ? 'var(--accent-primary)'
                          : 'var(--border-subtle)',
                      }
                    : {}
                "
              >
                <!-- Indicador de check no modo de seleção -->
                <div
                  v-if="isSelectingBlocks"
                  class="absolute top-3.5 right-3.5 flex h-5 w-5 items-center justify-center rounded-full border transition-colors"
                  :style="{
                    backgroundColor: selectedSet.has(idx)
                      ? 'var(--accent-primary)'
                      : 'transparent',
                    borderColor: selectedSet.has(idx)
                      ? 'var(--accent-primary)'
                      : 'var(--text-muted)',
                    color: '#ffffff',
                  }"
                >
                  <Check v-if="selectedSet.has(idx)" :size="13" :stroke-width="3" />
                </div>

                <p v-for="(line, lineIdx) in section.lines" :key="lineIdx" class="m-0">
                  {{ line }}
                </p>
              </section>
            </article>
          </div>
        </Transition>
      </div>

      <!-- Barra fixa inferior: alterna entre Controles de Seleção e Anterior/Próximo -->
      <footer
        class="shrink-0 border-t px-4 py-3 backdrop-blur-md"
        style="
          background-color: color-mix(in srgb, var(--bg-primary) 94%, transparent);
          border-color: var(--border-subtle);
        "
      >
        <!-- Modo de Seleção de Compartilhamento -->
        <div v-if="isSelectingBlocks" class="grid grid-cols-3 gap-2.5">
          <button
            type="button"
            @click="exitSelectionMode"
            class="flex h-11 items-center justify-center whitespace-nowrap rounded-xl border px-3 text-xs font-semibold cursor-pointer"
            style="
              background-color: var(--bg-surface);
              border-color: var(--border-subtle);
              color: var(--text-secondary);
            "
          >
            Cancelar
          </button>

          <button
            type="button"
            @click="toggleSelectAllBlocks"
            class="flex h-11 items-center justify-center whitespace-nowrap rounded-xl border px-3 text-xs font-semibold cursor-pointer"
            style="
              background-color: var(--bg-surface);
              border-color: var(--border-subtle);
              color: var(--text-primary);
            "
          >
            {{ allBlocksSelected ? 'Limpar' : 'Tudo' }}
          </button>

          <button
            type="button"
            :disabled="selectedBlockIndices.length === 0"
            @click="openSharePreview"
            class="flex h-11 items-center justify-center whitespace-nowrap rounded-xl px-3 text-xs font-bold text-white transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="background-color: var(--accent-primary)"
          >
            Continuar
          </button>
        </div>

        <!-- Modo Padrão: Navegação Anterior / Próximo -->
        <div v-else class="grid grid-cols-2 gap-3">
          <button
            type="button"
            :disabled="!hymnsStore.previousHymn"
            @click="goToPrevious"
            class="flex min-w-0 items-center gap-2 overflow-hidden rounded-xl border px-3.5 py-2.5 text-left transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
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
            class="flex min-w-0 items-center justify-end gap-2 overflow-hidden rounded-xl border px-3.5 py-2.5 text-right transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
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
        </div>
      </footer>

      <!-- Modal de Pré-visualização e Opções de Compartilhamento -->
      <ShareHymnModal
        :is-open="isShareModalOpen"
        :hymn="hymnsStore.currentHymn"
        :selected-indices="selectedBlockIndices"
        @close="isShareModalOpen = false"
        @shared="exitSelectionMode"
      />
    </template>
  </div>
</template>
