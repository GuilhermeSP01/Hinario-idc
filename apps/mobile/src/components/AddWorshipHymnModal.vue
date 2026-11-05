<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Check, Plus, Search, X } from 'lucide-vue-next';
import { useHymnsStore } from '@/stores/hymnsStore';
import { useWorshipStore } from '@/stores/worshipStore';

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const hymnsStore = useHymnsStore();
const worshipStore = useWorshipStore();

const query = ref('');

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      query.value = '';
    }
  }
);

const results = computed(() => hymnsStore.searchCustom(query.value));

function onSearchInput(event: Event) {
  query.value = (event.target as HTMLInputElement).value;
}

function clearSearch() {
  query.value = '';
}
</script>

<template>
  <Teleport to="body">
    <Transition name="share-modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex flex-col justify-end sm:items-center sm:justify-center"
        role="dialog"
        aria-modal="true"
        aria-label="Adicionar hinos ao culto"
      >
        <!-- Backdrop -->
        <div
          class="fixed inset-0 bg-black/60 backdrop-blur-xs"
          @click="emit('close')"
        />

        <!-- Sheet / Modal -->
        <div
          class="relative z-10 flex max-h-[88dvh] w-full max-w-xl flex-col overflow-hidden rounded-t-3xl border-t sm:rounded-3xl sm:border shadow-2xl"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
        >
          <!-- Cabeçalho Fixo com Busca -->
          <div
            class="shrink-0 border-b px-4 pt-4 pb-3"
            style="border-color: var(--border-subtle)"
          >
            <div class="mb-3 flex items-center justify-between">
              <div>
                <h2 class="text-base font-bold" style="color: var(--text-primary)">
                  Adicionar ao Culto
                </h2>
                <p class="text-xs" style="color: var(--text-muted)">
                  Toque nos hinos na ordem em que serão louvados
                </p>
              </div>
              <button
                type="button"
                @click="emit('close')"
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

            <!-- Campo de Busca -->
            <div
              class="flex items-center gap-2.5 rounded-xl border px-3.5 py-2 transition-colors"
              style="background-color: var(--bg-primary); border-color: var(--border-subtle)"
            >
              <Search :size="17" class="shrink-0" style="color: var(--text-muted)" />
              <input
                :value="query"
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
                v-if="query"
                type="button"
                @click="clearSearch"
                class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full cursor-pointer"
                style="background-color: var(--bg-elevated); color: var(--text-secondary)"
                aria-label="Limpar busca"
              >
                <X :size="12" />
              </button>
            </div>
          </div>

          <!-- Lista de Hinos -->
          <div class="flex-1 overflow-y-auto px-4 py-3">
            <div v-if="results.length > 0" class="flex flex-col gap-2">
              <button
                v-for="item in results"
                :key="item.hymn.id"
                type="button"
                @click="worshipStore.toggleHymn(item.hymn.id)"
                class="flex w-full items-center justify-between gap-3 rounded-xl border px-3.5 py-2.5 text-left transition-all active:scale-[0.99] cursor-pointer"
                :style="{
                  backgroundColor: worshipStore.hasHymn(item.hymn.id)
                    ? 'color-mix(in srgb, var(--accent-soft) 45%, var(--bg-primary))'
                    : 'var(--bg-primary)',
                  borderColor: worshipStore.hasHymn(item.hymn.id)
                    ? 'var(--accent-primary)'
                    : 'var(--border-subtle)',
                }"
              >
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <span
                      class="inline-flex shrink-0 items-center justify-center rounded-md px-2 py-0.5 text-xs font-bold"
                      style="
                        background-color: var(--accent-soft);
                        color: var(--accent-primary);
                      "
                    >
                      #{{ item.hymn.number }}
                    </span>
                    <span
                      class="truncate text-sm font-semibold"
                      style="color: var(--text-primary)"
                    >
                      {{ item.hymn.title }}
                    </span>
                  </div>
                  <p
                    v-if="item.matchedSnippet"
                    class="mt-1 truncate text-xs italic"
                    style="color: var(--text-muted)"
                  >
                    "{{ item.matchedSnippet }}"
                  </p>
                </div>

                <!-- Indicador de Adicionado / Posição no Culto -->
                <div
                  v-if="worshipStore.hasHymn(item.hymn.id)"
                  class="flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold"
                  style="background-color: var(--accent-primary); color: #ffffff"
                >
                  <span>{{ worshipStore.getOrderNumber(item.hymn.id) }}º</span>
                  <Check :size="13" :stroke-width="3" />
                </div>
                <div
                  v-else
                  class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border"
                  style="
                    background-color: var(--bg-surface);
                    border-color: var(--border-subtle);
                    color: var(--text-muted);
                  "
                >
                  <Plus :size="15" />
                </div>
              </button>
            </div>

            <div
              v-else
              class="py-10 text-center text-sm"
              style="color: var(--text-muted)"
            >
              Nenhum hino encontrado para "{{ query }}"
            </div>
          </div>

          <!-- Rodapé Fixo -->
          <div
            class="shrink-0 border-t px-4 pt-3"
            style="
              background-color: var(--bg-surface);
              border-color: var(--border-subtle);
              padding-bottom: calc(0.875rem + env(safe-area-inset-bottom, 0px));
            "
          >
            <button
              type="button"
              @click="emit('close')"
              class="flex w-full items-center justify-center rounded-xl py-2.5 text-xs font-bold transition-opacity active:opacity-90 cursor-pointer"
              style="background-color: var(--accent-primary); color: #ffffff"
            >
              Concluir
              <template v-if="worshipStore.worshipIds.length > 0">
                ({{ worshipStore.worshipIds.length }}
                {{ worshipStore.worshipIds.length === 1 ? 'hino' : 'hinos' }})
              </template>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
