'use client';
import { useEffect, useState, useRef } from 'react';
import { useI18n } from '@/lib/i18n';
import { api } from '@/lib/api';
import * as echarts from 'echarts';

function formatNum(n: number, decimals = 2): string {
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(decimals) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(decimals) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(decimals) + 'K';
  return n.toFixed(decimals);
}

function formatPrice(n: number): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function DashboardPage() {
  const { t } = useI18n();
  const [market, setMarket] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [liquidations, setLiquidations] = useState<any[]>([]);
  const [traders, setTraders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const miniChartRef = useRef<HTMLDivElement>(null);
  const miniChartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [mRes, sRes, lRes, tRes] = await Promise.allSettled([
          api.getMarketOverview(),
          api.getSignals(undefined, 5),
          api.getLiquidations(undefined, 10),
          api.getTopTraders(5),
        ]);
        if (mRes.status === 'fulfilled') setMarket(mRes.value?.data || []);
        if (sRes.status === 'fulfilled') setSignals(sRes.value?.data || []);
        if (lRes.status === 'fulfilled') setLiquidations(lRes.value?.data || []);
        if (tRes.status === 'fulfilled') setTraders(tRes.value?.data || []);
      } catch (e) {
        console.error('Dashboard load error:', e);
      }
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  // C3: Mini liquidation chart
  useEffect(() => {
    if (!miniChartRef.current || !liquidations.length) return;

    if (!miniChartInstance.current) {
      miniChartInstance.current = echarts.init(miniChartRef.current, 'dark');
    }

    const symbolCounts: Record<string, { long: number; short: number }> = {};
    liquidations.forEach((l) => {
      const sym = l.symbol ?? 'UNKNOWN';
      if (!symbolCounts[sym]) symbolCounts[sym] = { long: 0, short: 0 };
      const usd = l.usd_value || (l.qty ?? 0) * (l.price ?? 0);
      if ((l.side ?? '') === 'LONG') symbolCounts[sym].long += usd;
      else symbolCounts[sym].short += usd;
    });

    const syms = Object.keys(symbolCounts);
    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 5, right: 5, top: 5, bottom: 20, containLabel: false },
      xAxis: {
        type: 'category', data: syms,
        axisLabel: { color: '#6b7280', fontSize: 9 },
        axisLine: { show: false }, axisTick: { show: false },
      },
      yAxis: { type: 'value', show: false },
      series: [
        {
          type: 'bar', stack: 'liq', name: 'Long',
          data: syms.map((s) => symbolCounts[s].long),
          itemStyle: { color: '#ef4444', borderRadius: [2, 2, 0, 0] },
          barWidth: '60%',
        },
        {
          type: 'bar', stack: 'liq', name: 'Short',
          data: syms.map((s) => symbolCounts[s].short),
          itemStyle: { color: '#22c55e', borderRadius: [2, 2, 0, 0] },
        },
      ],
    };
    miniChartInstance.current.setOption(option, true);
  }, [liquidations]);

  useEffect(() => {
    return () => { miniChartInstance.current?.dispose(); };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-pulse text-gray-400">{t('common.loading')}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">{t('dashboard.title')}</h2>
        <p className="text-sm text-gray-500 mt-1">{t('dashboard.subtitle')}</p>
      </div>

      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-3">{t('dashboard.marketOverview')}</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {(market.length > 0 ? market : defaultMarketData).map((m: any) => (
            <div key={m.symbol} className="card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-300">{m.symbol ?? ''}</span>
                <span className="text-[10px] text-gray-600 uppercase">{m.source || 'binance'}</span>
              </div>
              <div className="text-lg font-bold text-white">${formatPrice(Number(m.price ?? 0))}</div>
              <div className={`text-xs mt-1 font-medium ${Number(m.price_change_24h ?? 0) >= 0 ? 'text-long' : 'text-short'}`}>
                {Number(m.price_change_24h ?? 0) >= 0 ? '+' : ''}{Number(m.price_change_24h ?? 0).toFixed(2)}%
              </div>
              <div className="text-[10px] text-gray-600 mt-1">Vol: ${formatNum(Number(m.volume_24h ?? 0))}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-sm font-medium text-gray-400 mb-4">{t('dashboard.latestSignals')}</h3>
          {signals.length > 0 ? (
            <div className="space-y-3">
              {signals.map((s: any) => (
                <div key={s.id} className="flex items-center justify-between py-2 border-b border-surface-border last:border-0">
                  <div className="flex items-center gap-3">
                    <span className={(s.signal_type ?? '') === 'LONG' ? 'badge-long' : 'badge-short'}>
                      {(s.signal_type ?? '') === 'LONG' ? t('signals.long') : t('signals.short')}
                    </span>
                    <span className="text-sm font-medium text-white">{s.symbol ?? ''}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-400">
                      {t('signals.confidence')}: {((s.confidence ?? 0) * 100).toFixed(0)}%
                    </div>
                    <div className="text-[10px] text-gray-600">
                      {s.created_at ? new Date(s.created_at).toLocaleString() : '-'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-600 text-sm">{t('common.noData')}</div>
          )}
        </div>

        <div className="card">
          <h3 className="text-sm font-medium text-gray-400 mb-4">{t('dashboard.recentLiquidations')}</h3>
          {liquidations.length > 0 ? (
            <>
              <div ref={miniChartRef} style={{ width: '100%', height: '80px' }} className="mb-3" />
              <div className="space-y-2">
                {liquidations.slice(0, 8).map((l: any) => (
                  <div key={l.id} className="flex items-center justify-between py-1.5 border-b border-surface-border last:border-0">
                    <div className="flex items-center gap-2">
                      <span className={(l.side ?? '') === 'LONG' ? 'badge-long' : 'badge-short'}>
                        {l.side ?? '-'}
                      </span>
                      <span className="text-xs text-white">{l.symbol ?? ''}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-white">${formatPrice(Number(l.price ?? 0))}</div>
                      <div className="text-[10px] text-gray-500">${formatNum(l.usd_value || (l.qty ?? 0) * (l.price ?? 0))}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center py-8 text-gray-600 text-sm">{t('common.noData')}</div>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-4">{t('dashboard.topSmartMoney')}</h3>
        {traders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs">
                  <th className="text-left py-2 px-2">{t('common.rank')}</th>
                  <th className="text-left py-2 px-2">{t('traders.wallet')}</th>
                  <th className="text-right py-2 px-2">{t('traders.totalPnl')}</th>
                  <th className="text-right py-2 px-2">{t('traders.winRate')}</th>
                  <th className="text-right py-2 px-2">{t('traders.score')}</th>
                </tr>
              </thead>
              <tbody>
                {traders.map((tr: any, i: number) => (
                  <tr key={tr.wallet_address ?? i} className="border-t border-surface-border hover:bg-surface-hover transition-colors">
                    <td className="py-2 px-2 text-gray-400">#{i + 1}</td>
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-white">
                          {(tr.wallet_address ?? '').slice(0, 6)}...{(tr.wallet_address ?? '').slice(-4)}
                        </span>
                        {tr.is_smart_money && <span className="badge-smart">{t('traders.smartMoney')}</span>}
                      </div>
                    </td>
                    <td className={`py-2 px-2 text-right font-medium ${(tr.total_pnl ?? 0) >= 0 ? 'text-long' : 'text-short'}`}>
                      ${formatNum(tr.total_pnl ?? 0)}
                    </td>
                    <td className="py-2 px-2 text-right text-gray-300">{(tr.win_rate ?? 0).toFixed(1)}%</td>
                    <td className="py-2 px-2 text-right text-brand-400 font-medium">{(tr.score ?? 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-600 text-sm">{t('common.noData')}</div>
        )}
      </div>
    </div>
  );
}

const defaultMarketData = [
  { symbol: 'BTCUSDT', price: 0, price_change_24h: 0, volume_24h: 0, source: 'binance' },
  { symbol: 'ETHUSDT', price: 0, price_change_24h: 0, volume_24h: 0, source: 'binance' },
  { symbol: 'SOLUSDT', price: 0, price_change_24h: 0, volume_24h: 0, source: 'binance' },
  { symbol: 'BNBUSDT', price: 0, price_change_24h: 0, volume_24h: 0, source: 'binance' },
  { symbol: 'XRPUSDT', price: 0, price_change_24h: 0, volume_24h: 0, source: 'binance' },
];
