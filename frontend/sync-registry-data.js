#!/usr/bin/env node

/**
 * Sync registry data from backend/ to frontend/data/
 * Run this after updating backend registries
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const backendDir = path.join(__dirname, '../backend');
const dataDir = path.join(__dirname, 'data');

// Ensure data directory exists
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

// Copy registry files (mainnet + testnet)
const filesToSync = ['registry.json', 'ccip_registry.json', 'registry_testnet.json', 'ccip_registry_testnet.json'];

for (const filename of filesToSync) {
  const srcPath = path.join(backendDir, filename);
  const destPath = path.join(dataDir, filename);
  
  if (!fs.existsSync(srcPath)) {
    console.error(`❌ Source file not found: ${srcPath}`);
    process.exit(1);
  }
  
  fs.copyFileSync(srcPath, destPath);
  console.log(`✅ Synced ${filename}`);
}

console.log('\n✅ Registry data synced to frontend/data/');
