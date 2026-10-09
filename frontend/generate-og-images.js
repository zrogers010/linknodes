#!/usr/bin/env node

// Simple OG image generator using Sharp
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const createOGImage = async (title, subtitle, filename) => {
  const width = 1200;
  const height = 630;
  
  const svg = `
    <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#1e293b;stop-opacity:1" />
        </linearGradient>
      </defs>
      
      <rect width="${width}" height="${height}" fill="url(#bg)"/>
      
      <!-- Accent line -->
      <rect x="0" y="0" width="${width}" height="4" fill="#3b82f6"/>
      
      <!-- Logo circle -->
      <circle cx="100" cy="100" r="45" fill="#3b82f6" opacity="0.15"/>
      <text x="100" y="120" font-family="Arial, sans-serif" font-size="48" fill="#fff" text-anchor="middle">⛓</text>
      
      <!-- Title -->
      <text x="600" y="300" font-family="Arial, sans-serif" font-size="72" font-weight="bold" fill="#fff" text-anchor="middle">${title}</text>
      
      <!-- Subtitle -->
      <text x="600" y="380" font-family="Arial, sans-serif" font-size="36" fill="#94a3b8" text-anchor="middle">${subtitle}</text>
      
      <!-- Bottom badge -->
      <rect x="475" y="520" width="250" height="50" rx="25" fill="#1e293b" stroke="#334155" stroke-width="2"/>
      <text x="600" y="555" font-family="Arial, sans-serif" font-size="24" font-weight="600" fill="#64748b" text-anchor="middle">www.linknodes.io</text>
    </svg>
  `;
  
  const outputPath = path.join(__dirname, 'public', filename);
  
  await sharp(Buffer.from(svg))
    .png()
    .toFile(outputPath);
  
  console.log(`Generated: ${outputPath}`);
};

// Generate default OG image
await createOGImage('LinkNodes.io', 'The Developer Toolkit for Chainlink', 'og-default.png');

console.log('OG image generation complete!');

