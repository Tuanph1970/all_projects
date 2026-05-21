// src/components/Layout/Header.js
import React, { useEffect, useState } from 'react';
import { LogOut, Menu, Search } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import NotificationBell from './NotificationBell';
import LanguageSwitcher from './LanguageSwitcher';

// Locale used for the live clock + date in the header. We bias to the
// active i18n language so a user reading the page in English doesn't
// get a Vietnamese-formatted date next to English copy.
const dateLocale = (lng) => (lng === 'en' ? 'en-GB' : 'vi-VN');
const formatTime = (d, lng) =>
  d.toLocaleTimeString(dateLocale(lng), { hour12: false });
const formatDate = (d, lng) =>
  d.toLocaleDateString(dateLocale(lng), { day: '2-digit', month: '2-digit', year: 'numeric' });

const renderTitle = ({ title, emphasis }) => {
  if (!emphasis || !title.endsWith(emphasis)) {
    return <span>{title}</span>;
  }
  const head = title.slice(0, title.length - emphasis.length).trimEnd();
  return (
    <>
      {head}
      {head && ' '}
      <em>{emphasis}</em>
    </>
  );
};

const Header = ({ alertSlot }) => {
  const { logout } = useAuth();
  const location = useLocation();
  const { t, i18n } = useTranslation();
  const segments = location.pathname.split('/').filter(Boolean);
  const key = segments.length === 0 ? 'dashboard' : segments[0];

  // i18next "returnObjects" gives us {title, emphasis}; fall back to
  // the dashboard key if the route hasn't been mapped yet so the
  // header is never empty.
  const lookup = t(`page_titles.${key}`, { returnObjects: true });
  const pageTitle =
    lookup && typeof lookup === 'object' && lookup.title
      ? lookup
      : t('page_titles.dashboard', { returnObjects: true });

  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          {/* Mobile menu toggle */}
          <button
            onClick={() => document.dispatchEvent(new CustomEvent('toggleSidebar'))}
            className="menu-toggle mobile-only"
            title={t('common.open_menu')}
          >
            <Menu />
          </button>

          <div className="header-title-block">
            <div className="header-meta">
              <span className="header-meta-dot" />
              <span className="header-meta-text">
                {t('header.updated_at')} {formatTime(now, i18n.language)} · {formatDate(now, i18n.language)} · {t('header.market_status_open')}
              </span>
            </div>
            <h1 className="header-title">{renderTitle(pageTitle)}</h1>
          </div>
        </div>

        <div className="header-right">
          <div className="header-search">
            <Search className="header-search-icon" />
            <input
              type="text"
              placeholder={t('common.search_placeholder')}
              className="header-search-input"
              aria-label={t('common.search_placeholder')}
            />
            <span className="header-search-kbd">⌘K</span>
          </div>

          <NotificationBell />
          {alertSlot}

          <LanguageSwitcher />

          <button onClick={logout} className="logout-button" title={t('common.logout')}>
            <LogOut />
            <span className="logout-text">{t('common.logout')}</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
