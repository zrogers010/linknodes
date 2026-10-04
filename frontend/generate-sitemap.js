#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read the CCIP registry
const registryPath = path.join(__dirname, '../backend/ccip_registry.json');
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));

// Generate all valid CCIP lanes
const lanes = [];
for (const [sourceId, sourceNetwork] of Object.entries(registry.networks)) {
  const supports = sourceNetwork.supports || [];
  for (const destId of supports) {
    if (registry.networks[destId]) {
      lanes.push({ source: sourceId, dest: destId });
    }
  }
}

console.log(`Found ${lanes.length} valid CCIP lanes`);

// Generate sitemap XML
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.linknodes.io/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.linknodes.io/products/data-feeds</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.linknodes.io/products/ccip</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
${lanes.map(lane => `  <url>
    <loc>https://www.linknodes.io/products/ccip/${lane.source}/${lane.dest}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`).join('\n')}
  <url>
    <loc>https://www.linknodes.io/feeds</loc>
    <changefreq>daily</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://www.linknodes.io/operators</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>
`;

// Write sitemap
const outputPath = path.join(__dirname, 'public/sitemap.xml');
fs.writeFileSync(outputPath, sitemap);
console.log(`Sitemap generated: ${outputPath}`);
console.log(`Total URLs: ${lanes.length + 5}`);
