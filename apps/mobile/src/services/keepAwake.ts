import { KeepAwake } from '@capacitor-community/keep-awake';

/**
 * Ativa ou desativa o bloqueio de tela durante a leitura do hino.
 * Possui fallback silencioso caso a API Screen Wake Lock não esteja disponível no navegador.
 */
export async function updateKeepAwakeState(shouldKeepAwake: boolean): Promise<void> {
  try {
    const { isSupported } = await KeepAwake.isSupported();
    if (!isSupported) return;

    if (shouldKeepAwake) {
      await KeepAwake.keepAwake();
    } else {
      await KeepAwake.allowSleep();
    }
  } catch {
    // Ignora silenciosamente em ambientes onde WakeLock não é suportado
  }
}
