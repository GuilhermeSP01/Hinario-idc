import type { Hymn, HymnSection } from '@hinario/core';

export type ShareCardTheme = 'light' | 'dark' | 'sepia';

export type ShareRenderItem =
  | { kind: 'section'; section: HymnSection; originalIndex: number }
  | { kind: 'gap' };

export interface ShareHymnOptions {
  hymn: Hymn;
  selectedIndices: number[];
  includeTitle: boolean;
  includeFooter: boolean;
  cardTheme: ShareCardTheme;
}

interface CardPalette {
  outerBg: string;
  cardBg: string;
  cardBorder: string;
  titleColor: string;
  accentColor: string;
  verseColor: string;
  chorusColor: string;
  mutedColor: string;
}

const PALETTES: Record<ShareCardTheme, CardPalette> = {
  light: {
    outerBg: '#f2ece1',
    cardBg: '#ffffff',
    cardBorder: '#e4ddd0',
    titleColor: '#1f1b16',
    accentColor: '#8c5218',
    verseColor: '#2e2820',
    chorusColor: '#120f0b',
    mutedColor: '#7d7264',
  },
  dark: {
    outerBg: '#0c0c0c',
    cardBg: '#1a1a1a',
    cardBorder: '#2c2c2c',
    titleColor: '#ededed',
    accentColor: '#c89d66',
    verseColor: '#cccccc',
    chorusColor: '#ffffff',
    mutedColor: '#8a8a8a',
  },
  sepia: {
    outerBg: '#e8dec6',
    cardBg: '#fbf5e6',
    cardBorder: '#dfd1b2',
    titleColor: '#3b2f20',
    accentColor: '#9a5b13',
    verseColor: '#463726',
    chorusColor: '#1f160c',
    mutedColor: '#7d6850',
  },
};

/**
 * Monta a lista ordenada de blocos selecionados e insere um marcador `gap`
 * apenas quando uma estrofe (`type === 'verse'`) foi pulada entre dois blocos selecionados.
 */
export function buildShareRenderItems(
  sections: HymnSection[],
  selectedIndices: number[]
): ShareRenderItem[] {
  const sorted = [...selectedIndices]
    .filter((idx) => idx >= 0 && idx < sections.length)
    .sort((a, b) => a - b);

  const items: ShareRenderItem[] = [];

  for (let i = 0; i < sorted.length; i++) {
    const currentIdx = sorted[i]!;
    if (i > 0) {
      const prevIdx = sorted[i - 1]!;
      let skippedVerse = false;
      for (let k = prevIdx + 1; k < currentIdx; k++) {
        if (sections[k]?.type === 'verse') {
          skippedVerse = true;
          break;
        }
      }
      if (skippedVerse) {
        items.push({ kind: 'gap' });
      }
    }

    const section = sections[currentIdx];
    if (section) {
      items.push({
        kind: 'section',
        section,
        originalIndex: currentIdx,
      });
    }
  }

  return items;
}

/**
 * Formata o texto puro para compartilhamento ou cópia.
 */
export function formatShareText(options: ShareHymnOptions): string {
  const { hymn, selectedIndices, includeTitle, includeFooter } = options;
  const items = buildShareRenderItems(hymn.sections, selectedIndices);
  const parts: string[] = [];

  if (includeTitle) {
    parts.push(`${hymn.number}. ${hymn.title}`);
  }

  const bodyBlocks: string[] = [];
  for (const item of items) {
    if (item.kind === 'gap') {
      bodyBlocks.push('[...]');
    } else {
      bodyBlocks.push(item.section.lines.join('\n'));
    }
  }

  if (bodyBlocks.length > 0) {
    parts.push(bodyBlocks.join('\n\n'));
  }

  if (includeFooter) {
    parts.push('— Hinário IDC');
  }

  return parts.join('\n\n');
}

function wrapCanvasLine(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string[] {
  const words = text.split(' ');
  const lines: string[] = [];
  let currentLine = '';

  for (const word of words) {
    const testLine = currentLine ? `${currentLine} ${word}` : word;
    if (ctx.measureText(testLine).width > maxWidth && currentLine) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      currentLine = testLine;
    }
  }
  if (currentLine) {
    lines.push(currentLine);
  }
  return lines.length > 0 ? lines : [''];
}

