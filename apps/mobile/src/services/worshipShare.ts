import { Capacitor } from '@capacitor/core';
import { copyTextToClipboard } from '@/services/shareHymn';

const SEED_VERSION = 0x01;
export const WEB_SHARE_BASE_URL = 'https://hinario-idc.web.app/';
export const APP_DEEP_LINK_BASE_URL = 'hinarioidc://culto';

/**
 * Calcula um checksum CRC-16 (CCITT-FALSE) de 16 bits para validar
 * offline se a seed não foi corrompida ou truncada.
 */
function computeCrc16(bytes: Uint8Array): number {
  let crc = 0xffff;
  for (let i = 0; i < bytes.length; i++) {
    crc ^= (bytes[i]! << 8) & 0xffff;
    for (let bit = 0; bit < 8; bit++) {
      if ((crc & 0x8000) !== 0) {
        crc = ((crc << 1) ^ 0x1021) & 0xffff;
      } else {
        crc = (crc << 1) & 0xffff;
      }
    }
  }
  return crc & 0xffff;
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]!);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function base64UrlToBytes(base64Url: string): Uint8Array | null {
  try {
    const cleaned = base64Url.trim().replace(/-/g, '+').replace(/_/g, '/');
    if (!cleaned || /[^A-Za-z0-9+/=]/.test(cleaned)) {
      return null;
    }
    const padLen = (4 - (cleaned.length % 4)) % 4;
    const padded = cleaned + '='.repeat(padLen);
    const binary = atob(padded);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      out[i] = binary.charCodeAt(i);
    }
    return out;
  } catch {
    return null;
  }
}

/**
 * Codifica a lista ordenada de números dos hinos em uma seed compacta Base64URL
 * com verificação de integridade CRC-16 embutida.
 *
 * Estrutura binária:
 * - Byte 0: versão do protocolo (0x01)
 * - Byte 1: quantidade de hinos N (1..100)
 * - Bytes 2..(2 + 2*N - 1): números dos hinos em Uint16 Big-Endian
 * - Últimos 2 bytes: CRC-16 sobre todo o payload anterior
 */
export function encodeWorshipSeed(hymnNumbers: number[]): string {
  const validNumbers = hymnNumbers
    .map((n) => Math.trunc(n))
    .filter((n) => n > 0 && n <= 65535)
    .slice(0, 100);

  const count = validNumbers.length;
  const payloadLength = 2 + count * 2;
  const buffer = new Uint8Array(payloadLength + 2);

  buffer[0] = SEED_VERSION;
  buffer[1] = count;

  for (let i = 0; i < count; i++) {
    const num = validNumbers[i]!;
    buffer[2 + i * 2] = (num >> 8) & 0xff;
    buffer[2 + i * 2 + 1] = num & 0xff;
  }

  const crc = computeCrc16(buffer.subarray(0, payloadLength));
  buffer[payloadLength] = (crc >> 8) & 0xff;
  buffer[payloadLength + 1] = crc & 0xff;

  return bytesToBase64Url(buffer);
}

/**
 * Decodifica e verifica offline uma seed de culto.
 * Retorna a lista ordenada de números dos hinos se a seed for íntegra, ou `null` se inválida.
 */
export function decodeWorshipSeed(seed: string): number[] | null {
  const bytes = base64UrlToBytes(seed);
  if (!bytes || bytes.length < 6) {
    return null;
  }

  const version = bytes[0];
  const count = bytes[1];
  if (version !== SEED_VERSION || !count || count < 1 || count > 100) {
    return null;
  }

  const expectedPayloadLength = 2 + count * 2;
  if (bytes.length !== expectedPayloadLength + 2) {
    return null;
  }

  const expectedCrc = computeCrc16(bytes.subarray(0, expectedPayloadLength));
  const actualCrc = ((bytes[expectedPayloadLength]! << 8) | bytes[expectedPayloadLength + 1]!) & 0xffff;

  if (expectedCrc !== actualCrc) {
    return null;
  }

  const numbers: number[] = [];
  const seen = new Set<number>();
  for (let i = 0; i < count; i++) {
    const num = ((bytes[2 + i * 2]! << 8) | bytes[2 + i * 2 + 1]!) & 0xffff;
    if (num <= 0) return null;
    if (!seen.has(num)) {
      seen.add(num);
      numbers.push(num);
    }
  }

  return numbers.length > 0 ? numbers : null;
}

/**
 * Gera o link de compartilhamento de acordo com o ambiente de execução:
 * - No aplicativo nativo (Capacitor): gera o deep link `hinarioidc://culto?c=<seed>` para abrir o app.
 * - No navegador web: gera o link `https://hinario-idc.web.app/?c=<seed>`.
 */
export function buildWorshipShareUrl(seed: string): string {
  const encoded = encodeURIComponent(seed);
  if (Capacitor.isNativePlatform()) {
    return `${APP_DEEP_LINK_BASE_URL}?c=${encoded}`;
  }
  return `${WEB_SHARE_BASE_URL}?c=${encoded}`;
}

export function buildWorshipShareMessage(hymnNumbers: number[]): {
  seed: string;
  url: string;
  text: string;
} {
  const seed = encodeWorshipSeed(hymnNumbers);
  const url = buildWorshipShareUrl(seed);
  const text = `Acompanhe os hinos do culto no Hinário IDC: ${url}`;
  return { seed, url, text };
}

/**
 * Extrai o parâmetro `c` (ou `culto`) de uma URL completa ou query string.
 */
export function extractWorshipSeedFromUrl(rawUrlOrSearch: string): string | null {
  if (!rawUrlOrSearch) return null;
  try {
    if (rawUrlOrSearch.startsWith('?')) {
      const params = new URLSearchParams(rawUrlOrSearch);
      return params.get('c') || params.get('culto');
    }
    const parsed = new URL(rawUrlOrSearch);
    return parsed.searchParams.get('c') || parsed.searchParams.get('culto');
  } catch {
    const match = rawUrlOrSearch.match(/[?&](?:c|culto)=([^&#]+)/);
    return match?.[1] ? decodeURIComponent(match[1]) : null;
  }
}

/**
 * Copia apenas o link do culto para a área de transferência.
 */
export async function copyWorshipLink(hymnNumbers: number[]): Promise<boolean> {
  const { url } = buildWorshipShareMessage(hymnNumbers);
  try {
    await copyTextToClipboard(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Compartilha o link do culto usando o menu nativo do dispositivo (quando disponível)
 * ou copia para a área de transferência.
 */
export async function shareOrCopyWorshipService(
  hymnNumbers: number[]
): Promise<'shared' | 'copied' | 'cancelled'> {
  const { text } = buildWorshipShareMessage(hymnNumbers);

  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    try {
      await navigator.share({
        title: 'Culto — Hinário IDC',
        text,
      });
      return 'shared';
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return 'cancelled';
      }
    }
  }

  try {
    await copyTextToClipboard(text);
    return 'copied';
  } catch {
    return 'cancelled';
  }
}
