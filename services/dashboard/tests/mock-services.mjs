// Local browser test fixture only. This file is never imported by the app.
import http from 'node:http';

const transactions = [{ transactionId: 'tx-ui-test-001', accountId: 'acct_001', amount: 125.5,
  currency: 'AUD', transactionType: 'CARD_PAYMENT', decision: 'REVIEW', riskLevel: 'MEDIUM', createdAt: '2026-10-13T00:00:00Z' }];
http.createServer(async (request, response) => {
  response.setHeader('Access-Control-Allow-Origin', 'http://127.0.0.1:3003');
  response.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  response.setHeader('Content-Type', 'application/json');
  const send = (status, body) => { response.statusCode = status; response.end(JSON.stringify(body)); };
  if (request.method === 'OPTIONS') { response.end(); return; }
  if (request.url === '/v1/auth/login') return send(200, { access_token: 'ui-test-token', email: 'ui@example.com', userId: 'ui-user', role: 'CUSTOMER' });
  if (request.url === '/v1/auth/me') return send(request.headers.authorization === 'Bearer ui-test-token' ? 200 : 401, { userId: 'ui-user', role: 'CUSTOMER' });
  if (request.url === '/v1/accounts') return send(200, [{ accountId: 'acct_001', userId: 'ui-user', status: 'ACTIVE', currency: 'AUD' }]);
  if (request.url?.startsWith('/v1/transactions')) return send(200, transactions);
  if (request.url === '/v1/assistant/query') {
    if (request.headers.authorization !== 'Bearer ui-operator-test-token') return send(401, { detail: 'invalid fixture token' });
    let text = '';
    for await (const chunk of request) text += chunk;
    const body = JSON.parse(text);
    if (body.user_id !== 'ui-user') return send(403, { detail: 'incorrect scope' });
    if (body.question.includes('failure')) return send(502, { detail: 'fixture unavailable' });
    await new Promise(resolve => setTimeout(resolve, 1000));
    return send(200, {
      answer: 'This transaction needs review because the fraud service was unavailable. The recorded probability of zero is a fallback value, not evidence of low risk. [fraud_policy#1]',
      citations: [{ doc_id: 'fraud_policy#1', title: 'Fraud Decision Policy', snippet: 'REVIEW is used when fraud scoring is unavailable and requires further investigation.', score: .85 }],
      tool_calls: [{ name: 'get_transaction_audit', result_summary: 'Scoped audit for ui-user.' }]
    });
  }
  send(404, { detail: 'not found' });
}).listen(8018, '127.0.0.1', () => console.log('UI mock service: http://127.0.0.1:8018'));
