'use client';
import { useState } from 'react';
import { I18nProvider } from '@/lib/i18n';
import ErrorBoundary from '@/components/ErrorBoundary';
import Sidebar from '@/components/Sidebar';
import DashboardPage from '@/components/DashboardPage';
import TradersPage from '@/components/TradersPage';
import SignalsPage from '@/components/SignalsPage';
import LiquidationPage from '@/components/LiquidationPage';
import OrderbookPage from '@/components/OrderbookPage';
import MarketPage from '@/components/MarketPage';

const pages: Record<string, React.ComponentType> = {
  dashboard: DashboardPage,
  topTraders: TradersPage,
  signals: SignalsPage,
  liquidationMap: LiquidationPage,
  orderbook: OrderbookPage,
  market: MarketPage,
};

export default function Home() {
  const [activePage, setActivePage] = useState('dashboard');
  const PageComponent = pages[activePage] || DashboardPage;

  return (
    <I18nProvider>
      <div className="flex min-h-screen">
        <Sidebar activePage={activePage} onNavigate={setActivePage} />
        <main className="flex-1 ml-56 p-6 max-w-[1400px]">
          <ErrorBoundary key={activePage}>
            <PageComponent />
          </ErrorBoundary>
        </main>
      </div>
    </I18nProvider>
  );
}