function drawOutlineLogoOnCanvas(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  color: string
) {
  ctx.save();
  const scale = size / 24;
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.85;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // Círculo da nota musical
  ctx.beginPath();
  ctx.arc(10.5, 6.5, 1.5, 0, Math.PI * 2);
  ctx.stroke();

  // Haste e bandeirola da nota
  ctx.beginPath();
  ctx.moveTo(12, 6.5);
  ctx.lineTo(12, 2.5);
  ctx.bezierCurveTo(13.6, 2.7, 14.8, 3.5, 15.2, 4.7);
  ctx.stroke();

  // Contorno do hinário aberto
  ctx.beginPath();
  ctx.moveTo(3, 10.2);
  ctx.bezierCurveTo(5.5, 9.9, 8.5, 10.5, 12, 12.3);
  ctx.bezierCurveTo(15.5, 10.5, 18.5, 9.9, 21, 10.2);
  ctx.lineTo(21, 19);
  ctx.bezierCurveTo(18.5, 18.7, 15.5, 19.3, 12, 21.1);
  ctx.bezierCurveTo(8.5, 19.3, 5.5, 18.7, 3, 19);
  ctx.closePath();
  ctx.stroke();

  // Lombada central
  ctx.beginPath();
  ctx.moveTo(12, 12.3);
  ctx.lineTo(12, 21.1);
  ctx.stroke();

  // Linhas internas sutis
  ctx.beginPath();
  ctx.moveTo(5.8, 13.5);
  ctx.bezierCurveTo(7.3, 13.4, 8.8, 13.7, 10, 14.3);
  ctx.moveTo(5.8, 16.2);
  ctx.bezierCurveTo(7.3, 16.1, 8.8, 16.4, 10, 17);
  ctx.moveTo(18.2, 13.5);
  ctx.bezierCurveTo(16.7, 13.4, 15.2, 13.7, 14, 14.3);
  ctx.moveTo(18.2, 16.2);
  ctx.bezierCurveTo(16.7, 16.1, 15.2, 16.4, 14, 17);
  ctx.stroke();

  ctx.restore();
}

/**
 * Gera uma imagem PNG de alta resolução (1080px de largura) com altura adaptável
 * contendo os blocos selecionados do hino, usando a fonte Crimson Pro.
 */
