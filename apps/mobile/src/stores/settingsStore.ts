import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import {
  DEFAULT_USER_SETTINGS,
  getStoredUserSettings,
  setStoredUserSettings,
  type ThemeMode,
} from '@/services/preferences';

export const FONT_SCALE_MIN = 85;
export const FONT_SCALE_MAX = 145;
export const FONT_SCALE_STEP = 10;

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<ThemeMode>(DEFAULT_USER_SETTINGS.theme);
  const fontScale = ref<number>(DEFAULT_USER_SETTINGS.fontScale);
  const keepAwake = ref<boolean>(DEFAULT_USER_SETTINGS.keepAwake);
  const isLoaded = ref(false);

  let mediaQueryList: MediaQueryList | null = null;

  function resolveEffectiveTheme(mode: ThemeMode): 'light' | 'dark' | 'sepia' {
    if (mode === 'system') {
      if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return 'light';
    }
    return mode;
  }

  function applyThemeAndTypography(): void {
    if (typeof document === 'undefined') return;
    const effectiveTheme = resolveEffectiveTheme(theme.value);
    const root = document.documentElement;

    root.setAttribute('data-theme', effectiveTheme);
    root.style.setProperty('--hymn-font-scale', String(fontScale.value / 100));
  }

  async function initSettings(): Promise<void> {
    const stored = await getStoredUserSettings();
    theme.value = stored.theme;
    fontScale.value = stored.fontScale;
    keepAwake.value = stored.keepAwake;
    isLoaded.value = true;

    applyThemeAndTypography();

    if (typeof window !== 'undefined' && window.matchMedia && !mediaQueryList) {
      mediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQueryList.addEventListener('change', () => {
        if (theme.value === 'system') {
          applyThemeAndTypography();
        }
      });
    }
  }

  function setTheme(newTheme: ThemeMode): void {
    theme.value = newTheme;
  }

  function increaseFontScale(): void {
    fontScale.value = Math.min(FONT_SCALE_MAX, fontScale.value + FONT_SCALE_STEP);
  }

  function decreaseFontScale(): void {
    fontScale.value = Math.max(FONT_SCALE_MIN, fontScale.value - FONT_SCALE_STEP);
  }

  function resetFontScale(): void {
    fontScale.value = 100;
  }

  function setKeepAwake(enabled: boolean): void {
    keepAwake.value = enabled;
  }

  watch([theme, fontScale, keepAwake], async () => {
    applyThemeAndTypography();
    if (!isLoaded.value) return;
    await setStoredUserSettings({
      theme: theme.value,
      fontScale: fontScale.value,
      keepAwake: keepAwake.value,
    });
  });

  return {
    theme,
    fontScale,
    keepAwake,
    isLoaded,
    initSettings,
    setTheme,
    increaseFontScale,
    decreaseFontScale,
    resetFontScale,
    setKeepAwake,
  };
});
