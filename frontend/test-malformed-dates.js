#!/usr/bin/env node

/**
 * Test that frontend JS files (generate-sitemap.js and prerender.js) properly
 * exclude feeds with malformed shutdown dates.
 * 
 * Imports the real isFeedVisible functions and tests them.
 */

import { isFeedVisible as isFeedVisible_generateSitemap } from './generate-sitemap.js';
import { isFeedVisible as isFeedVisible_prerender } from './prerender.js';

// Test cases
const testFeeds = [
  { name: "Valid future", shutdown_date: "2027-01-01", expected: true },
  { name: "Valid past", shutdown_date: "2020-01-01", expected: false },
  { name: "No date", shutdown_date: null, expected: true },
  { name: "Malformed 'garbage'", shutdown_date: "garbage", expected: false },
  { name: "Malformed 'TBD'", shutdown_date: "TBD", expected: false },
  { name: "Malformed '2026-6-3'", shutdown_date: "2026-6-3", expected: false },
  { name: "Valid today", shutdown_date: new Date().toISOString().split('T')[0], expected: true }
];

let failed = 0;

console.log("Testing generate-sitemap.js isFeedVisible function...");
for (const test of testFeeds) {
  const result = isFeedVisible_generateSitemap(test);
  const pass = result === test.expected;
  if (!pass) {
    console.log(`❌ FAIL: ${test.name} - expected ${test.expected}, got ${result}`);
    failed++;
  } else {
    console.log(`✅ PASS: ${test.name}`);
  }
}

console.log("\nTesting prerender.js isFeedVisible function...");
for (const test of testFeeds) {
  const result = isFeedVisible_prerender(test);
  const pass = result === test.expected;
  if (!pass) {
    console.log(`❌ FAIL: ${test.name} - expected ${test.expected}, got ${result}`);
    failed++;
  } else {
    console.log(`✅ PASS: ${test.name}`);
  }
}

if (failed > 0) {
  console.log(`\n❌ ${failed} test(s) failed`);
  process.exit(1);
} else {
  console.log("\n✅ All tests passed");
  process.exit(0);
}
