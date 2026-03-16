'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import { useI18n } from '@/lib/i18n';
import { api } from '@/lib/api';
import * as echarts from 'echarts';

function formatNum(n: number): string {
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toFixed(2);
}

export default function OrderbookPage() {
  const { t } = useI18n();
  const [orderbook, setOrderbook] = useState<any>(null);
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [loading, setLoading] = useState(true);
  const depthChartRef = useRef<HTMLDivElement>(null);
  const depthInstance = useRef<echarts.ECharts | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getOrderbook(symbol);
      setOrderbook(res?.data || null);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [symbol]);

  useEffect(() => {
    setLoading(true);
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    if (!depthChartRef.current || !orderbook) return;
    const bids: [number, number][] = orderbook.bids || [];
    const asks: [number, number][] = orderbook.asks || [];
    if (!bids.length && !asks.length) return;

    if (!depthInstance.current) {
      depthInstance.current = echarts.init(depthChartRef.current, 'dark');
    }
    const chart = depthInstance.current;

    const sortedBids = [...bids].sort((a, b) => b[0] - a[0]);
    const sortedAsks = [...asks].sort((a, b) => a[0] - b[0]);

    let cumBid = 0;
    const bidCumulative = sortedBids.map(([price, qty]) => {
      cumBid += qty;
      return [price, cumBid];
    }).reverse();

    let cumAsk = 0;
    const askCumulative = sortedAsks.map(([price, qty]) => {
      cumAsk += qty;
      return [price, cumAsk];
    });

    const avgQty = (cumBid + cumAsk) / Math.max(bids.length + asks.length, 1);
    const whaleThreshold = avgQty / Math.max(bids.length + asks.length, 1) * 3 * (bids.length + asks.length);

    const whaleBids = (orderbook.whale_bids || []).map((b: [number, number]) => ({
      coord: [b[0], 0], symbol: 'diamond', symbolSize: 10,
      itemStyle: { color: '#facc15' },
      label: { show: true, formatter: `${b[1].toFixed(2)}`, position: 'top', fontSize: 9, color: '#facc15' },
    }));
    const whaleAsks = (orderbook.whale_asks || []).map((a: [number, number]) => ({
      coord: [a[0], 0], symbol: 'diamond', symbolSize: 10,
      itemStyle: { color: '#f97316' },
      label: { show: true, formatter: `${a[1].toFixed(2)}`, position: 'top', fontSize: 9, color: '#f97316' },
    }));

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params?.length) return '';
          const p = params[0];
          return `$${Number(p.data[0]).toLocaleString()}<br/>${t('orderbook.depth')}: ${Number(p.data[1]).toFixed(4)}`;
        },
      },
      legend: {
        data: [t('orderbook.bids'), t('orderbook.asks')],
        top: 10, right: 20,
        textStyle: { color: '#9ca3af' },
      },
      grid: { left: 80, right: 30, top: 50, bottom: 40 },
      xAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v: number) => '$' + Number(v).toLocaleString(),
          color: '#6b7280', fontSize: 10,
        },
        splitLine: { lineStyle: { color: '#2a2e3d' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v: number) => formatNum(v),
          color: '#6b7280',
        },
        splitLine: { lineStyle: { color: '#2a2e3d' } },
      },
      series: [
        {
          name: t('orderbook.bids'),
          type: 'line',
          data: bidCumulative,
          smooth: true,
          lineStyle: { color: '#22c55e', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34, 197, 94, 0.4)' },
              { offset: 1, color: 'rgba(34, 197, 94, 0.05)' },
            ]),
          },
          symbol: 'none',
          markPoint: whaleBids.length ? { data: whaleBids } : undefined,
        },
        {
          name: t('orderbook.asks'),
          type: 'line',
          data: askCumulative,
          smooth: true,
          lineStyle: { color: '#ef4444', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(239, 68, 68, 0.4)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0.05)' },
            ]),
          },
          symbol: 'none',
          markPoint: whaleAsks.length ? { data: whaleAsks } : undefined,
        },
      ],
      animationDuration: 500,
    };

    chart.setOption(option, true);
    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [orderbook, t]);

  useEffect(() => {
    return () => {
      if (depthInstance.current) {
        depthInstance.current.dispose();
        depthInstance.current = null;
      }
    };
  }, []);

  const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];
  const bidAskRatio = orderbook?.bid_ask_ratio ?? 0;
  const totalBid = orderbook?.total_bid_qty ?? 0;
  const totalAsk = orderbook?.total_ask_qty ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white">{t('orderbook.title')}</h2>
          <p className="text-sm text-gray-500 mt-1">{t('orderbook.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          {symbols.map((s) => (
            <button
              key={s}
              onClick={() => { setSymbol(s); setLoading(true); }}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                symbol === s ? 'bg-brand-600 text-white' : 'bg-surface-hover text-gray-400'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      {orderbook && (
        <div className="grid grid-cols-3 gap-3">
          <div className="card">
            <div className="text-xs text-gray-500">{t('orderbook.bidAskRatio')}</div>
            <div className={`text-lg font-bold ${bidAskRatio > 1 ? 'text-long' : 'text-short'}`}>
              {bidAskRatio.toFixed(3)}
            </div>
            <div className="text-[10px] text-gray-600">{bidAskRatio > 1 ? t('orderbook.buyPressure') : t('orderbook.sellPressure')}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500">{t('orderbook.totalBids')}</div>
            <div className="text-lg font-bold text-long">{formatNum(totalBid)}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500">{t('orderbook.totalAsks')}</div>
            <div className="text-lg font-bold text-short">{formatNum(totalAsk)}</div>
          </div>
        </div>
      )}

      {/* Depth Chart */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-2">{t('orderbook.depthChart')}</h3>
        {loading ? (
          <div className="text-center py-16 text-gray-500">{t('common.loading')}</div>
        ) : orderbook && ((orderbook.bids?.length ?? 0) > 0 || (orderbook.asks?.length ?? 0) > 0) ? (
          <div ref={depthChartRef} style={{ width: '100%', height: '400px' }} />
        ) : (
          <div className="text-center py-16 text-gray-600">{t('common.noData')}</div>
        )}
      </div>

      {/* Order Book Table */}
      {orderbook && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card">
            <h3 className="text-sm font-medium text-long mb-3">{t('orderbook.bids')} ({(orderbook.bids ?? []).length})</h3>
            <div className="space-y-0.5 max-h-80 overflow-y-auto">
              {(orderbook.bids ?? []).slice(0, 20).map((bid: [number, number], i: number) => {
                const maxQty = Math.max(...(orderbook.bids ?? []).map((b: [number, number]) => b[1]), 1);
                const pct = (bid[1] / maxQty) * 100;
                const isWhale = (orderbook.whale_bids ?? []).some((w: [number, number]) => w[0] === bid[0]);
                return (
                  <div key={i} className="relative flex justify-between text-xs py-1 px-2 rounded">
                    <div className="absolute inset-0 bg-long/10 rounded" style={{ width: `${pct}%` }} />
                    <span className={`relative z-10 ${isWhale ? 'text-yellow-400 font-bold' : 'text-long'}`}>
                      ${Number(bid[0]).toLocaleString()} {isWhale ? '🐋' : ''}
                    </span>
                    <span className="relative z-10 text-gray-400">{Number(bid[1]).toFixed(4)}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="card">
            <h3 className="text-sm font-medium text-short mb-3">{t('orderbook.asks')} ({(orderbook.asks ?? []).length})</h3>
            <div className="space-y-0.5 max-h-80 overflow-y-auto">
              {(orderbook.asks ?? []).slice(0, 20).map((ask: [number, number], i: number) => {
                const maxQty = Math.max(...(orderbook.asks ?? []).map((a: [number, number]) => a[1]), 1);
                const pct = (ask[1] / maxQty) * 100;
                const isWhale = (orderbook.whale_asks ?? []).some((w: [number, number]) => w[0] === ask[0]);
                return (
                  <div key={i} className="relative flex justify-between text-xs py-1 px-2 rounded">
                    <div className="absolute inset-0 bg-short/10 rounded" style={{ width: `${pct}%` }} />
                    <span className={`relative z-10 ${isWhale ? 'text-yellow-400 font-bold' : 'text-short'}`}>
                      ${Number(ask[0]).toLocaleString()} {isWhale ? '🐋' : ''}
                    </span>
                    <span className="relative z-10 text-gray-400">{Number(ask[1]).toFixed(4)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
