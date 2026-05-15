import type { APIRoute } from 'astro';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const execFileAsync = promisify(execFile);
const here = dirname(fileURLToPath(import.meta.url));
const hubRoot = resolve(here, '../../../..');
const statusScript = resolve(hubRoot, 'scripts/hub-status');

async function readStatus() {
  try {
    const result = await execFileAsync('python3.11', [statusScript, '--json'], {
      cwd: hubRoot,
      timeout: 7000,
      maxBuffer: 1024 * 1024
    });
    return JSON.parse(result.stdout);
  } catch (error) {
    const err = error as { stdout?: string; stderr?: string; message?: string; code?: number };
    if (err.stdout) {
      try {
        return JSON.parse(err.stdout);
      } catch {
        // Fall through to the structured error below.
      }
    }
    return {
      status: 'down',
      checked_at: new Date().toISOString(),
      exit_code: typeof err.code === 'number' ? err.code : 1,
      components: {},
      error: err.stderr || err.message || 'hub-status failed'
    };
  }
}

export const GET: APIRoute = async () => {
  const payload = await readStatus();
  return new Response(JSON.stringify(payload), {
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store'
    }
  });
};

