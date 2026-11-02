#!/usr/bin/env node

/**
 * Font-independent OG image + icon generator.
 *
 * Text is rasterized with Sharp's text renderer and an explicit bundled Inter
 * TTF (OFL). No system fonts are required — Docker/CI images without
 * fontconfig still produce legible glyphs.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const WIDTH = 1200;
const HEIGHT = 630;
const FONTS_DIR = path.join(__dirname, 'fonts');
const FONT_REGULAR = path.join(FONTS_DIR, 'Inter-Regular.ttf');
const FONT_BOLD = path.join(FONTS_DIR, 'Inter-Bold.ttf');
const PUBLIC_DIR = path.join(__dirname, 'public');

for (const fontPath of [FONT_REGULAR, FONT_BOLD]) {
  if (!fs.existsSync(fontPath)) {
    console.error(`Missing bundled font: ${fontPath}`);
    process.exit(1);
  }
}

function escapePango(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function renderText({
  text,
  fontfile,
  px,
  color,
  width,
  align = 'center',
  maxHeight,
}) {
  // Sharp's text renderer sizes via dpi (72 dpi ≈ 1 CSS px per pt).
  const buffer = await sharp({
    text: {
      text: `<span foreground="${color}">${escapePango(text)}</span>`,
      font: 'Inter',
      fontfile,
      width,
      align,
      rgba: true,
      dpi: Math.round(72 * (px / 16)),
    },
  })
    .png()
    .toBuffer();

  if (!maxHeight) return buffer;

  const meta = await sharp(buffer).metadata();
  if ((meta.height ?? 0) <= maxHeight) return buffer;
  return sharp(buffer)
    .resize({ height: maxHeight, fit: 'inside' })
    .png()
    .toBuffer();
}

function backgroundSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="${WIDTH}" height="${HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#07090f"/>
      <stop offset="100%" stop-color="#151b2e"/>
    </linearGradient>
    <radialGradient id="glow" cx="18%" cy="20%" r="45%">
      <stop offset="0%" stop-color="#2470ff" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#2470ff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="${WIDTH}" height="${HEIGHT}" fill="url(#bg)"/>
  <rect width="${WIDTH}" height="${HEIGHT}" fill="url(#glow)"/>
  <rect x="0" y="0" width="${WIDTH}" height="4" fill="#2470ff"/>
  <circle cx="96" cy="96" r="44" fill="#2470ff" fill-opacity="0.16"/>
  <polygon
    points="96,64 123,80 123,112 96,128 69,112 69,80"
    fill="none"
    stroke="#4d92ff"
    stroke-width="3.5"
    stroke-linejoin="round"
  />
  <rect x="460" y="516" width="280" height="50" rx="25" fill="#0b0e17" stroke="#2a3554" stroke-width="2"/>
</svg>`;
}

async function createOGImage({ title, subtitle, filename }) {
  const titleBuf = await renderText({
    text: title,
    fontfile: FONT_BOLD,
    px: 64,
    color: '#ffffff',
    width: 1000,
    maxHeight: 140,
  });
  const subtitleBuf = await renderText({
    text: subtitle,
    fontfile: FONT_REGULAR,
    px: 30,
    color: '#94a3b8',
    width: 960,
    maxHeight: 80,
  });
  const badgeBuf = await renderText({
    text: 'www.linknodes.io',
    fontfile: FONT_REGULAR,
    px: 20,
    color: '#94a3b8',
    width: 260,
    maxHeight: 32,
  });

  const titleMeta = await sharp(titleBuf).metadata();
  const subtitleMeta = await sharp(subtitleBuf).metadata();
  const badgeMeta = await sharp(badgeBuf).metadata();

  const titleLeft = Math.round((WIDTH - (titleMeta.width ?? 0)) / 2);
  const subtitleLeft = Math.round((WIDTH - (subtitleMeta.width ?? 0)) / 2);
  const badgeLeft = Math.round((WIDTH - (badgeMeta.width ?? 0)) / 2);

  const outputPath = path.join(PUBLIC_DIR, filename);
  await sharp(Buffer.from(backgroundSvg()))
    .composite([
      { input: titleBuf, top: 248, left: Math.max(40, titleLeft) },
      { input: subtitleBuf, top: 360, left: Math.max(40, subtitleLeft) },
      { input: badgeBuf, top: 530, left: Math.max(470, badgeLeft) },
    ])
    .png({ compressionLevel: 9, effort: 10 })
    .toFile(outputPath);

  console.log(`Generated: ${outputPath}`);
}

function pngToIco(pngBuffer) {
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(1, 4);

  const entry = Buffer.alloc(16);
  entry.writeUInt8(32, 0);
  entry.writeUInt8(32, 1);
  entry.writeUInt8(0, 2);
  entry.writeUInt8(0, 3);
  entry.writeUInt16LE(1, 4);
  entry.writeUInt16LE(32, 6);
  entry.writeUInt32LE(pngBuffer.length, 8);
  entry.writeUInt32LE(22, 12);

  return Buffer.concat([header, entry, pngBuffer]);
}

async function generateIcons() {
  const svgPath = path.join(PUBLIC_DIR, 'favicon.svg');
  const svg = fs.readFileSync(svgPath);

  const icoPng = await sharp(svg).resize(32, 32).png().toBuffer();
  fs.writeFileSync(path.join(PUBLIC_DIR, 'favicon.ico'), pngToIco(icoPng));

  await sharp(svg)
    .resize(180, 180)
    .png()
    .toFile(path.join(PUBLIC_DIR, 'apple-touch-icon.png'));

  console.log('Generated: favicon.ico, apple-touch-icon.png');
}

const pages = [
  {
    title: 'LinkNodes.io',
    subtitle: 'The Developer Toolkit for Chainlink',
    filename: 'og-default.png',
  },
  {
    title: 'Chainlink for Agents',
    subtitle: 'Skills, guardrails, and the x402 catalog',
    filename: 'og-agents.png',
  },
  {
    title: 'RWA and 24/7 feeds',
    subtitle: 'Stocks, commodities, and tokenized assets',
    filename: 'og-rwa.png',
  },
  {
    title: 'Chainlink 24/7',
    subtitle: 'Data Streams vs Data Feeds, what is live',
    filename: 'og-chainlink-247.png',
  },
  {
    title: 'Feed Catalog',
    subtitle: '1,400+ Chainlink Data Feeds across 13 mainnets',
    filename: 'og-feeds.png',
  },
];

for (const page of pages) {
  await createOGImage(page);
}

await generateIcons();

console.log('OG image and icon generation complete!');
