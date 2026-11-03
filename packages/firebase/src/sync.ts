import {
  collection,
  doc,
  getDoc,
  getDocs,
  orderBy,
  query,
  where,
  type Firestore,
} from 'firebase/firestore';
import type { HinarioMetadata, Hymn, HymnSection } from '@hinario/core';

export const METADATA_COLLECTION = 'metadata';
export const VERSION_DOC_ID = 'version';
export const HYMNS_COLLECTION = 'hymns';

/**
 * Busca a versão atual do hinário no Firestore (`metadata/version`).
 * Consome apenas 1 leitura de documento no Firestore.
 */
export async function fetchRemoteMetadata(db: Firestore): Promise<HinarioMetadata | null> {
  const versionRef = doc(db, METADATA_COLLECTION, VERSION_DOC_ID);
  const snapshot = await getDoc(versionRef);

  if (!snapshot.exists()) {
    return null;
  }

  const data = snapshot.data();
  if (typeof data.currentVersion !== 'number') {
    return null;
  }

  return {
    currentVersion: data.currentVersion,
    updatedAt: typeof data.updatedAt === 'string' ? data.updatedAt : new Date().toISOString(),
  };
}

/**
 * Busca apenas os hinos criados ou alterados após `localVersion` (Delta Sync).
 */
export async function fetchHymnsDelta(db: Firestore, localVersion: number): Promise<Hymn[]> {
  const hymnsRef = collection(db, HYMNS_COLLECTION);
  const deltaQuery = query(
    hymnsRef,
    where('version', '>', localVersion),
    orderBy('version', 'asc')
  );

  const snapshot = await getDocs(deltaQuery);
  const updatedHymns: Hymn[] = [];

  snapshot.forEach((docSnap) => {
    const raw = docSnap.data();
    if (typeof raw.number !== 'number' || typeof raw.title !== 'string') {
      return;
    }

    const sections: HymnSection[] = Array.isArray(raw.sections)
      ? raw.sections.map((sec: Record<string, unknown>) => ({
          type: sec.type === 'chorus' ? 'chorus' : 'verse',
          number: typeof sec.number === 'number' ? sec.number : undefined,
          lines: Array.isArray(sec.lines) ? sec.lines.map(String) : [],
        }))
      : [];

    updatedHymns.push({
      id: docSnap.id,
      number: raw.number,
      title: raw.title,
      sections,
      version: typeof raw.version === 'number' ? raw.version : localVersion + 1,
      deleted: Boolean(raw.deleted),
    });
  });

  return updatedHymns;
}
