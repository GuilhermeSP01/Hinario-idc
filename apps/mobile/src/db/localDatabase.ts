import Dexie, { type Table } from 'dexie';
import type { Hymn } from '@hinario/core';

export interface SearchCacheRecord {
  /** Chave fixa ('main') */
  id: string;
  /** Versão do hinário correspondente ao índice serializado */
  version: number;
  /** Quantidade de hinos indexados no cache */
  hymnCount: number;
  /** Índice MiniSearch serializado em JSON */
  serializedIndex: string;
  /** Data/hora ISO em que o cache foi gerado */
  updatedAt: string;
}

export class HinarioLocalDB extends Dexie {
  public hymns!: Table<Hymn, string>;
  public searchCache!: Table<SearchCacheRecord, string>;

  constructor() {
    super('HinarioIdcDB');

    this.version(1).stores({
      hymns: 'id, number, version',
      searchCache: 'id, version',
    });
  }
}

export const localDb = new HinarioLocalDB();
