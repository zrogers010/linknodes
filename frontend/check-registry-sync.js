#!/usr/bin/env node

/**
 * CI check: Verify frontend/data/ is in sync with backend/
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function hashFile(filepath) {
  const content = fs.readFileSync(filepath, 'utf8');
  return crypto.createHash('sha256').update(content).digest('hex');
}

const filesToCheck = ['registry.json', 'ccip_registry.json'];
let allMatch = true;

console.log('Checking registry data sync...\n');

for (const filename of filesToCheck) {
  const backendPath = path.join(__dirname, '../backend', filename);
  const frontendPath = path.join(__dirname, 'data', filename);
  
  if (!fs.existsSync(backendPath)) {
    console.error(`❌ Backend file missing: ${backendPath}`);
    allMatch = false;
    continue;
  }
  
  if (!fs.existsSync(frontendPath)) {
    console.error(`❌ Frontend data file missing: ${frontendPath}`);
    console.error(`   Run: cd frontend && node sync-registry-data.js`);
    allMatch = false;
    continue;
  }
  
  const backendHash = hashFile(backendPath);
  const frontendHash = hashFile(frontendPath);
  
  if (backendHash !== frontendHash) {
    console.error(`❌ ${filename} is out of sync`);
    console.error(`   Backend hash:  ${backendHash.substring(0, 16)}...`);
    console.error(`   Frontend hash: ${frontendHash.substring(0, 16)}...`);
    console.error(`   Run: cd frontend && node sync-registry-data.js`);
    allMatch = false;
  } else {
    console.log(`✅ ${filename} is in sync`);
  }
}

if (!allMatch) {
  console.error('\n❌ Registry data is out of sync. Run: cd frontend && node sync-registry-data.js');
  process.exit(1);
}

console.log('\n✅ All registry data is in sync');
