<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  Check,
  Copy,
  GripVertical,
  ListOrdered,
  Plus,
  Search,
  Share2,
  Trash2,
  X,
} from 'lucide-vue-next';
import type { Hymn } from '@hinario/core';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import { useWorshipStore } from '@/stores/worshipStore';
import {
  buildWorshipShareMessage,
  copyWorshipLink,
  shareOrCopyWorshipService,
} from '@/services/worshipShare';
import HymnListItem from '@/components/HymnListItem.vue';
import AddWorshipHymnModal from '@/components/AddWorshipHymnModal.vue';

const router = useRouter();
const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();
const worshipStore = useWorshipStore();

const isAddModalOpen = ref(false);
const isShareWorshipModalOpen = ref(false);
const copiedShareFeedback = ref(false);

const isWorshipView = computed({
  get: () => worshipStore.isWorshipViewOpen,
  set: (val: boolean) => {
    worshipStore.isWorshipViewOpen = val;
  },
});

const worshipHymns = computed(() => hymnsStore.worshipHymns);

const pendingImportHymns = computed<Hymn[]>(() => {
  if (!worshipStore.pendingImportedIds) return [];
  const list: Hymn[] = [];
  for (const id of worshipStore.pendingImportedIds) {
    const found = hymnsStore.hymnsById.get(id);
    if (found) list.push(found);
  }
  return list;
});

function toggleWorshipView() {
  isWorshipView.value = !isWorshipView.value;
}

async function openHymn(hymnId: string) {
  await hymnsStore.selectHymn(hymnId, 'all');
  await router.push('/hymn');
}

async function openWorshipHymn(hymnId: string) {
  if (draggingIndex.value !== null) return;
  await hymnsStore.selectHymn(hymnId, 'worship');
  await router.push('/hymn');
}

const worshipSharePreview = computed(() => {
  if (worshipHymns.value.length === 0) return null;
  const numbers = worshipHymns.value.map((h) => h.number);
  return buildWorshipShareMessage(numbers);
});

function openShareWorshipModal() {
  if (worshipHymns.value.length === 0) return;
  copiedShareFeedback.value = false;
  isShareWorshipModalOpen.value = true;
}

async function handleCopyWorshipLink() {
  if (worshipHymns.value.length === 0) return;
  const numbers = worshipHymns.value.map((h) => h.number);
  const ok = await copyWorshipLink(numbers);
  if (ok) {
    copiedShareFeedback.value = true;
    setTimeout(() => {
      copiedShareFeedback.value = false;
    }, 2200);
  }
}

async function handleShareWorship() {
  if (worshipHymns.value.length === 0) return;
  const numbers = worshipHymns.value.map((h) => h.number);
  const result = await shareOrCopyWorshipService(numbers);
  if (result === 'shared') {
    isShareWorshipModalOpen.value = false;
  } else if (result === 'copied') {
    copiedShareFeedback.value = true;
    setTimeout(() => {
      copiedShareFeedback.value = false;
    }, 2200);
  }
}

function clearSearch() {
  hymnsStore.searchQuery = '';
}

function onSearchInput(event: Event) {
  hymnsStore.searchQuery = (event.target as HTMLInputElement).value;
}

// Drag-and-drop via Pointer Events (compatível com toque mobile e mouse desktop)
const listContainerRef = ref<HTMLElement | null>(null);
const draggingIndex = ref<number | null>(null);

function onHandlePointerDown(index: number, event: PointerEvent) {
  worshipStore.dismissReorderToast();
  const target = event.currentTarget as HTMLElement | null;
  if (target) {
    target.setPointerCapture(event.pointerId);
  }
  draggingIndex.value = index;
}

function handleCloseAddModal() {
  isAddModalOpen.value = false;
  if (worshipStore.isReorderToastVisible) {
    worshipStore.showReorderHintToast(3800);
  }
}

function onHandlePointerMove(event: PointerEvent) {
  if (draggingIndex.value === null || !listContainerRef.value) return;

  const items = Array.from(
    listContainerRef.value.querySelectorAll<HTMLElement>('[data-worship-item]')
  );
  const clientY = event.clientY;

  for (let i = 0; i < items.length; i++) {
    if (i === draggingIndex.value) continue;
    const rect = items[i]!.getBoundingClientRect();
    const middleY = rect.top + rect.height / 2;

    if (
      (draggingIndex.value < i && clientY > middleY) ||
      (draggingIndex.value > i && clientY < middleY)
    ) {
      void worshipStore.moveHymn(draggingIndex.value, i);
      draggingIndex.value = i;
      break;
    }
  }
}

