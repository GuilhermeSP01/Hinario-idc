import { log, reportError, normalizeError } from '@hinario/observability';
import { KeepAwake } from '@capacitor-community/keep-awake';

/**
 * Ativa ou desativa o bloqueio de tela durante a leitura do hino.
 * Possui fallback silencioso caso a API Screen Wake Lock não esteja disponível no navegador.
 */
export async function updateKeepAwakeState(shouldKeepAwake: boolean): Promise<void> {
  try {
    const { isSupported } = await KeepAwake.isSupported();
    if (!isSupported) {
      log('native.plugin.unavailable', { plugin: 'wake_lock' });
      return;
    }

    if (shouldKeepAwake) {
      await KeepAwake.keepAwake();
    } else {
      await KeepAwake.allowSleep();
    }
  } catch (error) {
    if (['UNIMPLEMENTED', 'UNAVAILABLE', 'NotAllowedError', 'AbortError'].includes(normalizeError(error).errorCode)) {
      log('native.plugin.unavailable', { plugin: 'wake_lock' });
    } else {
      reportError('native.plugin.failed', error, { plugin: 'wake_lock' });
    }
    // The optional feature never interrupts hymn reading.
  }
}
