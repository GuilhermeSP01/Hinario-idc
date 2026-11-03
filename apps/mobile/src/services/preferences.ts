import { Preferences } from '@capacitor/preferences';

export type ThemeMode = 'light' | 'dark' | 'sepia' | 'system';

export interface UserSettings {
  theme: ThemeMode;
  /** Escala percentual de fonte: 85 a 145 (padrão 100) */
  fontScale: number;
  keepAwake: boolean;
}

const KEYS = {
  LOCAL_VERSION: 'hinario_idc_local_version',
  FAVORITE_IDS: 'hinario_idc_favorite_ids',
  LAST_HYMN_ID: 'hinario_idc_last_hymn_id',
  USER_SETTINGS: 'hinario_idc_user_settings',
} as const;

export const DEFAULT_USER_SETTINGS: UserSettings = {
  theme: 'system',
  fontScale: 100,
  keepAwake: true,
};

export async function getStoredLocalVersion(): Promise<number> {
  const { value } = await Preferences.get({ key: KEYS.LOCAL_VERSION });
  if (!value) return 0;
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export async function setStoredLocalVersion(version: number): Promise<void> {
  await Preferences.set({ key: KEYS.LOCAL_VERSION, value: String(version) });
}

export async function getStoredFavoriteIds(): Promise<string[]> {
  const { value } = await Preferences.get({ key: KEYS.FAVORITE_IDS });
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

export async function setStoredFavoriteIds(ids: string[]): Promise<void> {
  await Preferences.set({ key: KEYS.FAVORITE_IDS, value: JSON.stringify(ids) });
}

export async function getStoredLastHymnId(): Promise<string | null> {
  const { value } = await Preferences.get({ key: KEYS.LAST_HYMN_ID });
  return value || null;
}

export async function setStoredLastHymnId(id: string): Promise<void> {
  await Preferences.set({ key: KEYS.LAST_HYMN_ID, value: id });
}

export async function getStoredUserSettings(): Promise<UserSettings> {
  const { value } = await Preferences.get({ key: KEYS.USER_SETTINGS });
  if (!value) return { ...DEFAULT_USER_SETTINGS };
  try {
    const parsed = JSON.parse(value) as Partial<UserSettings>;
    return {
      theme:
        parsed.theme === 'light' ||
        parsed.theme === 'dark' ||
        parsed.theme === 'sepia' ||
        parsed.theme === 'system'
          ? parsed.theme
          : DEFAULT_USER_SETTINGS.theme,
      fontScale:
        typeof parsed.fontScale === 'number' && parsed.fontScale >= 80 && parsed.fontScale <= 150
          ? parsed.fontScale
          : DEFAULT_USER_SETTINGS.fontScale,
      keepAwake:
        typeof parsed.keepAwake === 'boolean'
          ? parsed.keepAwake
          : DEFAULT_USER_SETTINGS.keepAwake,
    };
  } catch {
    return { ...DEFAULT_USER_SETTINGS };
  }
}

export async function setStoredUserSettings(settings: UserSettings): Promise<void> {
  await Preferences.set({ key: KEYS.USER_SETTINGS, value: JSON.stringify(settings) });
}
