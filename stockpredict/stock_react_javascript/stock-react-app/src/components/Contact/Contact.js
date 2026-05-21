// src/components/Contact/Contact.js
import React from 'react';
import { Mail } from 'lucide-react';

const Contact = () => {
  return (
    <footer className="dashboard-footer">
      <span className="dashboard-footer-author">Pham Hoang Tuan</span>
      <span className="dashboard-footer-sep">|</span>
      <a
        href="mailto:tuanph1970@gmail.com"
        className="dashboard-footer-link"
      >
        <Mail />
        tuanph1970@gmail.com
      </a>
    </footer>
  );
};

export default Contact;
