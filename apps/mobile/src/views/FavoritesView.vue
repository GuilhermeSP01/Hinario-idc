<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { GripVertical, Heart, ListOrdered, Plus, Trash2, X } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useFavoritesStore } from '@/stores/favoritesStore';
import { useWorshipStore } from '@/stores/worshipStore';
import HymnListItem from '@/components/HymnListItem.vue';
import AddWorshipHymnModal from '@/components/AddWorshipHymnModal.vue';

const router = useRouter();
const hymnsStore = useHymnsStore();
const favoritesStore = useFavoritesStore();
const worshipStore = useWorshipStore();

const isWorshipView = ref(false);
const isAddModalOpen = ref(false);

const favoriteHymns = computed(() =>
  hymnsStore.sortedHymns.filter((hymn) => favoritesStore.isFavorite(hymn.id))
);

const worshipHymns = computed(() => hymnsStore.worshipHymns);

function toggleWorshipView() {
  isWorshipView.value = !isWorshipView.value;
}

async function openFavoriteHymn(hymnId: string) {
  await hymnsStore.selectHymn(hymnId, 'all');
  await router.push('/hymn');
}

async function openWorshipHymn(hymnId: string) {
  if (draggingIndex.value !== null) return;
  await hymnsStore.selectHymn(hymnId, 'worship');
  await router.push('/hymn');
}

// Drag-and-drop via Pointer Events (compatível com toque mobile e mouse desktop)
const listContainerRef = ref<HTMLElement | null>(null);
const draggingIndex = ref<number | null>(null);

function onHandlePointerDown(index: number, event: PointerEvent) {
  const target = event.currentTarget as HTMLElement | null;
  if (target) {
    target.setPointerCapture(event.pointerId);
  }
  draggingIndex.value = index;
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
    <!-- Cabeçalho com botão de alternância para Organizar Culto -->
    <header class="mb-4 flex items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold tracking-tight" style="color: var(--text-primary)">
          {{ isWorshipView ? 'Organizar Culto' : 'Hinos Favoritos' }}
        </h1>
        <p v-if="isWorshipView" class="mt-0.5 text-xs" style="color: var(--text-muted)">
          Arraste pela alça lateral para definir a ordem dos louvores
        </p>
      </div>

      <!-- Botão circular estilo tela de hino para abrir/fechar Organizar Culto -->
      <button
        type="button"
        @click="toggleWorshipView"
        class="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border transition-all duration-200 active:scale-90 cursor-pointer"
        :style="{
          backgroundColor: isWorshipView ? 'var(--accent-soft)' : 'var(--bg-surface)',
          borderColor: isWorshipView ? 'var(--accent-primary)' : 'var(--border-subtle)',
          color: isWorshipView ? 'var(--accent-primary)' : 'var(--text-muted)',
        }"
        :aria-label="isWorshipView ? 'Voltar para Hinos Favoritos' : 'Organizar Culto'"
        :aria-pressed="isWorshipView"
        :title="isWorshipView ? 'Voltar para Hinos Favoritos' : 'Organizar Culto'"
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
    </header>

    <!-- MODO 1: TELA DE ORGANIZAR CULTO -->
    <template v-if="isWorshipView">
      <!-- Barra de ações do culto -->
      <div class="mb-3.5 flex items-center justify-between gap-2.5">
        <button
          type="button"
          @click="isAddModalOpen = true"
          class="flex flex-1 items-center justify-center gap-1.5 rounded-xl border py-2.5 px-3.5 text-xs font-bold transition-all active:scale-[0.99] cursor-pointer"
          style="
            background-color: var(--accent-soft);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
          "
        >
          <Plus :size="16" :stroke-width="2.5" />
          <span>Adicionar hino</span>
        </button>

        <button
          v-if="worshipHymns.length > 0"
          type="button"
          @click="worshipStore.clearWorship()"
          class="flex items-center justify-center gap-1.5 rounded-xl border py-2.5 px-3.5 text-xs font-semibold transition-colors active:scale-[0.98] cursor-pointer"
          style="
            background-color: var(--bg-surface);
            border-color: var(--border-subtle);
            color: var(--text-secondary);
          "
          title="Limpar lista do culto"
        >
          <Trash2 :size="15" />
          <span>Limpar</span>
        </button>
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

    <!-- MODO 2: TELA DE HINOS FAVORITOS -->
    <template v-else>
      <TransitionGroup
        v-if="favoriteHymns.length > 0"
        name="fav-list"
        tag="div"
        class="relative flex flex-col gap-2.5"
      >
        <HymnListItem
          v-for="hymn in favoriteHymns"
          :key="hymn.id"
          :hymn="hymn"
          :is-favorite="true"
          :is-current="hymnsStore.currentHymnId === hymn.id"
          @select="openFavoriteHymn"
          @toggle-favorite="favoritesStore.toggleFavorite"
        />
      </TransitionGroup>

      <div
        v-else
        class="mt-12 flex flex-col items-center justify-center rounded-2xl border p-8 text-center transition-all duration-300"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <div
          class="mb-3 flex h-12 w-12 items-center justify-center rounded-full"
          style="background-color: var(--bg-elevated); color: var(--text-muted)"
        >
          <Heart :size="22" />
        </div>
        <p class="text-base font-medium" style="color: var(--text-primary)">
          Nenhum hino favorito ainda
        </p>
        <p class="mt-1 text-xs" style="color: var(--text-muted)">
          Toque no ícone de coração em qualquer hino para acessá-lo rapidamente aqui.
        </p>
        <button
          type="button"
          @click="router.push('/')"
          class="mt-4 rounded-lg px-4 py-2 text-xs font-semibold cursor-pointer"
          style="background-color: var(--accent-soft); color: var(--accent-primary)"
        >
          Explorar hinário
        </button>
      </div>
    </template>

    <!-- Modal de busca e adição de hinos ao culto -->
    <AddWorshipHymnModal
      :is-open="isAddModalOpen"
      @close="isAddModalOpen = false"
    />
  </div>
</template>
