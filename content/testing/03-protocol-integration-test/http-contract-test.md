---
title: "HTTP contract test 設計"
date: 2026-06-19
description: "HTTP REST API 的 protocol integration test — request/response 格式、status code 語意、error body 結構的驗證"
weight: 3
tags: ["testing", "integration-test", "http", "contract-test", "api"]
---

HTTP REST API 的協議複雜度比 WebSocket 低 — request body 是 JSON、response body 是 JSON、status code 有標準語意。但 mock HTTP client（回傳固定 JSON）和真實 API 之間仍然存在差異：error response 的格式、header 的必要性、認證 token 的有效期、rate limit 行為。

## HTTP protocol test 的驗證對象

### Request 格式

Client 端發送的 request 是否符合 API 規格。Content-Type header、JSON body 的欄位名稱和型別、query parameter 的格式 — 這些在 mock client 中通常不被驗證（mock 接受任何 request），但真實 API 可能因為格式不符而拒絕。

### Response 解析

Client 端能否正確解析真實 API 的 response。Mock response 通常是開發者手寫的 JSON，可能和真實 API 的 response 有微妙差異 — 欄位名稱大小寫、數值型別（integer vs float）、null vs 缺失欄位、巢狀結構。

### Error response 處理

真實 API 的 error response 格式可能和 success response 不同。Mock client 通常只模擬 success case，偶爾模擬簡化的 error case。真實 API 的 400/401/403/404/500 各自可能有不同的 error body 結構。

### 認證流程

API 的認證流程（API key、OAuth token、session cookie）在 mock 中通常被跳過。真實 API 的認證包括 token 取得、token 過期、refresh flow — 每一步都可能失敗。

## Test 結構

HTTP protocol test 的結構和 WebSocket protocol test 類似 — 對真實 API 發送真實 request、驗證真實 response。

```text
test('POST /api/resource creates resource'):
  response = await httpClient.post(
    'http://localhost:8080/api/resource',
    body: jsonEncode({'name': 'test', 'type': 'A'}),
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ...'},
  )
  expect(response.statusCode, 201)
  body = jsonDecode(response.body)
  expect(body['id'], isNotNull)
  expect(body['name'], 'test')

test('POST /api/resource with invalid body returns 400'):
  response = await httpClient.post(
    'http://localhost:8080/api/resource',
    body: jsonEncode({'invalid_field': 'value'}),
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ...'},
  )
  expect(response.statusCode, 400)
  body = jsonDecode(response.body)
  expect(body['error'], isNotNull)  // 驗證 error body 結構
```

## Consumer-driven contract test

當 client 和 server 由不同團隊開發時，[consumer-driven contract test](/testing/knowledge-cards/consumer-driven-contract-test/) 是 protocol integration test 的延伸。Client 團隊定義「我期望的 request/response 格式」（contract），server 團隊驗證 server 實作是否符合 contract。

Consumer-driven contract test 的工具（Pact、Spring Cloud Contract）自動化了 contract 的定義、驗證和版本管理。適合 API 有多個 consumer 且需要獨立部署的場景。

自用工具或 client/server 同一人開發的場景不需要 contract test 工具 — 直接對真實 server 跑 protocol integration test 更簡單。

## 下一步路由

- CI 中如何管理 test 用的 server → [CI 中的服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)
- WebSocket 的 protocol test → [WebSocket 協議測試實作](/testing/03-protocol-integration-test/websocket-protocol-test/)
- 什麼時候用 contract test 替代 protocol integration test → [成本判斷表](/testing/03-protocol-integration-test/cost-judgment/)
- Backend 的 contract testing 實務 → [Backend 可靠性 contract testing](/backend/06-reliability/contract-testing/)
