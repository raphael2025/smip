'use client';
import { useEffect, useState } from 'react';
import { useI18n } from '@/lib/i18n';
import { api } from '@/lib/api';

function formatNum(n: number): string {
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(2) + 'K';
  return n.toFixed(2);
}

export default function MarketPage() {
  const { t } = useI18n();
  const [market, setMarket] = useState<any[]>([]);
  const [oi, setOi] = useState<any[]>([]);
  const [funding, setFunding] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [mRes, oiRes, fRes] = await Promise.allSettled([
          api.getMarketOverview(),
          api.getOpenInterest(undefined, 50),
          api.getFundingRates(undefined, 50),
        ]);
        if (mRes.status === 'fulfilled') setMarket(mRes.value?.data || []);
        if (oiRes.status === 'fulfilled') setOi(oiRes.value?.data || []);
        if (fRes.status === 'fulfilled') setFunding(fRes.value?.data || []);
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="text-center py-16 text-gray-500">{t('common.loading')}</div>;
  }

  const latestOi: Record<string, any> = {};
  oi.forEach((o) => {
    if (!latestOi[o.symbol]) latestOi[o.symbol] = o;
  });

  const latestFunding: Record<string, any> = {};
  funding.forEach((f) => {
    if (!latestFunding[f.symbol]) latestFunding[f.symbol] = f;
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">{t('market.title')}</h2>
        <p className="text-sm text-gray-500 mt-1">{t('market.subtitle')}</p>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs border-b border-surface-border">
              <th className="text-left py-3 px-3">{t('common.symbol')}</th>
              <th className="text-right py-3 px-3">{t('common.price')}</th>
              <th className="text-right py-3 px-3">{t('common.change24h')}</th>
              <th className="text-right py-3 px-3">{t('common.high24h')}</th>
              <th className="text-right py-3 px-3">{t('common.low24h')}</th>
              <th className="text-right py-3 px-3">{t('common.volume')}</th>
              <th className="text-right py-3 px-3">{t('market.fundingRate')}</th>
              <th className="text-right py-3 px-3">{t('market.openInterest')}</th>
            </tr>
          </thead>
          <tbody>
            {market.map((m) => {
              const fr = latestFunding[m.symbol];
              const oiData = latestOi[m.symbol];
              return (
                <tr key={m.symbol ?? ''} className="border-t border-surface-border hover:bg-surface-hover transition-colors">
                  <td className="py-3 px-3 text-white font-semibold">{m.symbol ?? ''}</td>
                  <td className="py-3 px-3 text-right text-white">${Number(m.price ?? 0).toLocaleString()}</td>
                  <td className={`py-3 px-3 text-right font-medium ${Number(m.price_change_24h ?? 0) >= 0 ? 'text-long' : 'text-short'}`}>
                    {Number(m.price_change_24h ?? 0) >= 0 ? '+' : ''}{Number(m.price_change_24h ?? 0).toFixed(2)}%
                  </td>
                  <td className="py-3 px-3 text-right text-gray-300">${Number(m.high_24h ?? 0).toLocaleString()}</td>
                  <td className="py-3 px-3 text-right text-gray-300">${Number(m.low_24h ?? 0).toLocaleString()}</td>
                  <td className="py-3 px-3 text-right text-gray-300">${formatNum(Number(m.volume_24h ?? 0))}</td>
                  <td className={`py-3 px-3 text-right ${fr && Number(fr.rate ?? 0) >= 0 ? 'text-long' : 'text-short'}`}>
                    {fr ? (Number(fr.rate ?? 0) * 100).toFixed(4) + '%' : '-'}
                  </td>
                  <td className="py-3 px-3 text-right text-gray-300">
                    {oiData ? formatNum(Number(oiData.total_oi ?? 0)) : '-'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {market.length === 0 && (
          <div className="text-center py-12 text-gray-600">{t('common.noData')}</div>
        )}
      </div>

      {Object.keys(latestOi).length > 0 && (
        <div className="card">
          <h3 className="text-sm font-medium text-gray-400 mb-4">{t('market.openInterest')}</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(latestOi).map(([sym, data]: [string, any]) => {
              const totalOi = Number(data.total_oi ?? 0) || 1;
              const longPct = (Number(data.long_oi ?? 0) / totalOi) * 100;
              const shortPct = (Number(data.short_oi ?? 0) / totalOi) * 100;
              return (
                <div key={sym} className="bg-surface rounded-lg p-3 border border-surface-border">
                  <div className="text-xs font-semibold text-white mb-2">{sym}</div>
                  <div className="flex gap-1 mb-2">
                    <div className="h-2 rounded-full bg-long" style={{ width: `${longPct}%` }} />
                    <div className="h-2 rounded-full bg-short" style={{ width: `${shortPct}%` }} />
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-long">{t('market.longOI')}: {longPct.toFixed(0)}%</span>
                    <span className="text-short">{t('market.shortOI')}: {shortPct.toFixed(0)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
