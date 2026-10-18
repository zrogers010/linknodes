#!/usr/bin/env node

/**
 * Test that frontend JS files properly validate ISO YYYY-MM-DD dates.
 * This test checks the source files contain the strict regex validation.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read the source files
const sitemapPath = path.join(__dirname, 'generate-sitemap.js');
const prerenderPath = path.join(__dirname, 'prerender.js');

const sitemapContent = fs.readFileSync(sitemapPath, 'utf8');
const prerenderContent = fs.readFileSync(prerenderPath, 'utf8');

let failed = 0;

// Check that both files have the strict ISO date validation
console.log("Testing generate-sitemap.js has strict date validation...");
if (sitemapContent.includes('/^\\d{4}-\\d{2}-\\d{2}$/')) {
  console.log("✅ PASS: generate-sitemap.js has strict ISO YYYY-MM-DD regex");
} else {
  console.log("❌ FAIL: generate-sitemap.js missing strict ISO YYYY-MM-DD regex");
  failed++;
}

console.log("\nTesting prerender.js has strict date validation...");
if (prerenderContent.includes('/^\\d{4}-\\d{2}-\\d{2}$/')) {
  console.log("✅ PASS: prerender.js has strict ISO YYYY-MM-DD regex");
} else {
  console.log("❌ FAIL: prerender.js missing strict ISO YYYY-MM-DD regex");
  failed++;
}

// Check that malformed dates are treated as hidden (return false)
console.log("\nTesting generate-sitemap.js returns false for malformed dates...");
if (sitemapContent.includes('return false') && sitemapContent.includes('Malformed date')) {
  console.log("✅ PASS: generate-sitemap.js returns false for malformed dates");
} else {
  console.log("❌ FAIL: generate-sitemap.js doesn't return false for malformed dates");
  failed++;
}

console.log("\nTesting prerender.js returns false for malformed dates...");
if (prerenderContent.includes('return false') && prerenderContent.includes('Malformed date')) {
  console.log("✅ PASS: prerender.js returns false for malformed dates");
} else {
  console.log("❌ FAIL: prerender.js doesn't return false for malformed dates");
  failed++;
}

if (failed > 0) {
  console.log(`\n❌ ${failed} test(s) failed`);
  process.exit(1);
} else {
  console.log("\n✅ All tests passed");
  process.exit(0);
}
