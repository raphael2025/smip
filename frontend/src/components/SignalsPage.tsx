'use client';
import { useEffect, useState } from 'react';
import { useI18n } from '@/lib/i18n';
import { api } from '@/lib/api';

export default function SignalsPage() {
  const { t } = useI18n();
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.getSignals(undefined, 100);
        setSignals(res?.data || []);
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">{t('signals.title')}</h2>
        <p className="text-sm text-gray-500 mt-1">{t('signals.subtitle')}</p>
      </div>

      {loading ? (
        <div className="card text-center py-12 text-gray-500">{t('common.loading')}</div>
      ) : signals.length > 0 ? (
        <div className="grid gap-4">
          {signals.map((s) => (
            <div key={s.id} className="card flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-lg font-bold
                  ${(s.signal_type ?? '') === 'LONG' ? 'bg-long/15 text-long' : 'bg-short/15 text-short'}`}>
                  {(s.signal_type ?? '') === 'LONG' ? '↑' : '↓'}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-semibold">{s.symbol ?? ''}</span>
                    <span className={(s.signal_type ?? '') === 'LONG' ? 'badge-long' : 'badge-short'}>
                      {(s.signal_type ?? '') === 'LONG' ? t('signals.long') : t('signals.short')}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {s.created_at ? new Date(s.created_at).toLocaleString() : '-'}
                  </div>
                </div>
              </div>
              <div className="text-right space-y-1">
                <div className="text-sm">
                  <span className="text-gray-500">{t('signals.confidence')}: </span>
                  <span className="text-brand-400 font-bold">{((s.confidence ?? 0) * 100).toFixed(0)}%</span>
                </div>
                {s.avg_entry_price && (
                  <div className="text-xs text-gray-500">
                    {t('signals.entryPrice')}: ${Number(s.avg_entry_price).toLocaleString()}
                  </div>
                )}
                {s.total_size && (
                  <div className="text-xs text-gray-500">
                    {t('signals.totalSize')}: ${Number(s.total_size).toLocaleString()}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-16">
          <div className="text-4xl mb-3">&#x26A1;</div>
          <div className="text-gray-500">{t('signals.noSignals')}</div>
          <div className="text-xs text-gray-600 mt-1">{t('signals.noSignalsHint')}</div>
        </div>
      )}
    </div>
  );
}