function onHandlePointerEnd(event: PointerEvent) {
  const target = event.currentTarget as HTMLElement | null;
  if (target && target.hasPointerCapture(event.pointerId)) {
    target.releasePointerCapture(event.pointerId);
  }
  draggingIndex.value = null;
}
</script>

<template>
  <div class="mx-auto max-w-xl px-4 pb-24 pt-4">
    <!-- Cabeçalho fixo com título, botão de Organizar Culto e barra de busca -->
    <header
      class="sticky top-0 z-20 -mx-4 px-4 pb-3 pt-2 backdrop-blur-md transition-colors"
      style="background-color: color-mix(in srgb, var(--bg-primary) 92%, transparent)"
    >
      <div class="flex items-center justify-between gap-3" :class="isWorshipView ? '' : 'mb-3'">
        <h1 class="text-xl font-bold tracking-tight" style="color: var(--text-primary)">
          {{ isWorshipView ? 'Organizar Culto' : 'Hinário IDC' }}
        </h1>

        <!-- Botão circular de acesso à Organização de Culto -->
        <button
          type="button"
          @click="toggleWorshipView"
          class="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border transition-all duration-200 active:scale-90 cursor-pointer"
          :style="{
            backgroundColor: isWorshipView ? 'var(--accent-soft)' : 'var(--bg-surface)',
            borderColor: isWorshipView ? 'var(--accent-primary)' : 'var(--border-subtle)',
            color: isWorshipView ? 'var(--accent-primary)' : 'var(--text-muted)',
          }"
          :aria-label="isWorshipView ? 'Voltar para lista de hinos' : 'Organizar Culto'"
          :aria-pressed="isWorshipView"
          :title="isWorshipView ? 'Voltar para lista de hinos' : 'Organizar Culto'"
        >
          <ListOrdered :size="19" />
          <Transition name="badge-pop" mode="out-in">
            <span
              v-if="!isWorshipView && worshipHymns.length > 0"
              :key="worshipHymns.length"
              class="pointer-events-none absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold leading-none"
              style="background-color: var(--accent-primary); color: #ffffff"
            >
              {{ worshipHymns.length }}
            </span>
          </Transition>
        </button>
      </div>

      <!-- Barra de busca (exibida apenas no modo padrão do Hinário) -->
      <div
        v-if="!isWorshipView"
        class="flex items-center gap-2.5 rounded-xl border px-3.5 py-2.5 shadow-2xs transition-colors"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <Search :size="18" class="shrink-0" style="color: var(--text-muted)" />
        <input
          :value="hymnsStore.searchQuery"
          @input="onSearchInput"
          type="text"
          inputmode="search"
          autocomplete="off"
          autocorrect="off"
          autocapitalize="off"
          spellcheck="false"
          placeholder="Buscar por número, título ou trecho..."
          class="w-full bg-transparent text-sm outline-none placeholder:opacity-65"
          style="color: var(--text-primary)"
        />
        <button
          v-if="hymnsStore.searchQuery"
          type="button"
          @click="clearSearch"
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full cursor-pointer"
          style="background-color: var(--bg-elevated); color: var(--text-secondary)"
          aria-label="Limpar busca"
        >
          <X :size="14" />
        </button>
      </div>
    </header>

    <!-- MODO 1: TELA DE ORGANIZAR CULTO -->
    <template v-if="isWorshipView">
      <div class="mt-1 mb-3.5 flex items-center justify-between gap-1.5">
        <button
          type="button"
          @click="isAddModalOpen = true"
          class="flex flex-1 items-center justify-center gap-1.5 rounded-xl border py-2.5 px-2.5 text-xs font-bold whitespace-nowrap transition-all active:scale-[0.99] cursor-pointer"
          style="
            background-color: var(--accent-soft);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
          "
        >
          <Plus :size="15" :stroke-width="2.5" class="shrink-0" />
          <span>Adicionar hino</span>
        </button>

        <template v-if="worshipHymns.length > 0">
          <button
            type="button"
            @click="openShareWorshipModal"
            class="flex shrink-0 items-center justify-center gap-1 rounded-xl border py-2.5 px-2.5 text-xs font-semibold whitespace-nowrap transition-colors active:scale-[0.98] cursor-pointer"
            style="
              background-color: var(--bg-surface);
              border-color: var(--border-subtle);
              color: var(--text-primary);
            "
            title="Compartilhar culto"
          >
            <Share2 :size="14" class="shrink-0" />
            <span>Compartilhar</span>
          </button>

          <button
            type="button"
            @click="worshipStore.clearWorship()"
            class="flex shrink-0 items-center justify-center gap-1 rounded-xl border py-2.5 px-2.5 text-xs font-semibold whitespace-nowrap transition-colors active:scale-[0.98] cursor-pointer"
            style="
              background-color: var(--bg-surface);
              border-color: var(--border-subtle);
              color: var(--text-secondary);
            "
            title="Limpar lista do culto"
          >
            <Trash2 :size="14" class="shrink-0" />
            <span>Limpar</span>
          </button>
        </template>
      </div>

      <!-- Lista ordenada de hinos do culto -->
      <div v-if="worshipHymns.length > 0" ref="listContainerRef">
        <TransitionGroup
          name="fav-list"
          tag="div"
          class="relative flex flex-col gap-2.5"
        >
          <div
            v-for="(hymn, index) in worshipHymns"
            :key="hymn.id"
            data-worship-item
            class="flex items-center gap-2 rounded-2xl border p-2.5 transition-all"
            :class="draggingIndex === index ? 'scale-[1.02] shadow-lg z-20' : ''"
            :style="{
              backgroundColor: 'var(--bg-surface)',
              borderColor:
                draggingIndex === index ||
                (hymnsStore.currentHymnId === hymn.id &&
                  hymnsStore.navigationContext === 'worship')
                  ? 'var(--accent-primary)'
                  : 'var(--border-subtle)',
            }"
          >
            <!-- Alça de arrastar (Drag Handle) -->
            <button
              type="button"
              class="flex h-10 w-8 shrink-0 items-center justify-center rounded-lg touch-none cursor-grab active:cursor-grabbing"
              style="color: var(--text-muted)"
              aria-label="Arrastar para reordenar"
              @pointerdown="onHandlePointerDown(index, $event)"
              @pointermove="onHandlePointerMove"
              @pointerup="onHandlePointerEnd"
              @pointercancel="onHandlePointerEnd"
            >
              <GripVertical :size="18" />
            </button>

            <!-- Conteúdo clicável do hino (abre no modo culto) -->
            <button
              type="button"
              @click="openWorshipHymn(hymn.id)"
              class="flex min-w-0 flex-1 items-center gap-2.5 py-1 text-left cursor-pointer"
            >
              <span
                class="flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full px-1.5 text-xs font-bold"
                style="
                  background-color: var(--accent-soft);
                  color: var(--accent-primary);
                "
              >
                {{ index + 1 }}º
              </span>

              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5">
                  <span
                    class="text-xs font-bold"
                    style="color: var(--accent-primary)"
                  >
                    #{{ hymn.number }}
                  </span>
                  <span
                    class="truncate text-sm font-semibold"
                    style="color: var(--text-primary)"
                  >
                    {{ hymn.title }}
                  </span>
                </div>
              </div>
            </button>

            <!-- Botão de remover do culto -->
            <button
              type="button"
              @click.stop="worshipStore.removeHymn(hymn.id)"
              class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors cursor-pointer"
              style="color: var(--text-muted)"
              aria-label="Remover hino do culto"
            >
              <X :size="16" />
            </button>
          </div>
        </TransitionGroup>
      </div>

      <!-- Estado vazio do Culto -->
      <div
        v-else
        class="mt-8 flex flex-col items-center justify-center rounded-2xl border p-8 text-center transition-all duration-300"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <div
          class="mb-3 flex h-12 w-12 items-center justify-center rounded-full"
          style="background-color: var(--bg-elevated); color: var(--text-muted)"
        >
          <ListOrdered :size="22" />
        </div>
        <p class="text-base font-medium" style="color: var(--text-primary)">
          Nenhum hino adicionado ao culto
        </p>
        <p class="mt-1 text-xs" style="color: var(--text-muted)">
          Adicione os hinos que serão louvados e arraste para organizá-los na ordem desejada.
        </p>
        <button
          type="button"
          @click="isAddModalOpen = true"
          class="mt-4 flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold cursor-pointer"
          style="background-color: var(--accent-soft); color: var(--accent-primary)"
        >
          <Plus :size="15" />
          <span>Adicionar hinos</span>
        </button>
      </div>
    </template>

    <!-- MODO 2: LISTA DE HINOS PADRÃO -->
    <template v-else>
      <div v-if="hymnsStore.searchResults.length > 0" class="mt-2 flex flex-col gap-2.5">
        <HymnListItem
          v-for="item in hymnsStore.searchResults"
          :key="item.hymn.id"
          :hymn="item.hymn"
          :matched-snippet="item.matchedSnippet"
          :is-favorite="favoritesStore.isFavorite(item.hymn.id)"
          :is-current="hymnsStore.currentHymnId === item.hymn.id"
          @select="openHymn"
          @toggle-favorite="favoritesStore.toggleFavorite"
        />
      </div>

      <div
        v-else
        class="mt-12 flex flex-col items-center justify-center rounded-2xl border p-8 text-center"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <p class="text-base font-medium" style="color: var(--text-primary)">
          Nenhum hino encontrado
        </p>
        <p class="mt-1 text-xs" style="color: var(--text-muted)">
          Tente buscar por outro número, título ou palavra da letra.
        </p>
        <button
          type="button"
          @click="clearSearch"
          class="mt-4 rounded-lg px-4 py-2 text-xs font-semibold cursor-pointer"
          style="background-color: var(--accent-soft); color: var(--accent-primary)"
        >
          Limpar filtro
        </button>
      </div>
    </template>

    <!-- Modal de busca e adição de hinos ao culto -->
    <AddWorshipHymnModal
      :is-open="isAddModalOpen"
      @close="handleCloseAddModal"
    />

    <!-- Toast sutil de dica de reordenação (exibida apenas 1 vez por sessão ao passar de 1 hino) -->
    <Teleport to="body">
      <Transition name="toast-pop">
        <div
          v-if="worshipStore.isReorderToastVisible && isWorshipView && !isAddModalOpen"
          @click="worshipStore.dismissReorderToast()"
          role="status"
          aria-live="polite"
          class="fixed left-4 right-4 z-40 mx-auto flex max-w-sm items-center gap-2.5 rounded-2xl border px-3.5 py-2.5 shadow-lg cursor-pointer"
          style="
            bottom: calc(4.75rem + env(safe-area-inset-bottom, 0px));
            background-color: var(--bg-surface);
            border-color: var(--accent-primary);
            color: var(--text-primary);
          "
        >
          <span
            class="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg"
            style="background-color: var(--accent-soft); color: var(--accent-primary)"
          >
            <GripVertical :size="15" />
          </span>
          <span class="text-xs font-medium leading-snug">
            Arraste pela alça lateral para definir a ordem dos hinos
          </span>
        </div>
      </Transition>
    </Teleport>

    <!-- Modal de compartilhamento do culto (escolher entre Copiar Link ou Compartilhar) -->
    <Teleport to="body">
      <Transition name="share-modal">
        <div
          v-if="isShareWorshipModalOpen && worshipSharePreview"
          class="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-label="Compartilhar culto"
        >
          <div
            class="fixed inset-0 bg-black/60 backdrop-blur-xs"
            @click="isShareWorshipModalOpen = false"
          />

          <div
            class="relative z-10 flex w-full max-w-md flex-col overflow-hidden rounded-t-3xl border-t px-5 pt-5 pb-7 sm:rounded-3xl sm:border sm:pb-5 shadow-2xl"
            style="
              background-color: var(--bg-surface);
              border-color: var(--border-subtle);
              padding-bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px));
            "
          >
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-base font-bold" style="color: var(--text-primary)">
                  Compartilhar Culto
                </h2>
                <p class="mt-0.5 text-xs" style="color: var(--text-muted)">
                  {{ worshipHymns.length }}
                  {{ worshipHymns.length === 1 ? 'hino selecionado' : 'hinos selecionados' }}
                </p>
              </div>
              <button
                type="button"
                @click="isShareWorshipModalOpen = false"
                class="flex h-8 w-8 items-center justify-center rounded-full border transition-colors cursor-pointer"
                style="
                  background-color: var(--bg-primary);
                  border-color: var(--border-subtle);
                  color: var(--text-secondary);
                "
                aria-label="Fechar"
              >
                <X :size="16" />
              </button>
            </div>

            <div
              class="my-3.5 rounded-xl border px-3.5 py-2.5 font-mono text-xs break-all select-all"
              style="
                background-color: var(--bg-primary);
                border-color: var(--border-subtle);
                color: var(--text-secondary);
              "
            >
              {{ worshipSharePreview.url }}
            </div>

            <div class="flex items-center gap-2.5">
              <button
                type="button"
                @click="handleCopyWorshipLink"
                class="flex flex-1 items-center justify-center gap-1.5 rounded-xl border py-2.5 px-3 text-xs font-semibold transition-colors cursor-pointer"
                :style="{
                  backgroundColor: copiedShareFeedback ? 'var(--accent-soft)' : 'var(--bg-primary)',
                  borderColor: copiedShareFeedback ? 'var(--accent-primary)' : 'var(--border-subtle)',
                  color: copiedShareFeedback ? 'var(--accent-primary)' : 'var(--text-primary)',
                }"
              >
                <Check v-if="copiedShareFeedback" :size="15" />
                <Copy v-else :size="15" />
                <span>{{ copiedShareFeedback ? 'Link copiado!' : 'Copiar link' }}</span>
              </button>

              <button
                type="button"
                @click="handleShareWorship"
                class="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2.5 px-3 text-xs font-bold transition-opacity active:opacity-90 cursor-pointer"
                style="background-color: var(--accent-primary); color: #ffffff"
              >
                <Share2 :size="15" />
                <span>Compartilhar</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Modal de confirmação ao abrir um link de culto quando já há um culto editado pelo usuário -->
    <Teleport to="body">
      <Transition name="share-modal">
        <div
          v-if="pendingImportHymns.length > 0"
          class="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-label="Confirmar importação de culto compartilhado"
        >
          <div
            class="fixed inset-0 bg-black/60 backdrop-blur-xs"
            @click="worshipStore.cancelPendingImport()"
          />

          <div
            class="relative z-10 flex max-h-[82dvh] w-full max-w-md flex-col overflow-hidden rounded-t-3xl border-t px-5 pt-5 pb-7 sm:rounded-3xl sm:border sm:pb-5 shadow-2xl"
            style="
              background-color: var(--bg-surface);
              border-color: var(--border-subtle);
              padding-bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px));
            "
          >
            <h2 class="text-base font-bold" style="color: var(--text-primary)">
              Substituir culto atual?
            </h2>
            <p class="mt-1 text-xs leading-relaxed" style="color: var(--text-secondary)">
              Você possui um culto organizado por você. Deseja substituí-lo pelo culto compartilhado abaixo?
            </p>

            <div
              class="my-3.5 max-h-56 overflow-y-auto rounded-2xl border p-3 space-y-2"
              style="background-color: var(--bg-primary); border-color: var(--border-subtle)"
            >
              <div
                v-for="(hymn, idx) in pendingImportHymns"
                :key="hymn.id"
                class="flex items-center gap-2 text-xs"
              >
                <span
                  class="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full px-1 font-bold"
                  style="background-color: var(--accent-soft); color: var(--accent-primary)"
                >
                  {{ idx + 1 }}º
                </span>
                <span class="font-bold" style="color: var(--accent-primary)">
                  #{{ hymn.number }}
                </span>
                <span class="truncate font-medium" style="color: var(--text-primary)">
                  {{ hymn.title }}
                </span>
              </div>
            </div>

            <div class="flex items-center gap-2.5">
              <button
                type="button"
                @click="worshipStore.cancelPendingImport()"
                class="flex-1 rounded-xl border py-2.5 text-xs font-semibold cursor-pointer"
                style="
                  background-color: var(--bg-primary);
                  border-color: var(--border-subtle);
                  color: var(--text-secondary);
                "
              >
                Manter atual
              </button>
              <button
                type="button"
                @click="worshipStore.confirmPendingImport()"
                class="flex-1 rounded-xl py-2.5 text-xs font-bold cursor-pointer"
                style="background-color: var(--accent-primary); color: #ffffff"
              >
                Substituir
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
