// src/components/Layout/LanguageSwitcher.js
//
// "EN | VI" segmented pill button. Clicking either label switches
// i18next's active language and the LanguageDetector persists the
// choice to localStorage ('lang') automatically. Active segment is
// highlighted; inactive is muted.
import React from 'react';
import { Languages } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'vi', label: 'VI' },
];

const LanguageSwitcher = () => {
  const { i18n, t } = useTranslation();
  const active = (i18n.language || 'vi').slice(0, 2);

  const change = (code) => {
    if (code !== active) {
      i18n.changeLanguage(code);
    }
  };

  return (
    <div
      className="lang-switcher"
      role="group"
      aria-label={t('common.language')}
    >
      <Languages className="lang-switcher-icon" aria-hidden="true" />
      {LANGUAGES.map((lng, idx) => (
        <React.Fragment key={lng.code}>
          {idx > 0 && <span className="lang-switcher-sep">|</span>}
          <button
            type="button"
            className={`lang-switcher-btn ${active === lng.code ? 'active' : ''}`}
            onClick={() => change(lng.code)}
            aria-pressed={active === lng.code}
          >
            {lng.label}
          </button>
        </React.Fragment>
      ))}
    </div>
  );
};

export default LanguageSwitcher;
