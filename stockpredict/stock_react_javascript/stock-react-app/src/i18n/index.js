// src/i18n/index.js
//
// react-i18next bootstrap. Default language is Vietnamese; the user's
// override is stored in localStorage under the key `lang`. Detection
// order: localStorage first, then navigator (so a Vietnamese visitor
// who has never toggled gets Vietnamese on a Vietnamese browser, and
// an English visitor gets English without explicit action).
//
// Imported once from src/index.js — components only need
// `import { useTranslation } from 'react-i18next'`.

import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import vi from './locales/vi.json';
import en from './locales/en.json';

const STORAGE_KEY = 'lang';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      vi: { translation: vi },
      en: { translation: en },
    },
    fallbackLng: 'vi',
    supportedLngs: ['vi', 'en'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: STORAGE_KEY,
      caches: ['localStorage'],
    },
    returnNull: false,
  });

export default i18n;
