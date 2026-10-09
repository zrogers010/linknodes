#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read the CCIP registry
const ccipRegistryPath = path.join(__dirname, '../backend/ccip_registry.json');
const ccipRegistry = JSON.parse(fs.readFileSync(ccipRegistryPath, 'utf8'));

// Read the Data Feeds registry
const feedsRegistryPath = path.join(__dirname, '../backend/registry.json');
const feedsRegistry = JSON.parse(fs.readFileSync(feedsRegistryPath, 'utf8'));

// Generate all valid CCIP lanes
const lanes = [];
for (const [sourceId, sourceNetwork] of Object.entries(ccipRegistry.networks)) {
  const supports = sourceNetwork.supports || [];
  for (const destId of supports) {
    if (ccipRegistry.networks[destId]) {
      lanes.push({ source: sourceId, dest: destId });
    }
  }
}

// Generate all feed pages
const feedPages = [];
for (const [chainId, network] of Object.entries(feedsRegistry.networks)) {
  // Add chain index page
  feedPages.push({
    url: `/feeds/${chainId}`,
    priority: 0.8,
    changefreq: 'daily'
  });
  
  // Add individual feed pages
  for (const feedSlug of Object.keys(network.feeds)) {
    feedPages.push({
      url: `/feeds/${chainId}/${feedSlug}`,
      priority: 0.7,
      changefreq: 'daily'
    });
  }
}

console.log(`Found ${lanes.length} valid CCIP lanes`);
console.log(`Found ${feedPages.length} feed pages`);

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
  <url>
    <loc>https://www.linknodes.io/products/vrf</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.linknodes.io/products/functions</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.linknodes.io/products/automation</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
${lanes.map(lane => `  <url>
    <loc>https://www.linknodes.io/products/ccip/${lane.source}/${lane.dest}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`).join('\n')}
  <url>
    <loc>https://www.linknodes.io/feeds</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
${feedPages.map(page => `  <url>
    <loc>https://www.linknodes.io${page.url}</loc>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`).join('\n')}
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
console.log(`Total URLs: ${lanes.length + feedPages.length + 8}`);

