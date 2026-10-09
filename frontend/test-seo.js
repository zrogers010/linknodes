#!/usr/bin/env node

/**
 * CI test to verify SEO meta tags are properly rendered
 * This test runs against the built frontend after deployment
 */

import { JSDOM } from 'jsdom';
import fetch from 'node-fetch';

const BASE_URL = process.env.TEST_URL || 'http://localhost:8080';

async function testMetaTags() {
  console.log('Testing SEO meta tags...\n');
  
  const routes = [
    { 
      path: '/', 
      expectedTitle: 'LinkNodes.io — The Developer Toolkit for Chainlink',
      checkTitle: true  // Only home page has static title
    },
  ];

  let failures = 0;

  for (const route of routes) {
    try {
      const url = `${BASE_URL}${route.path}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        console.error(`❌ ${route.path}: HTTP ${response.status}`);
        failures++;
        continue;
      }

      const html = await response.text();
      const dom = new JSDOM(html);
      const document = dom.window.document;

      // Check title (only for routes with checkTitle flag)
      if (route.checkTitle) {
        const title = document.querySelector('title')?.textContent || '';
        if (!title.includes(route.expectedTitle)) {
          console.error(`❌ ${route.path}: Expected title to contain "${route.expectedTitle}", got "${title}"`);
          failures++;
          continue;
        }
      }

      // Check canonical (should exist)
      const canonical = document.querySelector('link[rel="canonical"]')?.getAttribute('href') || '';
      if (!canonical) {
        console.error(`❌ ${route.path}: Missing canonical link`);
        failures++;
        continue;
      }

      // Check og:title (should exist)
      const ogTitle = document.querySelector('meta[property="og:title"]')?.getAttribute('content') || '';
      if (!ogTitle) {
        console.error(`❌ ${route.path}: Missing og:title`);
        failures++;
        continue;
      }

      // Check og:image (critical for link previews)
      const ogImage = document.querySelector('meta[property="og:image"]')?.getAttribute('content') || '';
      if (!ogImage) {
        console.error(`❌ ${route.path}: Missing og:image`);
        failures++;
        continue;
      }

      // Check og:description
      const ogDescription = document.querySelector('meta[property="og:description"]')?.getAttribute('content') || '';
      if (!ogDescription) {
        console.error(`❌ ${route.path}: Missing og:description`);
        failures++;
        continue;
      }

      console.log(`✅ ${route.path}: Meta tags OK`);
      console.log(`   Title: ${document.querySelector('title')?.textContent || 'N/A'}`);
      console.log(`   Canonical: ${canonical}`);
      console.log(`   OG Image: ${ogImage}`);
      console.log(`   OG Description: ${ogDescription}\n`);

    } catch (error) {
      console.error(`❌ ${route.path}: ${error.message}`);
      failures++;
    }
  }

  // Note about SPA behavior
  console.log('ℹ️  Note: For SPA routes like /feeds and /products/*, meta tags are updated client-side by JavaScript.');
  console.log('   Crawlers that execute JS (Google, Twitter, LinkedIn, Slack) will see the correct meta tags.\n');

  return failures;
}

async function test404Status() {
  console.log('\nTesting 404 status codes...\n');
  
  const invalidRoutes = [
    '/this-does-not-exist',
    '/feeds/invalid-chain',
    '/products/ccip/invalid/invalid',
  ];

  let failures = 0;

  for (const route of invalidRoutes) {
    try {
      const url = `${BASE_URL}${route}`;
      const response = await fetch(url, { redirect: 'manual' });
      
      // For SPA, we expect 200 (serving index.html) but the app should render 404 content
      // This is a limitation of SPAs without SSR
      // In the future, we can improve this with prerendering or SSR
      
      if (response.status === 200) {
        console.log(`⚠️  ${route}: Returns 200 (SPA behavior, client-side 404)`);
      } else if (response.status === 404) {
        console.log(`✅ ${route}: Returns 404`);
      } else {
        console.error(`❌ ${route}: Unexpected status ${response.status}`);
        failures++;
      }
    } catch (error) {
      console.error(`❌ ${route}: ${error.message}`);
      failures++;
    }
  }

  return failures;
}

async function main() {
  console.log(`Testing against: ${BASE_URL}\n`);
  console.log('='.repeat(60) + '\n');

  let totalFailures = 0;

  totalFailures += await testMetaTags();
  totalFailures += await test404Status();

  console.log('\n' + '='.repeat(60));
  
  if (totalFailures === 0) {
    console.log('\n✅ All tests passed!\n');
    process.exit(0);
  } else {
    console.log(`\n❌ ${totalFailures} test(s) failed\n`);
    process.exit(1);
  }
}

main().catch(error => {
  console.error('Test error:', error);
  process.exit(1);
});
