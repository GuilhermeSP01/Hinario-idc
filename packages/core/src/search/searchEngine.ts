import MiniSearch, { type Options as MiniSearchOptions } from 'minisearch';
import type { Hymn, HymnSearchResult } from '../models/hymn';
import { extractMatchSnippet, flattenHymnLyrics, normalizeText } from './normalize';

interface IndexedHymnDoc {
  id: string;
  numberStr: string;
  title: string;
  lyrics: string;
}

const MINISEARCH_OPTIONS: MiniSearchOptions<IndexedHymnDoc> = {
  idField: 'id',
  fields: ['numberStr', 'title', 'lyrics'],
  storeFields: ['id', 'numberStr'],
  processTerm: (term: string) => {
    const normalized = normalizeText(term);
    return normalized.length > 0 ? normalized : null;
  },
  searchOptions: {
    boost: {
      numberStr: 6,
      title: 3,
      lyrics: 1,
    },
    prefix: true,
    fuzzy: (term: string) => (term.length >= 5 ? 0.2 : false),
  },
};

/**
 * Motor de busca em memória otimizado para o Hinário IDC,
 * com suporte a serialização/deserialização JSON para cache no IndexedDB.
 */
export class HymnSearchEngine {
  private miniSearch: MiniSearch<IndexedHymnDoc>;

  constructor() {
    this.miniSearch = new MiniSearch<IndexedHymnDoc>(MINISEARCH_OPTIONS);
  }

  /**
   * Reconstrói o índice completo a partir da lista de hinos ativos.
   */
  public buildIndex(hymns: Hymn[]): void {
    this.miniSearch.removeAll();
    const docs: IndexedHymnDoc[] = hymns
      .filter((h) => !h.deleted)
      .map((h) => ({
        id: h.id,
        numberStr: `${h.number} ${String(h.number).padStart(3, '0')}`,
        title: h.title,
        lyrics: flattenHymnLyrics(h),
      }));

    this.miniSearch.addAll(docs);
  }

  /**
   * Serializa o índice atual para uma string JSON que pode ser salva no IndexedDB.
   */
  public serializeIndex(): string {
    return JSON.stringify(this.miniSearch.toJSON());
  }

  /**
   * Restaura o índice diretamente a partir de um JSON em cache, evitando re-indexação no startup.
   */
  public loadSerializedIndex(serializedJson: string): boolean {
    try {
      this.miniSearch = MiniSearch.loadJSON<IndexedHymnDoc>(serializedJson, MINISEARCH_OPTIONS);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Executa a busca combinando correspondência numérica prioritária, título e letra indexada.
   */
  public search(rawQuery: string, hymnsById: Map<string, Hymn>): HymnSearchResult[] {
    const trimmed = rawQuery.trim();
    if (!trimmed) {
      return Array.from(hymnsById.values())
        .filter((h) => !h.deleted)
        .sort((a, b) => a.number - b.number)
        .map((hymn) => ({
          hymn,
          score: 1,
          matchField: 'number',
        }));
    }

    const resultsMap = new Map<string, HymnSearchResult>();
    const normalizedQuery = normalizeText(trimmed);
    const isNumericQuery = /^\d+$/.test(trimmed);
    const numericValue = isNumericQuery ? parseInt(trimmed, 10) : null;

    // 1. Prioridade máxima para busca exata ou por prefixo de número
    if (numericValue !== null) {
      for (const hymn of hymnsById.values()) {
        if (hymn.deleted) continue;
        if (hymn.number === numericValue) {
          resultsMap.set(hymn.id, {
            hymn,
            score: 1000,
            matchField: 'number',
          });
        } else if (String(hymn.number).startsWith(String(numericValue))) {
          resultsMap.set(hymn.id, {
            hymn,
            score: 500 - hymn.number * 0.01,
            matchField: 'number',
          });
        }
      }
    }

    // 2. Busca no índice invertido MiniSearch
    const miniResults = this.miniSearch.search(trimmed);
    for (const item of miniResults) {
      if (resultsMap.has(item.id)) continue;
      const hymn = hymnsById.get(item.id);
      if (!hymn || hymn.deleted) continue;

      const normalizedTitle = normalizeText(hymn.title);
      const isTitleMatch = normalizedTitle.includes(normalizedQuery);
      const matchedSnippet = isTitleMatch ? undefined : extractMatchSnippet(hymn, trimmed);

      resultsMap.set(hymn.id, {
        hymn,
        score: item.score + (isTitleMatch ? 100 : 0),
        matchField: isTitleMatch ? 'title' : 'lyrics',
        matchedSnippet,
      });
    }

    // 3. Fallback de substring para trechos intermediários de palavras
    if (normalizedQuery.length >= 2) {
      for (const hymn of hymnsById.values()) {
        if (hymn.deleted || resultsMap.has(hymn.id)) continue;
        const normalizedTitle = normalizeText(hymn.title);
        if (normalizedTitle.includes(normalizedQuery)) {
          resultsMap.set(hymn.id, {
            hymn,
            score: 80,
            matchField: 'title',
          });
          continue;
        }
        const snippet = extractMatchSnippet(hymn, trimmed);
        if (snippet && normalizeText(snippet).includes(normalizedQuery)) {
          resultsMap.set(hymn.id, {
            hymn,
            score: 20,
            matchField: 'lyrics',
            matchedSnippet: snippet,
          });
        }
      }
    }

    return Array.from(resultsMap.values()).sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.hymn.number - b.hymn.number;
    });
  }
}
