#!/usr/bin/env node

/**
 * Prerender static HTML files for all routes with proper meta tags
 * This ensures link unfurlers (Slack, Discord, X, LinkedIn) see correct previews
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read registries from frontend/data/
const feedsRegistry = JSON.parse(fs.readFileSync(path.join(__dirname, 'data/registry.json'), 'utf8'));
const ccipRegistry = JSON.parse(fs.readFileSync(path.join(__dirname, 'data/ccip_registry.json'), 'utf8'));

// Read the built index.html template
const distPath = path.join(__dirname, 'dist');
const templatePath = path.join(distPath, 'index.html');

if (!fs.existsSync(templatePath)) {
  console.error('Error: dist/index.html not found. Run `npm run build` first.');
  process.exit(1);
}

const template = fs.readFileSync(templatePath, 'utf8');

const SITE_URL = 'https://www.linknodes.io';
const SITE_NAME = 'LinkNodes.io';

/**
 * Inject meta tags into HTML template
 */
function injectMetaTags(html, {
  title,
  description,
  canonical,
  ogImage = `${SITE_URL}/og-default.png`,
  jsonLd = null
}) {
  // Replace title
  html = html.replace(/<title>.*?<\/title>/, `<title>${title}</title>`);
  
  // Replace meta description
  html = html.replace(
    /<meta name="description" content=".*?" ?\/?>/,
    `<meta name="description" content="${description}" />`
  );
  
  // Replace canonical
  html = html.replace(
    /<link rel="canonical" href=".*?" ?\/?>/,
    `<link rel="canonical" href="${canonical}" />`
  );
  
  // Replace OG tags
  html = html.replace(
    /<meta property="og:title" content=".*?" ?\/?>/,
    `<meta property="og:title" content="${title}" />`
  );
  html = html.replace(
    /<meta property="og:description" content=".*?" ?\/?>/,
    `<meta property="og:description" content="${description}" />`
  );
  html = html.replace(
    /<meta property="og:url" content=".*?" ?\/?>/,
    `<meta property="og:url" content="${canonical}" />`
  );
  html = html.replace(
    /<meta property="og:image" content=".*?" ?\/?>/,
    `<meta property="og:image" content="${ogImage}" />`
  );
  
  // Replace Twitter tags
  html = html.replace(
    /<meta name="twitter:title" content=".*?" ?\/?>/,
    `<meta name="twitter:title" content="${title}" />`
  );
  html = html.replace(
    /<meta name="twitter:description" content=".*?" ?\/?>/,
    `<meta name="twitter:description" content="${description}" />`
  );
  html = html.replace(
    /<meta name="twitter:image" content=".*?" ?\/?>/,
    `<meta name="twitter:image" content="${ogImage}" />`
  );
  
  // Add JSON-LD if provided
  if (jsonLd) {
    const jsonLdTag = `\n    <script type="application/ld+json">${JSON.stringify(jsonLd)}</script>`;
    html = html.replace('</head>', `${jsonLdTag}\n  </head>`);
  }
  
  return html;
}

/**
 * Write HTML file to disk
 */
