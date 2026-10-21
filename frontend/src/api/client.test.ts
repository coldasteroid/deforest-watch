import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';
import { client } from './client';

const server = setupServer(...handlers);

describe('API client contract', () => {
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('reads configuration and paginated alerts from the mock contract', async () => {
    const config = await client.config();
    const health = await client.health();
    const response = await client.alerts({ tier: 'critical', sort: 'area_ha', order: 'desc' });
    expect(config).toHaveProperty('ndvi_drop_threshold');
    expect(['ok', 'degraded']).toContain(health.status);
    expect(response).toHaveProperty('items');
    expect(response).toHaveProperty('total');
  });

  it('sends the write API key on feedback', async () => {
    localStorage.setItem('dw_api_key', 'test-key');
    const response = await client.feedback('b2f1a7c3-4d55-4e8a-9f01-6b7c8d9e0a11', 'verified', 'checked');
    expect(response.status).toBe('verified');
    localStorage.removeItem('dw_api_key');
  });
});
