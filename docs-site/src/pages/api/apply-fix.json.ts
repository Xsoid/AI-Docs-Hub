import type { APIRoute } from 'astro';

const actions = [
  'codebase-memory.index',
  'docs-site.restart',
  'generated.refresh',
  'rag.reindex',
  'runtime.install-start',
  'runtime.start'
];

export const GET: APIRoute = async () =>
  new Response(
    JSON.stringify({
      status: 'ok',
      fix_server: 'http://127.0.0.1:4322',
      actions
    }),
    {
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': 'no-store'
      }
    }
  );
