#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Check if a feed should be included in the sitemap.
 * Drops feeds with past shutdown dates (shut_down status).
 * Keeps active and deprecating feeds (future/today shutdown dates or no shutdown date).
 * 
 * Malformed dates (non-ISO YYYY-MM-DD format) are treated as immediate shutdown (hidden).
 */
function isFeedVisible(feed) {
  const shutdownDate = feed.shutdown_date;
  if (!shutdownDate) {
    // No shutdown date => visible
    return true;
  }
  
  // Validate strict ISO YYYY-MM-DD format
  if (!/^\d{4}-\d{2}-\d{2}$/.test(shutdownDate)) {
    // Malformed date (e.g. 'garbage', 'TBD', '2026-6-3') => treat as immediate shutdown
    return false;
  }
  
  // Get UTC today in YYYY-MM-DD format
  const utcToday = new Date().toISOString().split('T')[0];
  
  // Past shutdown date => shut_down => hidden
  if (shutdownDate < utcToday) {
    return false;
  }
  
  // Today or future => deprecating => visible
  return true;
}

// Export for testing
export { isFeedVisible };

// Only run main code if executed directly (not imported)
if (import.meta.url === `file://${process.argv[1]}`) {
  // Read mainnet registries from frontend/data/
  const ccipRegistryPath = path.join(__dirname, 'data/ccip_registry.json');
  const ccipRegistry = JSON.parse(fs.readFileSync(ccipRegistryPath, 'utf8'));

  const feedsRegistryPath = path.join(__dirname, 'data/registry.json');
  const feedsRegistry = JSON.parse(fs.readFileSync(feedsRegistryPath, 'utf8'));

// Read testnet registries from frontend/data/
const ccipRegistryTestnetPath = path.join(__dirname, 'data/ccip_registry_testnet.json');
const ccipRegistryTestnet = JSON.parse(fs.readFileSync(ccipRegistryTestnetPath, 'utf8'));


const feedsRegistryTestnetPath = path.join(__dirname, 'data/registry_testnet.json');
const feedsRegistryTestnet = JSON.parse(fs.readFileSync(feedsRegistryTestnetPath, 'utf8'));

// Generate all valid CCIP lanes (mainnet + testnet)
const lanes = [];
for (const [sourceId, sourceNetwork] of Object.entries(ccipRegistry.networks)) {
  const supports = sourceNetwork.supports || [];
  for (const destId of supports) {
    if (ccipRegistry.networks[destId]) {
      lanes.push({ source: sourceId, dest: destId });
    }
  }
}

for (const [sourceId, sourceNetwork] of Object.entries(ccipRegistryTestnet.networks)) {
  const supports = sourceNetwork.supports || [];
  for (const destId of supports) {
    if (ccipRegistryTestnet.networks[destId]) {
      lanes.push({ source: sourceId, dest: destId });
    }
  }
}

// Generate all feed pages (mainnet + testnet)
const feedPages = [];
for (const [chainId, network] of Object.entries(feedsRegistry.networks)) {
  // Add chain index page
  feedPages.push({
    url: `/feeds/${chainId}`,
    priority: 0.8,
    changefreq: 'daily'
  });
  
  // Add individual feed pages (exclude shut_down feeds)
  for (const [feedSlug, feedMeta] of Object.entries(network.feeds)) {
    if (isFeedVisible(feedMeta)) {
      feedPages.push({
        url: `/feeds/${chainId}/${feedSlug}`,
        priority: 0.7,
        changefreq: 'daily'
      });
    }
  }
}

for (const [chainId, network] of Object.entries(feedsRegistryTestnet.networks)) {
  // Add chain index page
  feedPages.push({
    url: `/feeds/${chainId}`,
    priority: 0.8,
    changefreq: 'daily'
  });
  
  // Add individual feed pages (exclude shut_down feeds)
  for (const [feedSlug, feedMeta] of Object.entries(network.feeds)) {
    if (isFeedVisible(feedMeta)) {
      feedPages.push({
        url: `/feeds/${chainId}/${feedSlug}`,
        priority: 0.7,
        changefreq: 'daily'
      });
    }
  }
}

console.log(`Found ${lanes.length} valid CCIP lanes (mainnet + testnet)`);
console.log(`Found ${feedPages.length} feed pages (mainnet + testnet)`);

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
}

