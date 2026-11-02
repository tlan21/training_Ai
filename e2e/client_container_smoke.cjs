// Run inside the built Client image; the isolated HTTP fixture never touches product services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const { spawn } = require('node:child_process');

async function main() {
  const manifest = JSON.parse(fs.readFileSync('.next/routes-manifest.json', 'utf8'));
  assert.ok(manifest.rewrites.afterFiles.some(rule => rule.destination === 'http://gateway:8000/api/:path*'));
  const gateway = http.createServer(async (request, response) => {
    let body = '';
    for await (const chunk of request) body += chunk;
    response.setHeader('Content-Type', 'application/json');
    if (request.url.includes('fail=1')) {
      response.writeHead(503);
      response.end(JSON.stringify({ error: { code: 'AI_UNAVAILABLE', message: 'fixture unavailable' } }));
      return;
    }
    response.setHeader('Set-Cookie', 'refresh=fixture-rotated; Path=/api/auth; HttpOnly; SameSite=Lax');
    response.end(JSON.stringify({ method: request.method, path: request.url, authorization: request.headers.authorization,
      cookie: request.headers.cookie, body }));
  });
  await new Promise(resolve => gateway.listen(8000, '127.0.0.1', resolve));
  const next = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3000'], { stdio: 'inherit' });
  try {
    const origin = 'http://127.0.0.1:3000';
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt++) {
      try { ready = (await fetch(origin + '/login', { signal: AbortSignal.timeout(1000) })).status === 200; } catch {}
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    assert.ok(ready, 'Next production server must serve /login');
    const html = await (await fetch(origin + '/login')).text();
    assert.ok(html.includes('Đăng nhập'));
    const body = JSON.stringify({ purpose: 'same-origin-proxy-fixture' });
    const response = await fetch(origin + '/api/auth/refresh', { method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer fixture-access', Cookie: 'refresh=fixture-cookie' }, body });
    assert.equal(response.status, 200);
    assert.ok(response.headers.get('set-cookie').includes('HttpOnly'));
    assert.deepEqual(await response.json(), { method: 'POST', path: '/api/auth/refresh', authorization: 'Bearer fixture-access',
      cookie: 'refresh=fixture-cookie', body });
    const feed = await fetch(origin + '/api/feed?cursor=fixture-cursor&limit=10');
    assert.equal(feed.status, 200);
    assert.equal((await feed.json()).path, '/api/feed?cursor=fixture-cursor&limit=10');
    const failed = await fetch(origin + '/api/feed?fail=1');
    assert.equal(failed.status, 503);
    assert.deepEqual(await failed.json(), { error: { code: 'AI_UNAVAILABLE', message: 'fixture unavailable' } });
    console.log('INT-16 container production page + Docker rewrite + cookie/Bearer/JSON/query/error forwarding PASS');
  } finally {
    next.kill('SIGTERM');
    await new Promise(resolve => gateway.close(resolve));
    await new Promise(resolve => {
      if (next.exitCode !== null) return resolve();
      const deadline = setTimeout(() => { next.kill('SIGKILL'); resolve(); }, 5000);
      next.once('exit', () => { clearTimeout(deadline); resolve(); });
    });
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
