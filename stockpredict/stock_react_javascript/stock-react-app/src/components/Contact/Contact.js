// src/components/Contact/Contact.js
import React from 'react';
import { Mail } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const Contact = () => {
  const { t } = useTranslation();
  const email = t('contact.email');
  return (
    <footer className="dashboard-footer">
      <span className="dashboard-footer-author">{t('contact.author')}</span>
      <span className="dashboard-footer-sep">|</span>
      <a href={`mailto:${email}`} className="dashboard-footer-link">
        <Mail />
        {email}
      </a>
    </footer>
  );
};

export default Contact;
