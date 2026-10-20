#!/usr/bin/env node
/**
 * Test date validation in generate-sitemap.js and prerender.js
 * 
 * Tests that impossible dates (2026-13-45, 2099-02-30, 9999-99-99) and
 * malformed dates (garbage, '2026-6-3', null) are correctly treated as
 * immediate shutdown (hidden) while valid dates pass.
 * 
 * Both generate-sitemap.js and prerender.js must have strict validation.
 */

import { isFeedVisible as isFeedVisiblePrerender } from './prerender.js';
import { isFeedVisible as isFeedVisibleSitemap } from './generate-sitemap.js';

function testBothImplementations() {
  const testCases = [
    // Impossible calendar dates
    { date: '2026-13-45', desc: 'impossible month and day', expected: false },
    { date: '2099-02-30', desc: 'impossible February 30', expected: false },
    { date: '9999-99-99', desc: 'impossible month and day', expected: false },
    
    // Malformed format
    { date: 'garbage', desc: 'garbage text', expected: false },
    { date: '2026-6-3', desc: 'single-digit month/day', expected: false },
    { date: null, desc: 'null (no shutdown)', expected: true },
    
    // Valid dates
    { date: '2026-12-31', desc: 'valid future date', expected: true },
    { date: '2099-12-31', desc: 'valid far-future date', expected: true },
    { date: '1900-01-01', desc: 'valid past date', expected: false },
    
    // Today (should be visible - deprecating)
    { date: new Date().toISOString().split('T')[0], desc: 'today', expected: true },
  ];
  
  let passed = 0;
  let failed = 0;
  
  console.log('Testing prerender.js:');
  for (const { date, desc, expected } of testCases) {
    const feed = { shutdown_date: date };
    const result = isFeedVisiblePrerender(feed);
    const status = result === expected ? '✓' : '✗';
    
    if (result === expected) {
      passed++;
      console.log(`  ${status} ${String(date).padEnd(15)} (${desc}): ${expected ? 'visible' : 'hidden'}`);
    } else {
      failed++;
      console.error(`  ${status} ${String(date).padEnd(15)} (${desc}): expected ${expected}, got ${result}`);
    }
  }
  
  console.log('\nTesting generate-sitemap.js:');
  for (const { date, desc, expected } of testCases) {
    const feed = { shutdown_date: date };
    const result = isFeedVisibleSitemap(feed);
    const status = result === expected ? '✓' : '✗';
    
    if (result === expected) {
      passed++;
      console.log(`  ${status} ${String(date).padEnd(15)} (${desc}): ${expected ? 'visible' : 'hidden'}`);
    } else {
      failed++;
      console.error(`  ${status} ${String(date).padEnd(15)} (${desc}): expected ${expected}, got ${result}`);
    }
  }
  
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

testBothImplementations();
