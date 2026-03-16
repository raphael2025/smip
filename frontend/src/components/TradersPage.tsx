'use client';
import { useEffect, useState } from 'react';
import { useI18n } from '@/lib/i18n';
import { api } from '@/lib/api';

function formatNum(n: number): string {
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(2) + 'K';
  return n.toFixed(2);
}

export default function TradersPage() {
  const { t } = useI18n();
  const [traders, setTraders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getTopTraders(100);
        setTraders(res?.data || []);
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">{t('traders.title')}</h2>
        <p className="text-sm text-gray-500 mt-1">{t('traders.subtitle')}</p>
      </div>

      <div className="card overflow-x-auto">
        {loading ? (
          <div className="text-center py-12 text-gray-500">{t('common.loading')}</div>
        ) : traders.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs border-b border-surface-border">
                <th className="text-left py-3 px-3">#</th>
                <th className="text-left py-3 px-3">{t('traders.wallet')}</th>
                <th className="text-right py-3 px-3">{t('traders.totalPnl')}</th>
                <th className="text-right py-3 px-3">{t('traders.winRate')}</th>
                <th className="text-right py-3 px-3">{t('traders.tradeCount')}</th>
                <th className="text-right py-3 px-3">{t('traders.maxDrawdown')}</th>
                <th className="text-right py-3 px-3">{t('traders.profitFactor')}</th>
                <th className="text-right py-3 px-3">{t('traders.score')}</th>
              </tr>
            </thead>
            <tbody>
              {traders.map((tr, i) => (
                <tr key={tr.wallet_address ?? i} className="border-t border-surface-border hover:bg-surface-hover transition-colors">
                  <td className="py-3 px-3 text-gray-500">{i + 1}</td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-white">
                        {(tr.wallet_address ?? '').slice(0, 8)}...{(tr.wallet_address ?? '').slice(-6)}
                      </span>
                      {tr.is_smart_money && <span className="badge-smart">{t('traders.smartMoney')}</span>}
                    </div>
                  </td>
                  <td className={`py-3 px-3 text-right font-medium ${(tr.total_pnl ?? 0) >= 0 ? 'text-long' : 'text-short'}`}>
                    ${formatNum(tr.total_pnl ?? 0)}
                  </td>
                  <td className="py-3 px-3 text-right text-gray-300">{(tr.win_rate ?? 0).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-right text-gray-300">{tr.trade_count ?? 0}</td>
                  <td className="py-3 px-3 text-right text-short">{(tr.max_drawdown ?? 0).toFixed(1)}%</td>
                  <td className="py-3 px-3 text-right text-gray-300">{(tr.profit_factor ?? 0).toFixed(2)}</td>
                  <td className="py-3 px-3 text-right text-brand-400 font-bold">{(tr.score ?? 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-12 text-gray-500">{t('common.noData')}</div>
        )}
      </div>
    </div>
  );
}
