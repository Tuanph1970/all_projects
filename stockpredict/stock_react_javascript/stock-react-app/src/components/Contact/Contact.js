// src/components/Contact/Contact.js
import React from 'react';
import { Mail } from 'lucide-react';

const Contact = () => {
  return (
    <footer className="bg-gray-800 text-gray-300 py-4 mt-6 rounded-lg">
      <div className="flex items-center justify-center gap-6 text-sm">
        <span className="font-medium text-white">Pham Hoang Tuan</span>
        <span className="text-gray-500">|</span>
        <a
          href="mailto:tuanph1970@gmail.com"
          className="flex items-center gap-2 hover:text-white transition-colors"
        >
          <Mail className="w-4 h-4" />
          tuanph1970@gmail.com
        </a>
      </div>
    </footer>
  );
};

export default Contact;
