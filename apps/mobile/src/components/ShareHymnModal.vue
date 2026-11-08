<script setup lang="ts">
import { reportError } from '@hinario/observability';
import { computed, onMounted, ref, watch } from 'vue';
import {
  AlignLeft,
  BookOpen,
  Check,
  Copy,
  Download,
  Image as ImageIcon,
  Moon,
  Share2,
  Sun,
  X,
} from 'lucide-vue-next';
import type { Hymn } from '@hinario/core';
import HinarioOutlineIcon from '@/components/HinarioOutlineIcon.vue';
import {
  buildShareRenderItems,
  copyTextToClipboard,
  downloadImageBlob,
  formatShareText,
  renderHymnCardBlob,
  shareOrCopyText,
  shareOrDownloadImageBlob,
  type ShareCardTheme,
} from '@/services/shareHymn';

const props = defineProps<{
  isOpen: boolean;
  hymn: Hymn;
  selectedIndices: number[];
}>();

const emit = defineEmits<{
  close: [];
  shared: [];
}>();

const activeTab = ref<'image' | 'text'>('image');
const includeTitle = ref<boolean>(true);
const includeFooter = ref<boolean>(true);
const cardTheme = ref<ShareCardTheme>('sepia');
const isBusy = ref<boolean>(false);
const copiedFeedback = ref<boolean>(false);

function detectCurrentAppTheme(): ShareCardTheme {
  if (typeof document === 'undefined') return 'sepia';
  const attr = document.documentElement.getAttribute('data-theme');
  if (attr === 'dark' || attr === 'sepia' || attr === 'light') {
    return attr;
  }
  return 'sepia';
}

onMounted(() => {
  cardTheme.value = detectCurrentAppTheme();
});

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      cardTheme.value = detectCurrentAppTheme();
      copiedFeedback.value = false;
    }
  }
);

const renderItems = computed(() =>
  buildShareRenderItems(props.hymn.sections, props.selectedIndices)
);

const formattedText = computed(() =>
  formatShareText({
    hymn: props.hymn,
    selectedIndices: props.selectedIndices,
    includeTitle: includeTitle.value,
    includeFooter: includeFooter.value,
    cardTheme: cardTheme.value,
  })
);

const cardPreviewStyles = computed(() => {
  if (cardTheme.value === 'dark') {
    return {
      outerBg: '#0c0c0c',
      cardBg: '#1a1a1a',
      cardBorder: '#2c2c2c',
      titleColor: '#ededed',
      accentColor: '#c89d66',
      verseColor: '#cccccc',
      chorusColor: '#ffffff',
      mutedColor: '#8a8a8a',
    };
  }
  if (cardTheme.value === 'sepia') {
    return {
      outerBg: '#e8dec6',
      cardBg: '#fbf5e6',
      cardBorder: '#dfd1b2',
      titleColor: '#3b2f20',
      accentColor: '#9a5b13',
      verseColor: '#463726',
      chorusColor: '#1f160c',
      mutedColor: '#7d6850',
    };
  }
  return {
    outerBg: '#f2ece1',
    cardBg: '#ffffff',
    cardBorder: '#e4ddd0',
    titleColor: '#1f1b16',
    accentColor: '#8c5218',
    verseColor: '#2e2820',
    chorusColor: '#120f0b',
    mutedColor: '#7d7264',
  };
});

const themeChoices: { value: ShareCardTheme; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Claro', icon: Sun },
  { value: 'dark', label: 'Escuro', icon: Moon },
  { value: 'sepia', label: 'Sépia', icon: BookOpen },
];

function getFilename(): string {
  return `hinario-idc-hino-${props.hymn.number}.png`;
}

