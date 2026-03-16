'use client';
import { useI18n } from '@/lib/i18n';
import { clsx } from 'clsx';

interface SidebarProps {
  activePage: string;
  onNavigate: (page: string) => void;
}

const NAV_ITEMS = [
  { key: 'dashboard', icon: '📊' },
  { key: 'topTraders', icon: '🏆' },
  { key: 'signals', icon: '⚡' },
  { key: 'liquidationMap', icon: '🔥' },
  { key: 'orderbook', icon: '📈' },
  { key: 'market', icon: '🌐' },
];

export default function Sidebar({ activePage, onNavigate }: SidebarProps) {
  const { t, locale, setLocale } = useI18n();

  return (
    <aside className="w-56 bg-surface-card border-r border-surface-border flex flex-col h-screen fixed left-0 top-0 z-30">
      <div className="p-4 border-b border-surface-border">
        <h1 className="text-lg font-bold text-brand-400 tracking-tight">SMIP</h1>
        <p className="text-[10px] text-gray-500 mt-0.5">{t('sidebar.subtitle')}</p>
      </div>

      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto">
        {NAV_ITEMS.map(({ key, icon }) => (
          <button
            key={key}
            onClick={() => onNavigate(key)}
            className={clsx(
              'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all',
              activePage === key
                ? 'bg-brand-600/15 text-brand-400 font-medium'
                : 'text-gray-400 hover:bg-surface-hover hover:text-gray-200'
            )}
          >
            <span className="text-base">{icon}</span>
            {t(`nav.${key}`)}
          </button>
        ))}
      </nav>

      <div className="p-3 border-t border-surface-border space-y-2">
        <a
          href="/docs"
          target="_blank"
          rel="noopener"
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-surface-hover hover:text-gray-200 transition-all"
        >
          <span>📄</span>
          {t('nav.apiDocs')}
        </a>
        <div className="flex gap-1">
          <button
            onClick={() => setLocale('zh')}
            className={clsx(
              'flex-1 py-1.5 rounded text-xs font-medium transition-all',
              locale === 'zh' ? 'bg-brand-600 text-white' : 'bg-surface-hover text-gray-400'
            )}
          >
            中文
          </button>
          <button
            onClick={() => setLocale('en')}
            className={clsx(
              'flex-1 py-1.5 rounded text-xs font-medium transition-all',
              locale === 'en' ? 'bg-brand-600 text-white' : 'bg-surface-hover text-gray-400'
            )}
          >
            EN
          </button>
        </div>
      </div>
    </aside>
  );
}
