'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import { useI18n } from '@/lib/i18n';
import { api } from '@/lib/api';
import * as echarts from 'echarts';

function formatUsd(n: number): string {
  if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K';
  return '$' + n.toFixed(0);
}

export default function LiquidationPage() {
  const { t } = useI18n();
  const [mapData, setMapData] = useState<any>(null);
  const [liquidations, setLiquidations] = useState<any[]>([]);
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('24h');
  const [loading, setLoading] = useState(true);
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [mapRes, liqRes] = await Promise.all([
        api.getLiquidationMap(symbol, timeframe),
        api.getLiquidations(symbol, 50),
      ]);
      setMapData(mapRes?.data || null);
      setLiquidations(liqRes?.data || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [symbol, timeframe]);

  useEffect(() => {
    setLoading(true);
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    if (!chartRef.current || !mapData?.price_levels?.length) {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
      return;
    }

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, 'dark');
    }
    const chart = chartInstance.current;

    const levels = mapData.price_levels;
    const priceLabels = levels.map((l: any) => '$' + Number(l.price).toLocaleString());
    const longData = levels.map((l: any) => -(l.long_liq || 0));
    const shortData = levels.map((l: any) => l.short_liq || 0);
    const maxVal = Math.max(
      ...levels.map((l: any) => Math.max(l.long_liq || 0, l.short_liq || 0)),
      1
    );

    const currentPrice = mapData.current_price || 0;
    let markLineIdx = -1;
    if (currentPrice > 0) {
      let minDist = Infinity;
      levels.forEach((l: any, i: number) => {
        const dist = Math.abs(l.price - currentPrice);
        if (dist < minDist) { minDist = dist; markLineIdx = i; }
      });
    }

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const idx = params[0]?.dataIndex;
          if (idx === undefined) return '';
          const level = levels[idx];
          return `<b>${priceLabels[idx]}</b><br/>` +
            `<span style="color:#ef4444">● ${t('liquidation.longLiq')}: ${formatUsd(level.long_liq || 0)}</span><br/>` +
            `<span style="color:#22c55e">● ${t('liquidation.shortLiq')}: ${formatUsd(level.short_liq || 0)}</span><br/>` +
            `${t('liquidation.qty')}: ${level.count || 0}`;
        },
      },
      legend: {
        data: [t('liquidation.longLiq'), t('liquidation.shortLiq')],
        top: 10, right: 20,
        textStyle: { color: '#9ca3af' },
      },
      grid: { left: 120, right: 30, top: 50, bottom: 60 },
      xAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v: number) => formatUsd(Math.abs(v)),
          color: '#6b7280',
        },
        splitLine: { lineStyle: { color: '#2a2e3d' } },
        min: -maxVal * 1.1,
        max: maxVal * 1.1,
      },
      yAxis: {
        type: 'category',
        data: priceLabels,
        axisLabel: { color: '#9ca3af', fontSize: 11 },
        splitLine: { show: false },
      },
      dataZoom: [
        { type: 'slider', yAxisIndex: 0, right: 5, width: 15, filterMode: 'none' },
        { type: 'inside', yAxisIndex: 0, filterMode: 'none' },
      ],
      series: [
        {
          name: t('liquidation.longLiq'),
          type: 'bar',
          stack: 'liq',
          data: longData,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
              { offset: 0, color: 'rgba(239, 68, 68, 0.9)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0.3)' },
            ]),
            borderRadius: [4, 0, 0, 4],
          },
          markLine: markLineIdx >= 0 ? {
            silent: true,
            symbol: 'none',
            label: {
              formatter: `$${currentPrice.toLocaleString()}`,
              color: '#facc15',
              fontSize: 11,
            },
            lineStyle: { color: '#facc15', type: 'dashed', width: 1.5 },
            data: [{ yAxis: markLineIdx }],
          } : undefined,
        },
        {
          name: t('liquidation.shortLiq'),
          type: 'bar',
          stack: 'liq',
          data: shortData,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: 'rgba(34, 197, 94, 0.3)' },
              { offset: 1, color: 'rgba(34, 197, 94, 0.9)' },
            ]),
            borderRadius: [0, 4, 4, 0],
          },
        },
      ],
      animationDuration: 800,
      animationEasing: 'cubicOut',
    };

    chart.setOption(option, true);

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [mapData, t]);

  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];
  const timeframes = ['1h', '4h', '24h'];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white">{t('liquidation.title')}</h2>
          <p className="text-sm text-gray-500 mt-1">{t('liquidation.subtitle')}</p>
        </div>
        <div className="flex gap-2 items-center">
          <div className="flex gap-1">
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => { setTimeframe(tf); setLoading(true); }}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  timeframe === tf ? 'bg-brand-700 text-white' : 'bg-surface-hover text-gray-500'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
          <div className="w-px h-5 bg-surface-border" />
          <div className="flex gap-1">
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
      </div>

      {/* Summary cards */}
      {mapData && (
        <div className="grid grid-cols-3 gap-3">
          <div className="card">
            <div className="text-xs text-gray-500">{t('liquidation.longLiq')}</div>
            <div className="text-lg font-bold text-short">{formatUsd(mapData.total_long_liq || 0)}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500">{t('liquidation.shortLiq')}</div>
            <div className="text-lg font-bold text-long">{formatUsd(mapData.total_short_liq || 0)}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500">{t('common.price')}</div>
            <div className="text-lg font-bold text-white">
              ${(mapData.current_price || 0).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* ECharts Liquidation Map */}
      <div className="card">
        {loading ? (
          <div className="text-center py-16 text-gray-500">{t('common.loading')}</div>
        ) : mapData?.price_levels?.length ? (
          <div ref={chartRef} style={{ width: '100%', height: '500px' }} />
        ) : (
          <div className="text-center py-16 text-gray-600">{t('common.noData')}</div>
        )}
      </div>

      {/* Recent Liquidation Events */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-4">{t('liquidation.recentEvents')}</h3>
        {liquidations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs border-b border-surface-border">
                  <th className="text-left py-2 px-2">{t('common.symbol')}</th>
                  <th className="text-left py-2 px-2">{t('liquidation.side')}</th>
                  <th className="text-right py-2 px-2">{t('common.price')}</th>
                  <th className="text-right py-2 px-2">{t('liquidation.qty')}</th>
                  <th className="text-right py-2 px-2">{t('liquidation.usdValue')}</th>
                  <th className="text-right py-2 px-2">{t('common.source')}</th>
                  <th className="text-right py-2 px-2">{t('common.time')}</th>
                </tr>
              </thead>
              <tbody>
                {liquidations.map((l) => (
                  <tr key={l.id} className="border-t border-surface-border hover:bg-surface-hover transition-colors">
                    <td className="py-2 px-2 text-white">{l.symbol ?? ''}</td>
                    <td className="py-2 px-2">
                      <span className={(l.side ?? '') === 'LONG' ? 'badge-long' : 'badge-short'}>{l.side ?? '-'}</span>
                    </td>
                    <td className="py-2 px-2 text-right text-gray-300">${Number(l.price ?? 0).toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-gray-300">{Number(l.qty ?? 0).toFixed(4)}</td>
                    <td className="py-2 px-2 text-right text-white font-medium">{formatUsd(l.usd_value || (l.qty ?? 0) * (l.price ?? 0))}</td>
                    <td className="py-2 px-2 text-right text-gray-500 text-xs">{l.source ?? ''}</td>
                    <td className="py-2 px-2 text-right text-gray-500 text-xs">
                      {l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-600">{t('common.noData')}</div>
        )}
      </div>
    </div>
  );
}
