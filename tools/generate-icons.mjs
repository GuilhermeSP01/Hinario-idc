import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const mobileDir = path.join(rootDir, 'apps', 'mobile');

// Resolve sharp a partir do @capacitor/assets instalado em apps/mobile
const mobileRequire = createRequire(path.join(mobileDir, 'package.json'));
const assetsPkgPath = mobileRequire.resolve('@capacitor/assets/package.json');
const assetsRequire = createRequire(assetsPkgPath);
const sharp = assetsRequire('sharp');

// SVG quadrado completo (sem transparência nos cantos) para Capacitor icon-only.png e ícones Web/Maskable
const fullSquareIconSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e40af" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fde68a" />
      <stop offset="100%" stop-color="#f59e0b" />
    </linearGradient>
  </defs>

  <rect width="1024" height="1024" fill="url(#bgGrad)" />
  <circle cx="512" cy="280" r="360" fill="#3b82f6" opacity="0.14" />

  <!-- Capa traseira -->
  <path
    d="M192 392 C192 364 216 344 244 348 L512 392 L780 348 C808 344 832 364 832 392 L832 748 C832 776 808 796 780 800 L512 844 L244 800 C216 796 192 776 192 748 Z"
    fill="#93c5fd"
    opacity="0.28"
  />

  <!-- Página esquerda -->
  <path
    d="M228 352 C316 344 424 364 496 404 L496 788 C424 748 316 728 228 736 Z"
    fill="#ffffff"
  />

  <!-- Página direita -->
  <path
    d="M796 352 C708 344 600 364 528 404 L528 788 C600 748 708 728 796 736 Z"
    fill="#eff6ff"
  />

  <!-- Linhas esquerda -->
  <path d="M284 448 C344 444 408 456 448 476" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
  <path d="M284 524 C344 520 408 532 448 552" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
  <path d="M284 600 C344 596 408 608 448 628" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />

  <!-- Linhas direita -->
  <path d="M740 448 C680 444 616 456 576 476" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
  <path d="M740 524 C680 520 616 532 576 552" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
  <path d="M740 600 C680 596 616 608 576 628" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />

  <!-- Marcador de página dourado -->
  <path d="M496 404 L528 404 L528 832 L512 812 L496 832 Z" fill="url(#goldGrad)" />

  <!-- Nota musical dourada -->
  <path
    d="M500 152 C500 144 506 138 514 138 C564 142 608 172 620 220 C622 228 614 234 606 230 C578 210 550 200 524 200 L524 292 C524 320 496 344 464 344 C432 344 408 324 408 296 C408 268 436 244 468 244 C480 244 492 248 500 254 Z"
    fill="url(#goldGrad)"
  />
</svg>
`;

// SVG de primeiro plano (transparente, dimensionado dentro da safe-zone central do Android Adaptive Icon)
const adaptiveForegroundSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fde68a" />
      <stop offset="100%" stop-color="#f59e0b" />
    </linearGradient>
  </defs>
  <g transform="translate(154, 154) scale(0.7)">
    <path
      d="M192 392 C192 364 216 344 244 348 L512 392 L780 348 C808 344 832 364 832 392 L832 748 C832 776 808 796 780 800 L512 844 L244 800 C216 796 192 776 192 748 Z"
      fill="#93c5fd"
      opacity="0.28"
    />
    <path d="M228 352 C316 344 424 364 496 404 L496 788 C424 748 316 728 228 736 Z" fill="#ffffff" />
    <path d="M796 352 C708 344 600 364 528 404 L528 788 C600 748 708 728 796 736 Z" fill="#eff6ff" />
    <path d="M284 448 C344 444 408 456 448 476" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M284 524 C344 520 408 532 448 552" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M284 600 C344 596 408 608 448 628" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M740 448 C680 444 616 456 576 476" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M740 524 C680 520 616 532 576 552" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M740 600 C680 596 616 608 576 628" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M496 404 L528 404 L528 832 L512 812 L496 832 Z" fill="url(#goldGrad)" />
    <path
      d="M500 152 C500 144 506 138 514 138 C564 142 608 172 620 220 C622 228 614 234 606 230 C578 210 550 200 524 200 L524 292 C524 320 496 344 464 344 C432 344 408 324 408 296 C408 268 436 244 468 244 C480 244 492 248 500 254 Z"
      fill="url(#goldGrad)"
    />
  </g>
</svg>
`;

const adaptiveBackgroundSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e40af" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" fill="url(#bgGrad)" />
  <circle cx="512" cy="340" r="360" fill="#3b82f6" opacity="0.14" />
</svg>
`;

const splashSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2732 2732" width="2732" height="2732">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#172554" />
      <stop offset="100%" stop-color="#0b0f19" />
    </linearGradient>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fde68a" />
      <stop offset="100%" stop-color="#f59e0b" />
    </linearGradient>
  </defs>
  <rect width="2732" height="2732" fill="url(#bgGrad)" />
  <g transform="translate(854, 854)">
    <path
      d="M192 392 C192 364 216 344 244 348 L512 392 L780 348 C808 344 832 364 832 392 L832 748 C832 776 808 796 780 800 L512 844 L244 800 C216 796 192 776 192 748 Z"
      fill="#93c5fd"
      opacity="0.28"
    />
    <path d="M228 352 C316 344 424 364 496 404 L496 788 C424 748 316 728 228 736 Z" fill="#ffffff" />
    <path d="M796 352 C708 344 600 364 528 404 L528 788 C600 748 708 728 796 736 Z" fill="#eff6ff" />
    <path d="M284 448 C344 444 408 456 448 476" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M284 524 C344 520 408 532 448 552" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M284 600 C344 596 408 608 448 628" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M740 448 C680 444 616 456 576 476" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M740 524 C680 520 616 532 576 552" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M740 600 C680 596 616 608 576 628" stroke="#93c5fd" stroke-width="20" stroke-linecap="round" fill="none" />
    <path d="M496 404 L528 404 L528 832 L512 812 L496 832 Z" fill="url(#goldGrad)" />
    <path
      d="M500 152 C500 144 506 138 514 138 C564 142 608 172 620 220 C622 228 614 234 606 230 C578 210 550 200 524 200 L524 292 C524 320 496 344 464 344 C432 344 408 324 408 296 C408 268 436 244 468 244 C480 244 492 248 500 254 Z"
      fill="url(#goldGrad)"
    />
  </g>
</svg>
`;

async function main() {
  const publicDir = path.join(mobileDir, 'public');
  const assetsDir = path.join(mobileDir, 'assets');
  const roundedSvgPath = path.join(publicDir, 'favicon.svg');

  await fs.mkdir(publicDir, { recursive: true });
  await fs.mkdir(assetsDir, { recursive: true });

  const roundedSvgBuffer = await fs.readFile(roundedSvgPath);

  // 1. Web & PWA Icons (em apps/mobile/public)
  await sharp(roundedSvgBuffer).resize(64, 64).png().toFile(path.join(publicDir, 'favicon.png'));
  await sharp(Buffer.from(fullSquareIconSvg)).resize(180, 180).png().toFile(path.join(publicDir, 'apple-touch-icon.png'));
  await sharp( roundedSvgBuffer ).resize(192, 192).png().toFile(path.join(publicDir, 'icon-192.png'));
  await sharp(Buffer.from(fullSquareIconSvg)).resize(512, 512).png().toFile(path.join(publicDir, 'icon-512.png'));

  // 2. Capacitor Native Assets (em apps/mobile/assets) para @capacitor/assets (APK Android & iOS)
  await sharp(Buffer.from(fullSquareIconSvg)).resize(1024, 1024).png().toFile(path.join(assetsDir, 'icon-only.png'));
  await sharp(Buffer.from(adaptiveForegroundSvg)).resize(1024, 1024).png().toFile(path.join(assetsDir, 'icon-foreground.png'));
  await sharp(Buffer.from(adaptiveBackgroundSvg)).resize(1024, 1024).png().toFile(path.join(assetsDir, 'icon-background.png'));
  await sharp(Buffer.from(splashSvg)).resize(2732, 2732).png().toFile(path.join(assetsDir, 'splash.png'));
  await sharp(Buffer.from(splashSvg)).resize(2732, 2732).png().toFile(path.join(assetsDir, 'splash-dark.png'));

  console.log('Ícones Web/PWA e assets nativos do Capacitor gerados com sucesso!');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