async function handleShareImage() {
  if (isBusy.value) return;
  isBusy.value = true;
  try {
    const blob = await renderHymnCardBlob({
      hymn: props.hymn,
      selectedIndices: props.selectedIndices,
      includeTitle: includeTitle.value,
      includeFooter: includeFooter.value,
      cardTheme: cardTheme.value,
    });
    await shareOrDownloadImageBlob(
      blob,
      getFilename(),
      `${props.hymn.number}. ${props.hymn.title} — Hinário IDC`
    );
    emit('shared');
  } catch (err) {
    // Caso o usuário cancele o share nativo (AbortError), apenas permanece ou fecha sem erro
    if ((err as Error)?.name !== 'AbortError') {
      reportError('share.failed', err, { kind: 'image' });
    }
  } finally {
    isBusy.value = false;
  }
}

async function handleDownloadImage() {
  if (isBusy.value) return;
  isBusy.value = true;
  try {
    const blob = await renderHymnCardBlob({
      hymn: props.hymn,
      selectedIndices: props.selectedIndices,
      includeTitle: includeTitle.value,
      includeFooter: includeFooter.value,
      cardTheme: cardTheme.value,
    });
    downloadImageBlob(blob, getFilename());
  } finally {
    isBusy.value = false;
  }
}

async function handleShareText() {
  if (isBusy.value) return;
  isBusy.value = true;
  try {
    const result = await shareOrCopyText(
      formattedText.value,
      `${props.hymn.number}. ${props.hymn.title} — Hinário IDC`
    );
    if (result === 'copied') {
      copiedFeedback.value = true;
      setTimeout(() => {
        copiedFeedback.value = false;
      }, 2000);
    } else {
      emit('shared');
    }
  } catch (err) {
    if ((err as Error)?.name !== 'AbortError') {
      reportError('share.failed', err, { kind: 'text' });
    }
  } finally {
    isBusy.value = false;
  }
}

