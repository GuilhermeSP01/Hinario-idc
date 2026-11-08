import type { Hymn } from '@hinario/hymns-contracts';
export type { SectionType, HymnSection, Hymn, HinarioMetadata } from '@hinario/hymns-contracts';

export interface HymnSearchResult {
  hymn: Hymn;
  score: number;
  matchField: 'number' | 'title' | 'lyrics';
  /** Linha da letra onde o termo buscado foi encontrado (quando aplicável) */
  matchedSnippet?: string;
}
