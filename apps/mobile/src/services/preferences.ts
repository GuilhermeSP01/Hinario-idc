import { log, reportError } from '@hinario/observability';
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
  WORSHIP_IDS: 'hinario_idc_worship_ids',
  WORSHIP_EDITED_BY_USER: 'hinario_idc_worship_edited_by_user',
  LAST_HYMN_ID: 'hinario_idc_last_hymn_id',
  USER_SETTINGS: 'hinario_idc_user_settings',
} as const;

export const DEFAULT_USER_SETTINGS: UserSettings = {
  theme: 'sepia',
  fontScale: 100,
  keepAwake: true,
};

export async function getStoredLocalVersion(): Promise<number> {
  const { value } = await readPreference({ key: KEYS.LOCAL_VERSION });
  if (!value) return 0;
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export async function setStoredLocalVersion(version: number): Promise<void> {
  await writePreference({ key: KEYS.LOCAL_VERSION, value: String(version) });
}

export async function getStoredFavoriteIds(): Promise<string[]> {
  const { value } = await readPreference({ key: KEYS.FAVORITE_IDS });
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch (error) {
    reportError('storage.invalid_json', error);
    return [];
  }
}

export async function setStoredFavoriteIds(ids: string[]): Promise<void> {
  await writePreference({ key: KEYS.FAVORITE_IDS, value: JSON.stringify(ids) });
}

export async function getStoredWorshipIds(): Promise<string[]> {
  const { value } = await readPreference({ key: KEYS.WORSHIP_IDS });
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch (error) {
    reportError('storage.invalid_json', error);
    return [];
  }
}

export async function setStoredWorshipIds(ids: string[]): Promise<void> {
  await writePreference({ key: KEYS.WORSHIP_IDS, value: JSON.stringify(ids) });
}

export async function getStoredWorshipEditedByUser(): Promise<boolean> {
  const { value } = await readPreference({ key: KEYS.WORSHIP_EDITED_BY_USER });
  return value === 'true';
}

export async function setStoredWorshipEditedByUser(edited: boolean): Promise<void> {
  await writePreference({
    key: KEYS.WORSHIP_EDITED_BY_USER,
    value: edited ? 'true' : 'false',
  });
}

export async function getStoredLastHymnId(): Promise<string | null> {
  const { value } = await readPreference({ key: KEYS.LAST_HYMN_ID });
  return value || null;
}

export async function setStoredLastHymnId(id: string): Promise<void> {
  await writePreference({ key: KEYS.LAST_HYMN_ID, value: id });
}

export async function getStoredUserSettings(): Promise<UserSettings> {
  const { value } = await readPreference({ key: KEYS.USER_SETTINGS });
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
  } catch (error) {
    reportError('storage.invalid_json', error);
    return { ...DEFAULT_USER_SETTINGS };
  }
}

export async function setStoredUserSettings(settings: UserSettings): Promise<void> {
  await writePreference({ key: KEYS.USER_SETTINGS, value: JSON.stringify(settings) });
}

async function readPreference(options: { key: string }): Promise<{ value: string | null }> {
  const start = performance.now();
  try {
    const result = await Preferences.get(options);
    log('storage.read.succeeded', { durationMs: performance.now() - start });
    return result;
  } catch (error) {
    reportError('storage.read.failed', error, { durationMs: performance.now() - start });
    throw error;
  }
}

async function writePreference(options: { key: string; value: string }): Promise<void> {
  const start = performance.now();
  try {
    await Preferences.set(options);
    log('storage.write.succeeded', { durationMs: performance.now() - start });
  } catch (error) {
    reportError('storage.write.failed', error, { durationMs: performance.now() - start });
    throw error;
  }
}
