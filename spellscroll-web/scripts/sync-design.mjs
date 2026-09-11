/**
 * Copy the canonical design system into app/styles/.
 *
 * static/css/ at the repository root is the single source of truth for both
 * frontends.  This runs from predev/prebuild so the Next.js app can never ship
 * a stale copy of the tokens the Django templates are using.
 */
import { copyFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, '..', '..', 'static', 'css');
const target = resolve(here, '..', 'app', 'styles');

const files = ['tokens.css', 'spellscroll.css'];

if (!existsSync(source)) {
  console.warn(`[sync-design] ${source} not found; keeping the existing copies.`);
  process.exit(0);
}

mkdirSync(target, { recursive: true });
for (const file of files) {
  const from = join(source, file);
  if (!existsSync(from)) {
    console.warn(`[sync-design] missing ${from}`);
    continue;
  }
  copyFileSync(from, join(target, file));
  console.log(`[sync-design] ${file}`);
}
