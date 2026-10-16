// Static server for the generated demo forms (frontend/public/demo). Used only by the demo autofill suite.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(fileURLToPath(new URL('.', import.meta.url)), '..', '..', 'frontend', 'public', 'demo');
const port = Number(process.env.DEMO_FORMS_PORT ?? 8766);
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.pdf': 'application/pdf' };

createServer(async (req, res) => {
  const path = normalize(decodeURIComponent((req.url ?? '/').split('?')[0])).replace(/^[\/]+/, '');
  const file = join(root, path || 'forms/index.html');
  if (!file.startsWith(root)) { res.writeHead(403).end(); return; }
  try {
    const body = await readFile(file);
    const ext = file.slice(file.lastIndexOf('.'));
    res.writeHead(200, { 'Content-Type': types[ext] ?? 'application/octet-stream' });
    res.end(body);
  } catch { res.writeHead(404).end('not found'); }
}).listen(port, '127.0.0.1', () => console.log(`demo forms on http://127.0.0.1:${port}`));