export async function renderHymnCardBlob(options: ShareHymnOptions): Promise<Blob> {
  if (typeof document !== 'undefined' && 'fonts' in document) {
    try {
      await document.fonts.ready;
    } catch {
      // Prossegue caso a API de fontes falhe
    }
  }

  const palette = PALETTES[options.cardTheme];
  const items = buildShareRenderItems(options.hymn.sections, options.selectedIndices);

  const canvasWidth = 1080;
  const outerPadding = 56;
  const cardX = outerPadding;
  const cardWidth = canvasWidth - outerPadding * 2;
  const cardInnerPaddingX = 72;
  const cardInnerPaddingY = 72;
  const contentMaxWidth = cardWidth - cardInnerPaddingX * 2;

  const titleFont = '700 44px "Inter", system-ui, -apple-system, sans-serif';
  const titleLineHeight = 58;

  const verseFont = '400 40px "Crimson Pro", Georgia, serif';
  const chorusFont = '700 40px "Crimson Pro", Georgia, serif';
  const lyricLineHeight = 62;
  const sectionSpacing = 44;
  const gapIndicatorHeight = 56;

  const footerFont = '600 26px "Inter", system-ui, -apple-system, sans-serif';

  // Canvas temporário para medição precisa de quebras de linha
  const measureCanvas = document.createElement('canvas');
  const mCtx = measureCanvas.getContext('2d')!;

  // 1. Medir título (se ativo)
  let titleLines: string[] = [];
  const fullTitleText = `${options.hymn.number}. ${options.hymn.title}`;
  if (options.includeTitle) {
    mCtx.font = titleFont;
    titleLines = wrapCanvasLine(mCtx, fullTitleText, contentMaxWidth);
  }

  // 2. Medir blocos e gaps
  type MeasuredBlock =
    | { kind: 'gap' }
    | { kind: 'section'; isChorus: boolean; wrappedLines: string[] };

  const measuredBlocks: MeasuredBlock[] = [];
  for (const item of items) {
    if (item.kind === 'gap') {
      measuredBlocks.push({ kind: 'gap' });
    } else {
      const isChorus = item.section.type === 'chorus';
      mCtx.font = isChorus ? chorusFont : verseFont;
      const wrappedLines: string[] = [];
      for (const rawLine of item.section.lines) {
        wrappedLines.push(...wrapCanvasLine(mCtx, rawLine, contentMaxWidth));
      }
      measuredBlocks.push({
        kind: 'section',
        isChorus,
        wrappedLines,
      });
    }
  }

  // 3. Calcular altura total do Card
  let contentHeight = 0;

  if (options.includeTitle) {
    contentHeight += titleLines.length * titleLineHeight + 32 + 36; // título + espaço + divisor
  }

  measuredBlocks.forEach((block, idx) => {
    if (block.kind === 'gap') {
      contentHeight += gapIndicatorHeight;
    } else {
      contentHeight += block.wrappedLines.length * lyricLineHeight;
    }
    if (idx < measuredBlocks.length - 1) {
      contentHeight += sectionSpacing;
    }
  });

  if (options.includeFooter) {
    contentHeight += 52 + 36; // espaço + rodapé
  }

  const cardHeight = cardInnerPaddingY * 2 + contentHeight;
  const canvasHeight = cardHeight + outerPadding * 2;

  // 4. Desenhar no Canvas final
  const canvas = document.createElement('canvas');
  canvas.width = canvasWidth;
  canvas.height = canvasHeight;
  const ctx = canvas.getContext('2d')!;

  // Fundo externo
  ctx.fillStyle = palette.outerBg;
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  // Card com cantos arredondados
  const cardY = outerPadding;
  const radius = 40;
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(cardX, cardY, cardWidth, cardHeight, radius);
  ctx.fillStyle = palette.cardBg;
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = palette.cardBorder;
  ctx.stroke();
  ctx.restore();

  let cursorY = cardY + cardInnerPaddingY;
  const startX = cardX + cardInnerPaddingX;

  // Desenhar Cabeçalho ("X. Título")
  if (options.includeTitle && titleLines.length > 0) {
    ctx.font = titleFont;
    ctx.textBaseline = 'top';

    const numPrefix = `${options.hymn.number}.`;
    titleLines.forEach((line, idx) => {
      if (idx === 0 && line.startsWith(numPrefix)) {
        const restOfLine = line.slice(numPrefix.length);
        ctx.fillStyle = palette.accentColor;
        ctx.fillText(numPrefix, startX, cursorY);
        const prefixWidth = ctx.measureText(numPrefix).width;
        ctx.fillStyle = palette.titleColor;
        ctx.fillText(restOfLine, startX + prefixWidth, cursorY);
      } else {
        ctx.fillStyle = palette.titleColor;
        ctx.fillText(line, startX, cursorY);
      }
      cursorY += titleLineHeight;
    });

    cursorY += 28;
    // Linha divisória sutil
    ctx.beginPath();
    ctx.moveTo(startX, cursorY);
    ctx.lineTo(startX + contentMaxWidth, cursorY);
    ctx.strokeStyle = palette.cardBorder;
    ctx.lineWidth = 2;
    ctx.stroke();
    cursorY += 40;
  }

  // Desenhar Estrofes, Coros e Indicadores de Corte ("•••")
  measuredBlocks.forEach((block, idx) => {
    if (block.kind === 'gap') {
      ctx.save();
      ctx.font = '700 32px "Inter", system-ui, sans-serif';
      ctx.fillStyle = palette.mutedColor;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('• • •', cardX + cardWidth / 2, cursorY + gapIndicatorHeight / 2);
      ctx.restore();
      cursorY += gapIndicatorHeight;
    } else {
      ctx.font = block.isChorus ? chorusFont : verseFont;
      ctx.fillStyle = block.isChorus ? palette.chorusColor : palette.verseColor;
      ctx.textBaseline = 'top';

      for (const line of block.wrappedLines) {
        ctx.fillText(line, startX, cursorY);
        cursorY += lyricLineHeight;
      }
    }

    if (idx < measuredBlocks.length - 1) {
      cursorY += sectionSpacing;
    }
  });

  // Desenhar Rodapé ("Hinário IDC" + ícone outline discreto)
  if (options.includeFooter) {
    cursorY += 52;
    ctx.font = footerFont;
    ctx.fillStyle = palette.mutedColor;
    ctx.textBaseline = 'middle';

    const footerLabel = 'Hinário IDC';
    const iconSize = 34;
    const gapBetween = 12;
    const labelWidth = ctx.measureText(footerLabel).width;
    const totalFooterWidth = iconSize + gapBetween + labelWidth;
    const footerStartX = cardX + (cardWidth - totalFooterWidth) / 2;
    const centerY = cursorY + 18;

    drawOutlineLogoOnCanvas(ctx, footerStartX, centerY - iconSize / 2, iconSize, palette.mutedColor);
    ctx.fillText(footerLabel, footerStartX + iconSize + gapBetween, centerY + 1);
  }

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error('Falha ao gerar imagem do hino'));
      },
      'image/png',
      1.0
    );
  });
}

/**
 * Faz o download direto de um Blob PNG no dispositivo/navegador.
 */
export function downloadImageBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

/**
 * Compartilha a imagem gerada usando a Web Share API (com suporte a arquivos no mobile)
 * ou faz o download automático caso o navegador não suporte compartilhamento de arquivos.
 */
export async function shareOrDownloadImageBlob(
  blob: Blob,
  filename: string,
  title: string
): Promise<'shared' | 'downloaded'> {
  const file = new File([blob], filename, { type: 'image/png' });

  if (
    typeof navigator !== 'undefined' &&
    typeof navigator.canShare === 'function' &&
    navigator.canShare({ files: [file] })
  ) {
    await navigator.share({
      title,
      files: [file],
    });
    return 'shared';
  }

  downloadImageBlob(blob, filename);
  return 'downloaded';
}

/**
 * Compartilha texto usando a Web Share API ou copia para a área de transferência como fallback.
 */
export async function shareOrCopyText(
  text: string,
  title: string
): Promise<'shared' | 'copied'> {
  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
    await navigator.share({
      title,
      text,
    });
    return 'shared';
  }

  await copyTextToClipboard(text);
  return 'copied';
}

export async function copyTextToClipboard(text: string): Promise<void> {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}
