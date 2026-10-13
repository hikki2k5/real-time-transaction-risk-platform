import { test } from 'node:test';
import assert from 'node:assert/strict';
import { proxyAssistant } from '../app/lib/assistant-proxy.ts';

const config = { authBaseUrl: 'https://auth.example', assistantBaseUrl: 'https://assistant.example', operatorToken: 'test-operator' };
const request = (body = { question: 'Why REVIEW?' }, token = 'test-user') => new Request('http://localhost/api/assistant', {
  method: 'POST', headers: token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : {},
  body: JSON.stringify(body)
});

test('denies requests without login before calling upstream', async () => {
  const result = await proxyAssistant(request(undefined, ''), config, () => assert.fail('upstream called'));
  assert.equal(result.status, 401);
});
test('requires server-side configuration', async () => {
  assert.equal((await proxyAssistant(request(), { ...config, operatorToken: '' })).status, 503);
});
test('rejects invalid input and unsupported service URLs', async () => {
  assert.equal((await proxyAssistant(request({ question: 'a' }), config)).status, 400);
  assert.equal((await proxyAssistant(request({ question: 'valid', transaction_id: 23 }), config)).status, 400);
  assert.equal((await proxyAssistant(request(), { ...config, authBaseUrl: 'file:///tmp' })).status, 503);
});
test('expired JWT cannot reach assistant', async () => {
  let calls = 0;
  const result = await proxyAssistant(request(), config, async () => { calls++; return new Response('', { status: 401 }); });
  assert.equal(result.status, 401);
  assert.equal(calls, 1);
});
test('verified identity replaces client user ID and operator secret never returns to client', async () => {
  let calls = 0;
  const result = await proxyAssistant(request({ question: 'Why REVIEW?', transaction_id: 'tx-test', user_id: 'other-user' }), config,
    async (url, init) => {
      calls++;
      if (calls === 1) {
        assert.equal(url, 'https://auth.example/v1/auth/me');
        assert.equal(init.headers.Authorization, 'Bearer test-user');
        return Response.json({ userId: 'verified-user', role: 'CUSTOMER' });
      }
      assert.equal(url, 'https://assistant.example/v1/assistant/query');
      assert.equal(init.headers.Authorization, 'Bearer test-operator');
      assert.deepEqual(JSON.parse(init.body), { question: 'Why REVIEW?', transaction_id: 'tx-test', user_id: 'verified-user' });
      return Response.json({ answer: 'Review requires investigation.', citations: [], private_secret: 'test-operator' });
    });
  assert.equal(result.status, 200);
  assert.equal(calls, 2);
  assert.equal(result.headers.get('Cache-Control'), 'no-store');
  assert.deepEqual(await result.json(), { answer: 'Review requires investigation.', citations: [], tool_calls: [] });
});
test('malformed identity fails closed', async () => {
  const result = await proxyAssistant(request(), config, async () => Response.json({ email: 'demo@example.com' }));
  assert.equal(result.status, 401);
});
test('provider errors are sanitized', async () => {
  let calls = 0;
  const result = await proxyAssistant(request(), config, async () => ++calls === 1
    ? Response.json({ userId: 'verified-user' })
    : Response.json({ detail: 'private provider credentials' }, { status: 502 }));
  assert.equal(result.status, 502);
  assert.doesNotMatch(await result.text(), /private provider/);
});
test('provider timeout returns retryable status', async () => {
  let calls = 0;
  const result = await proxyAssistant(request(), config, async () => {
    if (++calls === 1) return Response.json({ userId: 'verified-user' });
    throw new DOMException('timed out', 'TimeoutError');
  });
  assert.equal(result.status, 504);
});
test('auth timeout is distinct and does not call the assistant', async () => {
  let calls = 0;
  const result = await proxyAssistant(request(), config, async () => {
    calls++;
    throw new DOMException('timed out', 'TimeoutError');
  });
  assert.equal(result.status, 504);
  assert.equal(calls, 1);
  assert.match((await result.json()).message, /Sign-in verification timed out/);
});
test('auth network failure remains sanitized and does not bypass verification', async () => {
  let calls = 0;
  const result = await proxyAssistant(request(), config, async () => {
    calls++;
    throw new TypeError('private URL or credential details', { cause: { code: 'ENOTFOUND' } });
  });
  assert.equal(result.status, 503);
  assert.equal(calls, 1);
  assert.doesNotMatch(await result.text(), /private URL|credential/);
});
test('invalid provider answer is not forwarded', async () => {
  let calls = 0;
  const result = await proxyAssistant(request(), config, async () => ++calls === 1
    ? Response.json({ userId: 'verified-user' }) : Response.json({ answer: '' }));
  assert.equal(result.status, 502);
});
