export type SectionType = 'verse' | 'chorus';

export interface HymnSection {
  /** Tipo do bloco: 'verse' (estrofe) ou 'chorus' (coro/refrão) */
  type: SectionType;
  /** Número da estrofe (1, 2, 3...), opcional para o coro */
  number?: number;
  /** Linhas/versos que compõem este bloco */
  lines: string[];
}

export interface Hymn {
  /** Identificador único do documento no Firestore e IndexedDB (ex: "001") */
  id: string;
  /** Número oficial do hino para ordenação e busca numérica (ex: 1) */
  number: number;
  /** Título oficial do hino */
  title: string;
  /** Lista ordenada de blocos (estrofes e coros na ordem em que são cantados) */
  sections: HymnSection[];
  /** Versão do hinário em que este hino foi criado ou atualizado */
  version: number;
  /** Indica se o hino foi removido em uma sincronização delta */
  deleted?: boolean;
}

export interface HinarioMetadata {
  /** Versão atual consolidada do hinário no Firestore */
  currentVersion: number;
  /** Data/hora ISO da última atualização */
  updatedAt: string;
}

export interface HymnSearchResult {
  hymn: Hymn;
  score: number;
  matchField: 'number' | 'title' | 'lyrics';
  /** Linha da letra onde o termo buscado foi encontrado (quando aplicável) */
  matchedSnippet?: string;
}
