import type { Hymn } from '../models/hymn';

/**
 * Remove acentos/diacríticos, pontuação irrelevante e normaliza para minúsculas.
 */
export function normalizeText(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Concatena todas as linhas das estrofes e coros de um hino em uma única string para indexação.
 */
export function flattenHymnLyrics(hymn: Hymn): string {
  return hymn.sections.flatMap((section) => section.lines).join(' \n ');
}

/**
 * Encontra a primeira linha da letra do hino que contém os termos pesquisados,
 * útil para exibir o trecho encontrado nos resultados de busca.
 */
export function extractMatchSnippet(hymn: Hymn, rawQuery: string): string | undefined {
  const normalizedQuery = normalizeText(rawQuery);
  if (!normalizedQuery) return undefined;

  const tokens = normalizedQuery.split(' ').filter((t) => t.length >= 2);
  if (tokens.length === 0) return undefined;

  for (const section of hymn.sections) {
    for (const line of section.lines) {
      const normalizedLine = normalizeText(line);
      if (
        normalizedLine.includes(normalizedQuery) ||
        tokens.every((token) => normalizedLine.includes(token))
      ) {
        return line.trim();
      }
    }
  }

  for (const section of hymn.sections) {
    for (const line of section.lines) {
      const normalizedLine = normalizeText(line);
      if (tokens.some((token) => normalizedLine.includes(token))) {
        return line.trim();
      }
    }
  }

  return undefined;
}