async function handleCopyText() {
  await copyTextToClipboard(formattedText.value);
  copiedFeedback.value = true;
  setTimeout(() => {
    copiedFeedback.value = false;
  }, 2000);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="share-modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-0 sm:p-4"
      >
        <!-- Backdrop escuro com blur -->
        <div
          class="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
          @click="emit('close')"
        />

        <!-- Painel do Modal / Bottom Sheet -->
        <div
          class="relative z-10 flex max-h-[90dvh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl sm:rounded-3xl border shadow-2xl safe-bottom"
          style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
        >
          <!-- Cabeçalho do Modal -->
          <div
            class="flex items-center justify-between border-b px-5 py-3.5"
            style="border-color: var(--border-subtle)"
          >
            <h2 class="text-base font-bold" style="color: var(--text-primary)">
              Compartilhar Trecho
            </h2>
            <button
              type="button"
              @click="emit('close')"
              class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer"
              style="background-color: var(--bg-elevated); color: var(--text-secondary)"
              aria-label="Fechar"
            >
              <X :size="16" />
            </button>
          </div>

          <!-- Corpo Rolável (Seletor Imagem/Texto + Pré-visualização + Opções) -->
          <div class="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
            <!-- Seletor de Abas: Imagem vs Texto -->
            <div
              class="grid grid-cols-2 gap-1.5 rounded-xl p-1"
              style="background-color: var(--bg-primary)"
            >
              <button
                type="button"
                @click="activeTab = 'image'"
                class="flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all cursor-pointer"
                :style="{
                  backgroundColor:
                    activeTab === 'image' ? 'var(--bg-surface)' : 'transparent',
                  color:
                    activeTab === 'image'
                      ? 'var(--accent-primary)'
                      : 'var(--text-secondary)',
                }"
              >
                <ImageIcon :size="15" />
                <span>Imagem</span>
              </button>

              <button
                type="button"
                @click="activeTab = 'text'"
                class="flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition-all cursor-pointer"
                :style="{
                  backgroundColor:
                    activeTab === 'text' ? 'var(--bg-surface)' : 'transparent',
                  color:
                    activeTab === 'text'
                      ? 'var(--accent-primary)'
                      : 'var(--text-secondary)',
                }"
              >
                <AlignLeft :size="15" />
                <span>Texto</span>
              </button>
            </div>

            <!-- Pré-visualização da Imagem -->
            <div
              v-if="activeTab === 'image'"
              class="rounded-2xl p-3.5 transition-colors"
              :style="{ backgroundColor: cardPreviewStyles.outerBg }"
            >
              <div
                class="rounded-xl border p-5 transition-colors"
                :style="{
                  backgroundColor: cardPreviewStyles.cardBg,
                  borderColor: cardPreviewStyles.cardBorder,
                }"
              >
                <!-- Título no Card -->
                <div
                  v-if="includeTitle"
                  class="mb-3.5 border-b pb-3"
                  :style="{ borderColor: cardPreviewStyles.cardBorder }"
                >
                  <h3
                    class="text-base font-bold leading-snug"
                    :style="{ color: cardPreviewStyles.titleColor }"
                  >
                    <span :style="{ color: cardPreviewStyles.accentColor }">
                      {{ hymn.number }}.
                    </span>
                    {{ ' ' + hymn.title }}
                  </h3>
                </div>

                <!-- Blocos do Hino e Indicadores de Corte ("•••") -->
                <div
                  class="flex flex-col gap-3.5"
                  style="font-family: var(--font-reading); font-size: 1.05rem; line-height: 1.55rem"
                >
                  <template v-for="(item, idx) in renderItems" :key="idx">
                    <div
                      v-if="item.kind === 'gap'"
                      class="py-0.5 text-center text-xs font-bold tracking-widest"
                      :style="{ color: cardPreviewStyles.mutedColor }"
                    >
                      • • •
                    </div>
                    <div
                      v-else
                      :style="{
                        color:
                          item.section.type === 'chorus'
                            ? cardPreviewStyles.chorusColor
                            : cardPreviewStyles.verseColor,
                        fontWeight: item.section.type === 'chorus' ? 700 : 400,
                      }"
                    >
                      <p
                        v-for="(line, lIdx) in item.section.lines"
                        :key="lIdx"
                        class="m-0"
                      >
                        {{ line }}
                      </p>
                    </div>
                  </template>
                </div>

                <!-- Rodapé Discreto com Ícone Outline -->
                <div
                  v-if="includeFooter"
                  class="mt-5 flex items-center justify-center gap-1.5 pt-1"
                  :style="{ color: cardPreviewStyles.mutedColor }"
                >
                  <HinarioOutlineIcon :size="15" />
                  <span class="text-[11px] font-semibold tracking-wide">
                    Hinário IDC
                  </span>
                </div>
              </div>
            </div>

            <!-- Pré-visualização do Texto Puro -->
            <div
              v-else
              class="rounded-2xl border p-4"
              style="
                background-color: var(--bg-primary);
                border-color: var(--border-subtle);
              "
            >
              <pre
                class="m-0 whitespace-pre-wrap text-sm leading-relaxed font-sans select-text"
                style="color: var(--text-primary)"
              >{{ formattedText }}</pre>
            </div>

            <!-- Opções de Personalização -->
            <div
              class="flex flex-col gap-3 rounded-2xl border p-3.5"
              style="
                background-color: var(--bg-primary);
                border-color: var(--border-subtle);
              "
            >
              <!-- Seletor de Tema do Card (apenas na aba Imagem) -->
              <div v-if="activeTab === 'image'" class="pb-2 border-b" style="border-color: var(--border-subtle)">
                <span
                  class="mb-2 block text-xs font-semibold"
                  style="color: var(--text-secondary)"
                >
                  Tema do card
                </span>
                <div class="grid grid-cols-3 gap-2">
                  <button
                    v-for="t in themeChoices"
                    :key="t.value"
                    type="button"
                    @click="cardTheme = t.value"
                    class="flex items-center justify-center gap-1.5 rounded-lg border py-2 px-2 text-xs font-semibold transition-all cursor-pointer"
                    :style="{
                      backgroundColor:
                        cardTheme === t.value
                          ? 'var(--accent-soft)'
                          : 'var(--bg-surface)',
                      borderColor:
                        cardTheme === t.value
                          ? 'var(--accent-primary)'
                          : 'var(--border-subtle)',
                      color:
                        cardTheme === t.value
                          ? 'var(--accent-primary)'
                          : 'var(--text-secondary)',
                    }"
                  >
                    <component :is="t.icon" :size="14" />
                    <span>{{ t.label }}</span>
                  </button>
                </div>
              </div>

              <!-- Switch: Incluir número e título -->
              <div class="flex items-center justify-between gap-3">
                <span class="text-xs font-semibold" style="color: var(--text-primary)">
                  Incluir número e título do hino
                </span>
                <button
                  type="button"
                  role="switch"
                  :aria-checked="includeTitle"
                  @click="includeTitle = !includeTitle"
                  class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 cursor-pointer"
                  :style="{
                    backgroundColor: includeTitle
                      ? 'var(--accent-primary)'
                      : 'var(--bg-elevated)',
                    border: includeTitle ? 'none' : '1px solid var(--border-subtle)',
                  }"
                >
                  <span
                    class="inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition-transform duration-200"
                    :class="includeTitle ? 'translate-x-5.5' : 'translate-x-1'"
                  />
                </button>
              </div>

              <!-- Switch: Incluir assinatura Hinário IDC -->
              <div class="flex items-center justify-between gap-3">
                <span class="text-xs font-semibold" style="color: var(--text-primary)">
                  Incluir assinatura "Hinário IDC"
                </span>
                <button
                  type="button"
                  role="switch"
                  :aria-checked="includeFooter"
                  @click="includeFooter = !includeFooter"
                  class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 cursor-pointer"
                  :style="{
                    backgroundColor: includeFooter
                      ? 'var(--accent-primary)'
                      : 'var(--bg-elevated)',
                    border: includeFooter ? 'none' : '1px solid var(--border-subtle)',
                  }"
                >
                  <span
                    class="inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition-transform duration-200"
                    :class="includeFooter ? 'translate-x-5.5' : 'translate-x-1'"
                  />
                </button>
              </div>
            </div>
          </div>

          <!-- Rodapé de Ações do Modal -->
          <div
            class="grid grid-cols-2 gap-3 border-t px-5 py-3.5"
            style="border-color: var(--border-subtle)"
          >
            <template v-if="activeTab === 'image'">
              <button
                type="button"
                :disabled="isBusy"
                @click="handleDownloadImage"
                class="flex items-center justify-center gap-2 rounded-xl border py-3 px-4 text-xs font-bold transition-opacity disabled:opacity-50 cursor-pointer"
                style="
                  background-color: var(--bg-primary);
                  border-color: var(--border-subtle);
                  color: var(--text-primary);
                "
              >
                <Download :size="16" />
                <span>Baixar</span>
              </button>

              <button
                type="button"
                :disabled="isBusy"
                @click="handleShareImage"
                class="flex items-center justify-center gap-2 rounded-xl py-3 px-4 text-xs font-bold text-white transition-opacity disabled:opacity-50 cursor-pointer"
                style="background-color: var(--accent-primary)"
              >
                <Share2 :size="16" />
                <span>Compartilhar</span>
              </button>
            </template>

            <template v-else>
              <button
                type="button"
                :disabled="isBusy"
                @click="handleCopyText"
                class="flex items-center justify-center gap-2 rounded-xl border py-3 px-4 text-xs font-bold transition-opacity disabled:opacity-50 cursor-pointer"
                style="
                  background-color: var(--bg-primary);
                  border-color: var(--border-subtle);
                  color: var(--text-primary);
                "
              >
                <Check v-if="copiedFeedback" :size="16" style="color: #16a34a" />
                <Copy v-else :size="16" />
                <span>{{ copiedFeedback ? 'Copiado!' : 'Copiar' }}</span>
              </button>

              <button
                type="button"
                :disabled="isBusy"
                @click="handleShareText"
                class="flex items-center justify-center gap-2 rounded-xl py-3 px-4 text-xs font-bold text-white transition-opacity disabled:opacity-50 cursor-pointer"
                style="background-color: var(--accent-primary)"
              >
                <Share2 :size="16" />
                <span>Compartilhar</span>
              </button>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
