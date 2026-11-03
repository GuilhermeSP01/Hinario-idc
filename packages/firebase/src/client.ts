import { getApps, initializeApp, type FirebaseApp } from 'firebase/app';
import { getFirestore, type Firestore } from 'firebase/firestore';

export interface FirebaseEnvConfig {
  apiKey?: string;
  authDomain?: string;
  projectId?: string;
  storageBucket?: string;
  messagingSenderId?: string;
  appId?: string;
}

let cachedFirestore: Firestore | null = null;

/**
 * Verifica se as credenciais mínimas do Firebase foram configuradas.
 */
export function isFirebaseConfigured(config: FirebaseEnvConfig): boolean {
  return Boolean(
    config.apiKey &&
      config.apiKey.trim() !== '' &&
      !config.apiKey.includes('YOUR_') &&
      config.projectId &&
      config.projectId.trim() !== '' &&
      config.appId &&
      config.appId.trim() !== ''
  );
}

/**
 * Inicializa o cliente Firestore de forma segura.
 * Caso as variáveis de ambiente não estejam preenchidas, retorna `null`
 * permitindo que o aplicativo opere normalmente com o armazenamento local.
 */
export function getOrInitFirestore(config: FirebaseEnvConfig): Firestore | null {
  if (!isFirebaseConfigured(config)) {
    return null;
  }

  if (cachedFirestore) {
    return cachedFirestore;
  }

  try {
    const existingApps = getApps();
    const app: FirebaseApp =
      existingApps.length > 0
        ? existingApps[0]!
        : initializeApp({
            apiKey: config.apiKey,
            authDomain: config.authDomain,
            projectId: config.projectId,
            storageBucket: config.storageBucket,
            messagingSenderId: config.messagingSenderId,
            appId: config.appId,
          });

    cachedFirestore = getFirestore(app);
    return cachedFirestore;
  } catch {
    return null;
  }
}
