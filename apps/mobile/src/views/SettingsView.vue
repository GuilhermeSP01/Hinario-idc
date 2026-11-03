<script setup lang="ts">
import { BookOpen, Monitor, Moon, RotateCcw, Sun } from 'lucide-vue-next';
import {
  FONT_SCALE_MAX,
  FONT_SCALE_MIN,
  useSettingsStore,
} from '@/stores/settingsStore';
import type { ThemeMode } from '@/services/preferences';

const settingsStore = useSettingsStore();

const themeOptions: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Claro', icon: Sun },
  { value: 'dark', label: 'Escuro', icon: Moon },
  { value: 'sepia', label: 'Sépia', icon: BookOpen },
  { value: 'system', label: 'Sistema', icon: Monitor },
];
</script>

<template>
  <div class="mx-auto max-w-xl px-4 pb-28 pt-4">
    <header class="mb-5">
      <h1 class="text-xl font-bold tracking-tight" style="color: var(--text-primary)">
        Configurações
      </h1>
      <p class="mt-0.5 text-xs" style="color: var(--text-muted)">
        Personalize a aparência e a leitura dos hinos
      </p>
    </header>

    <div class="flex flex-col gap-5">
      <!-- Tema de Cores -->
      <section
        class="rounded-2xl border p-4"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <h2 class="mb-3 text-sm font-semibold" style="color: var(--text-primary)">
          Tema de Aparência
        </h2>

        <div class="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <button
            v-for="opt in themeOptions"
            :key="opt.value"
            type="button"
            @click="settingsStore.setTheme(opt.value)"
            class="flex flex-col items-center justify-center gap-1.5 rounded-xl border py-3 px-2 text-xs font-semibold transition-all cursor-pointer"
            :style="{
              backgroundColor:
                settingsStore.theme === opt.value
                  ? 'var(--accent-soft)'
                  : 'var(--bg-primary)',
              borderColor:
                settingsStore.theme === opt.value
                  ? 'var(--accent-primary)'
                  : 'var(--border-subtle)',
              color:
                settingsStore.theme === opt.value
                  ? 'var(--accent-primary)'
                  : 'var(--text-secondary)',
            }"
          >
            <component :is="opt.icon" :size="18" />
            <span>{{ opt.label }}</span>
          </button>
        </div>
      </section>

      <!-- Tamanho da Fonte -->
      <section
        class="rounded-2xl border p-4"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold" style="color: var(--text-primary)">
            Tamanho da Fonte
          </h2>
          <span class="text-xs font-bold" style="color: var(--accent-primary)">
            {{ settingsStore.fontScale }}%
          </span>
        </div>

        <!-- Controle de Tamanho A- / A+ -->
        <div class="flex items-center gap-2.5">
          <button
            type="button"
            :disabled="settingsStore.fontScale <= FONT_SCALE_MIN"
            @click="settingsStore.decreaseFontScale"
            class="flex h-11 flex-1 items-center justify-center rounded-xl border text-sm font-bold transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="
              background-color: var(--bg-primary);
              border-color: var(--border-subtle);
              color: var(--text-primary);
            "
          >
            A−
          </button>

          <button
            type="button"
            @click="settingsStore.resetFontScale"
            class="flex h-11 items-center justify-center gap-1.5 rounded-xl border px-3.5 text-xs font-medium cursor-pointer"
            style="
              background-color: var(--bg-primary);
              border-color: var(--border-subtle);
              color: var(--text-secondary);
            "
            title="Restaurar tamanho padrão (100%)"
          >
            <RotateCcw :size="14" />
            <span>Padrão</span>
          </button>

          <button
            type="button"
            :disabled="settingsStore.fontScale >= FONT_SCALE_MAX"
            @click="settingsStore.increaseFontScale"
            class="flex h-11 flex-1 items-center justify-center rounded-xl border text-base font-bold transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style="
              background-color: var(--bg-primary);
              border-color: var(--border-subtle);
              color: var(--text-primary);
            "
          >
            A+
          </button>
        </div>

        <!-- Pré-visualização ao vivo (estrofe normal + coro em negrito) -->
        <div
          class="mt-4 rounded-xl border p-3.5"
          style="background-color: var(--bg-primary); border-color: var(--border-subtle)"
        >
          <span
            class="mb-1.5 block text-[10px] font-bold uppercase tracking-wider"
            style="color: var(--text-muted)"
          >
            Pré-visualização
          </span>
          <div class="hymn-reading-typography flex flex-col gap-2">
            <div class="hymn-verse-section">
              <p class="m-0">Deus prometeu com certeza</p>
              <p class="m-0">Chuvas de graça mandar;</p>
            </div>
            <div class="hymn-chorus-section">
              <p class="m-0">Chuvas de graça, chuvas pedimos, Senhor;</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Comportamento de Tela (Switch moderno) -->
      <section
        class="rounded-2xl border p-4"
        style="background-color: var(--bg-surface); border-color: var(--border-subtle)"
      >
        <div class="flex items-center justify-between gap-4">
          <span class="text-sm font-semibold" style="color: var(--text-primary)">
            Manter tela acesa na leitura
          </span>

          <button
            type="button"
            role="switch"
            :aria-checked="settingsStore.keepAwake"
            @click="settingsStore.setKeepAwake(!settingsStore.keepAwake)"
            class="relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors duration-200 cursor-pointer"
            :style="{
              backgroundColor: settingsStore.keepAwake
                ? 'var(--accent-primary)'
                : 'var(--bg-elevated)',
              border: settingsStore.keepAwake ? 'none' : '1px solid var(--border-subtle)',
            }"
          >
            <span
              class="inline-block h-5 w-5 transform rounded-full bg-white shadow-xs transition-transform duration-200"
              :class="settingsStore.keepAwake ? 'translate-x-6' : 'translate-x-1'"
            />
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
