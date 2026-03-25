/// <reference types="node" />
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const CURRENT_FILE = fileURLToPath(import.meta.url);
const FRONTEND_SRC_ROOT = path.resolve(path.dirname(CURRENT_FILE), '..');
const SHOULD_SCAN_EXTENSIONS = new Set(['.ts', '.tsx']);

const isTestFile = (filename: string): boolean =>
  filename.endsWith('.test.ts') ||
  filename.endsWith('.test.tsx') ||
  filename.endsWith('.spec.ts') ||
  filename.endsWith('.spec.tsx');

const collectSourceFiles = (directory: string): string[] => {
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  const collected: string[] = [];

  for (const entry of entries) {
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'test') {
        continue;
      }
      collected.push(...collectSourceFiles(absolutePath));
      continue;
    }

    const extension = path.extname(entry.name).toLowerCase();
    if (!SHOULD_SCAN_EXTENSIONS.has(extension)) {
      continue;
    }
    if (isTestFile(entry.name)) {
      continue;
    }
    collected.push(absolutePath);
  }

  return collected;
};

describe('training legacy briefing boundary', () => {
  it('does not allow legacy briefing field usage in frontend production source', () => {
    const sourceFiles = collectSourceFiles(FRONTEND_SRC_ROOT);
    const violations: string[] = [];

    for (const absoluteFilePath of sourceFiles) {
      const content = fs.readFileSync(absoluteFilePath, 'utf8');
      if (!/\bbriefing\b/.test(content)) {
        continue;
      }

      violations.push(path.relative(FRONTEND_SRC_ROOT, absoluteFilePath));
    }

    expect(violations).toEqual([]);
  });
});
