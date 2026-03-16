import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SMIP - Smart Money Intelligence Platform',
  description: 'Real-time crypto analytics: smart money tracking, liquidation maps, orderbook heatmaps',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" className="dark" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