function writeHtmlFile(relativePath, html) {
  const fullPath = path.join(distPath, relativePath, 'index.html');
  const dir = path.dirname(fullPath);
  
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(fullPath, html);
  
  return fullPath;
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

console.log('Prerendering static HTML files...\n');

let fileCount = 0;

// 1. Product pages
const productPages = [
  {
    path: 'products/data-feeds',
    title: 'Data Feeds — Live Chainlink Price Oracles | LinkNodes.io',
    description: 'Query 1,400+ live Chainlink Data Feeds across 13 mainnets. Get real-time prices, contract addresses, and production code snippets. Free developer toolkit.'
  },
  {
    path: 'products/ccip',
    title: 'CCIP — Cross-Chain Interoperability Protocol | LinkNodes.io',
    description: 'Explore Chainlink CCIP configuration across 49 supported lanes. Generate production code for cross-chain transfers with real contract addresses and fee estimators.'
  },
  {
    path: 'products/vrf',
    title: 'VRF — Verifiable Random Function | LinkNodes.io',
    description: 'Integrate Chainlink VRF for provably fair random numbers. Get subscription IDs, key hashes, and production-ready smart contracts for on-chain randomness.'
  },
  {
    path: 'products/functions',
    title: 'Functions — Serverless Web3 Computation | LinkNodes.io',
    description: 'Build hybrid smart contracts with Chainlink Functions. Connect any API to your smart contract with zero infrastructure. Get subscription IDs and code examples.'
  },
  {
    path: 'products/automation',
    title: 'Automation — Decentralized Smart Contract Execution | LinkNodes.io',
    description: 'Automate smart contract functions with Chainlink Automation. Time-based and custom logic triggers for decentralized, reliable on-chain automation.'
  }
];

for (const page of productPages) {
  const html = injectMetaTags(template, {
    title: page.title,
    description: page.description,
    canonical: `${SITE_URL}/${page.path}`
  });
  writeHtmlFile(page.path, html);
  fileCount++;
}

// 2. CCIP lane pages
const ccipLanes = [];
for (const [sourceId, sourceNetwork] of Object.entries(ccipRegistry.networks)) {
  const supports = sourceNetwork.supports || [];
  for (const destId of supports) {
    if (ccipRegistry.networks[destId]) {
      ccipLanes.push({ source: sourceId, dest: destId });
    }
  }
}

for (const lane of ccipLanes) {
  const sourceName = ccipRegistry.networks[lane.source].label;
  const destName = ccipRegistry.networks[lane.dest].label;
  
  const html = injectMetaTags(template, {
    title: `${sourceName} → ${destName} CCIP Lane | LinkNodes.io`,
    description: `Configure Chainlink CCIP transfers from ${sourceName} to ${destName}. Get router addresses, chain selectors, and production code for cross-chain messaging.`,
    canonical: `${SITE_URL}/products/ccip/${lane.source}/${lane.dest}`
  });
  
  writeHtmlFile(`products/ccip/${lane.source}/${lane.dest}`, html);
  fileCount++;
}

// 3. Feed index pages
const feedIndexHtml = injectMetaTags(template, {
  title: '1,400+ Chainlink Data Feeds — All Networks | LinkNodes.io',
  description: 'Browse all Chainlink Data Feeds across 13 mainnet networks. Get proxy addresses, latest prices, heartbeats, and production-ready code for any price feed.',
  canonical: `${SITE_URL}/feeds`
});
writeHtmlFile('feeds', feedIndexHtml);
fileCount++;

// 4. Per-chain feed index pages
for (const [chainId, network] of Object.entries(feedsRegistry.networks)) {
  const html = injectMetaTags(template, {
    title: `${network.label} Data Feeds — ${network.feed_count} Chainlink Oracles | LinkNodes.io`,
    description: `Browse ${network.feed_count} Chainlink price feeds on ${network.label}. Get proxy addresses, heartbeats, decimals, and copy-ready Solidity/JS code for ${network.label} data feeds.`,
    canonical: `${SITE_URL}/feeds/${chainId}`
  });
  
  writeHtmlFile(`feeds/${chainId}`, html);
  fileCount++;
}

// 5. Individual feed pages
for (const [chainId, network] of Object.entries(feedsRegistry.networks)) {
  for (const [feedSlug, feed] of Object.entries(network.feeds)) {
    const jsonLd = {
      '@context': 'https://schema.org',
      '@type': 'DataFeed',
      name: feed.name,
      description: `Chainlink ${feed.name} price feed on ${network.label}`,
      provider: {
        '@type': 'Organization',
        name: 'Chainlink',
        url: 'https://chain.link'
      },
      url: `${SITE_URL}/feeds/${chainId}/${feedSlug}`,
      identifier: feed.address
    };
    
    const html = injectMetaTags(template, {
      title: `${feed.name} on ${network.label} — Live Chainlink Price Feed | LinkNodes.io`,
      description: `Get ${feed.name} price data from Chainlink on ${network.label}. Proxy: ${feed.address}. Heartbeat: ${feed.heartbeat}s. Decimals: ${feed.decimals}. Free production code snippets.`,
      canonical: `${SITE_URL}/feeds/${chainId}/${feedSlug}`,
      jsonLd
    });
    
    writeHtmlFile(`feeds/${chainId}/${feedSlug}`, html);
    fileCount++;
  }
}

// 6. Operators page
const operatorsHtml = injectMetaTags(template, {
  title: 'Node Operators — Chainlink Oracle Network | LinkNodes.io',
  description: 'Explore Chainlink node operators providing secure, reliable oracle services. View operator profiles, reputation scores, and network contributions.',
  canonical: `${SITE_URL}/operators`
});
writeHtmlFile('operators', operatorsHtml);
fileCount++;

// 7. 404 page
const notFoundHtml = injectMetaTags(template, {
  title: 'Page Not Found (404) | LinkNodes.io',
  description: 'The page you are looking for does not exist.',
  canonical: `${SITE_URL}/404`
});
fs.writeFileSync(path.join(distPath, '404.html'), notFoundHtml);
fileCount++;

console.log(`✅ Prerendered ${fileCount} HTML files`);
console.log(`   - ${productPages.length} product pages`);
console.log(`   - ${ccipLanes.length} CCIP lane pages`);
console.log(`   - ${Object.keys(feedsRegistry.networks).length + 1} feed index pages`);
console.log(`   - ${Object.values(feedsRegistry.networks).reduce((sum, n) => sum + Object.keys(n.feeds).length, 0)} individual feed pages`);
console.log(`   - 1 operators page`);
console.log(`   - 1 404 page`);
