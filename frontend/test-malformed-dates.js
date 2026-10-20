#!/usr/bin/env node
/**
 * Test date validation in generate-sitemap.js and prerender.js
 * 
 * Tests that impossible dates (2026-13-45, 2099-02-30, 9999-99-99) are
 * correctly treated as immediate shutdown (hidden) while valid dates pass.
 */

import { isFeedVisible } from './prerender.js';

function testImpossibleDates() {
  const testCases = [
    { date: '2026-13-45', desc: 'impossible month and day', expected: false },
    { date: '2099-02-30', desc: 'impossible February 30', expected: false },
    { date: '9999-99-99', desc: 'impossible month and day', expected: false },
    { date: '2026-12-31', desc: 'valid future date', expected: true },
    { date: '2099-12-31', desc: 'valid far-future date', expected: true },
    { date: '1900-01-01', desc: 'valid past date', expected: false },
  ];
  
  let passed = 0;
  let failed = 0;
  
  for (const { date, desc, expected } of testCases) {
    const feed = { shutdown_date: date };
    const result = isFeedVisible(feed);
    const status = result === expected ? '✓' : '✗';
    
    if (result === expected) {
      passed++;
      console.log(`${status} ${date} (${desc}): ${expected ? 'visible' : 'hidden'}`);
    } else {
      failed++;
      console.error(`${status} ${date} (${desc}): expected ${expected}, got ${result}`);
    }
  }
  
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

testImpossibleDates();
