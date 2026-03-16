const API_BASE = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:80/api`
  : 'http://backend:8000/api';

async function fetchAPI(endpoint: string, params?: Record<string, string>) {
  const url = new URL(`${API_BASE}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
  }
  const res = await fetch(url.toString(), { next: { revalidate: 0 } });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getTopTraders: (limit = 50, offset = 0) =>
    fetchAPI('/top-traders', { limit: String(limit), offset: String(offset) }),

  getTrader: (wallet: string) =>
    fetchAPI(`/trader/${wallet}`),

  getSignals: (symbol?: string, limit = 50) =>
    fetchAPI('/signals', { ...(symbol && { symbol }), limit: String(limit) }),

  getLiquidations: (symbol?: string, limit = 200) =>
    fetchAPI('/liquidations', { ...(symbol && { symbol }), limit: String(limit) }),

  getLiquidationMap: (symbol = 'BTCUSDT', timeframe = '24h') =>
    fetchAPI('/liquidation-map', { symbol, timeframe }),

  getOrderbook: (symbol = 'BTCUSDT') =>
    fetchAPI('/orderbook', { symbol }),

  getOpenInterest: (symbol?: string, limit = 100) =>
    fetchAPI('/open-interest', { ...(symbol && { symbol }), limit: String(limit) }),

  getFundingRates: (symbol?: string, limit = 100) =>
    fetchAPI('/funding-rates', { ...(symbol && { symbol }), limit: String(limit) }),

  getMarketOverview: () =>
    fetchAPI('/market-overview'),

  getHealth: () =>
    fetchAPI('/health'),
};
