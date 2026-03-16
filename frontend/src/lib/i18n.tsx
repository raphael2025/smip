'use client';
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import zh from '@/i18n/zh.json';
import en from '@/i18n/en.json';

type Locale = 'zh' | 'en';

const messages: Record<Locale, any> = { zh, en };

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextType>({
  locale: 'zh',
  setLocale: () => {},
  t: (key: string) => key,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>('zh');

  const t = useCallback((key: string): string => {
    const keys = key.split('.');
    let value: any = messages[locale];
    for (const k of keys) {
      value = value?.[k];
    }
    return typeof value === 'string' ? value : key;
  }, [locale]);

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
