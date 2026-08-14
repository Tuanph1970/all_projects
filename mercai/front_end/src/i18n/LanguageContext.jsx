import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { translations, LANGUAGES } from './translations';

const LANGUAGE_STORAGE_KEY = '@app_language';

const LanguageContext = createContext();

/**
 * Helper function to get nested translation value
 * @param {Object} obj - Translation object
 * @param {string} path - Dot-separated path (e.g., 'auth.welcomeBack')
 * @returns {string} - Translation value or path if not found
 */
const getNestedValue = (obj, path) => {
  const keys = path.split('.');
  let result = obj;

  for (const key of keys) {
    if (result && typeof result === 'object' && key in result) {
      result = result[key];
    } else {
      return path; // Return the path if translation not found
    }
  }

  return result;
};

/**
 * Replace placeholders in translation string
 * @param {string} str - Translation string with placeholders like {name}
 * @param {Object} params - Object with values to replace placeholders
 * @returns {string} - String with placeholders replaced
 */
const interpolate = (str, params) => {
  if (!params || typeof str !== 'string') return str;

  return str.replace(/\{(\w+)\}/g, (match, key) => {
    return params[key] !== undefined ? params[key] : match;
  });
};

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(LANGUAGES.VI);
  const [isLoading, setIsLoading] = useState(true);

  // Load saved language preference on mount
  useEffect(() => {
    const loadLanguage = async () => {
      try {
        const savedLanguage = await AsyncStorage.getItem(LANGUAGE_STORAGE_KEY);
        if (savedLanguage && (savedLanguage === LANGUAGES.EN || savedLanguage === LANGUAGES.VI)) {
          setLanguage(savedLanguage);
        }
      } catch (error) {
        console.error('Error loading language preference:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadLanguage();
  }, []);

  // Change language and persist to storage
  const changeLanguage = useCallback(async (newLanguage) => {
    if (newLanguage !== LANGUAGES.EN && newLanguage !== LANGUAGES.VI) {
      console.warn('Invalid language:', newLanguage);
      return;
    }

    try {
      await AsyncStorage.setItem(LANGUAGE_STORAGE_KEY, newLanguage);
      setLanguage(newLanguage);
    } catch (error) {
      console.error('Error saving language preference:', error);
    }
  }, []);

  // Toggle between English and Vietnamese
  const toggleLanguage = useCallback(async () => {
    const newLanguage = language === LANGUAGES.EN ? LANGUAGES.VI : LANGUAGES.EN;
    await changeLanguage(newLanguage);
  }, [language, changeLanguage]);

  /**
   * Translation function
   * @param {string} key - Dot-separated translation key (e.g., 'auth.welcomeBack')
   * @param {Object} params - Optional parameters for interpolation
   * @returns {string} - Translated string
   */
  const t = useCallback((key, params) => {
    const translationObj = translations[language] || translations[LANGUAGES.EN];
    const translation = getNestedValue(translationObj, key);

    if (typeof translation !== 'string') {
      console.warn(`Translation not found for key: ${key}`);
      return key;
    }

    return interpolate(translation, params);
  }, [language]);

  /**
   * Format currency based on current language
   * @param {number} value - Amount to format
   * @returns {string} - Formatted currency string
   */
  const formatCurrency = useCallback((value) => {
    if (value === undefined || value === null) {
      return language === LANGUAGES.VI ? '0 ₫' : '$0.00';
    }

    if (language === LANGUAGES.VI) {
      // Vietnamese: 1.234.567 ₫
      return `${value.toLocaleString('vi-VN')} ₫`;
    } else {
      // English: $1,234.56
      return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
  }, [language]);

  const value = {
    language,
    isEnglish: language === LANGUAGES.EN,
    isVietnamese: language === LANGUAGES.VI,
    changeLanguage,
    toggleLanguage,
    t,
    formatCurrency,
    isLoading,
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};

/**
 * Hook to access language context
 * @returns {Object} Language context value
 */
export const useLanguage = () => {
  const context = useContext(LanguageContext);

  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }

  return context;
};

/**
 * Hook to get translation function only (for performance)
 * @returns {Function} Translation function
 */
export const useTranslation = () => {
  const { t } = useLanguage();
  return t;
};

export default LanguageContext;
