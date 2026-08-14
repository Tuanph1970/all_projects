import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useLanguage, LANGUAGES, LANGUAGE_NAMES } from '@i18n';

/**
 * Language Toggle Component
 * Allows users to switch between English and Vietnamese
 */
const LanguageToggle = ({ style, compact = false }) => {
  const { language, toggleLanguage, t } = useLanguage();

  if (compact) {
    return (
      <TouchableOpacity
        style={[styles.compactContainer, style]}
        onPress={toggleLanguage}
        accessibilityLabel={t('language.selectLanguage')}
        accessibilityRole="button"
        testID="language-toggle-compact"
      >
        <Text style={styles.compactText}>
          {language === LANGUAGES.EN ? '🇺🇸 EN' : '🇻🇳 VI'}
        </Text>
      </TouchableOpacity>
    );
  }

  return (
    <View style={[styles.container, style]} testID="language-toggle">
      <Text style={styles.label}>{t('language.title')}</Text>
      <View style={styles.toggleContainer}>
        <TouchableOpacity
          style={[
            styles.option,
            language === LANGUAGES.EN && styles.optionActive,
          ]}
          onPress={() => language !== LANGUAGES.EN && toggleLanguage()}
          accessibilityLabel={LANGUAGE_NAMES[LANGUAGES.EN]}
          accessibilityRole="button"
          accessibilityState={{ selected: language === LANGUAGES.EN }}
          testID="language-toggle-en"
        >
          <Text style={styles.flag}>🇺🇸</Text>
          <Text
            style={[
              styles.optionText,
              language === LANGUAGES.EN && styles.optionTextActive,
            ]}
          >
            {LANGUAGE_NAMES[LANGUAGES.EN]}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.option,
            language === LANGUAGES.VI && styles.optionActive,
          ]}
          onPress={() => language !== LANGUAGES.VI && toggleLanguage()}
          accessibilityLabel={LANGUAGE_NAMES[LANGUAGES.VI]}
          accessibilityRole="button"
          accessibilityState={{ selected: language === LANGUAGES.VI }}
          testID="language-toggle-vi"
        >
          <Text style={styles.flag}>🇻🇳</Text>
          <Text
            style={[
              styles.optionText,
              language === LANGUAGES.VI && styles.optionTextActive,
            ]}
          >
            {LANGUAGE_NAMES[LANGUAGES.VI]}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

/**
 * Language Switch Button - Simple button version
 */
export const LanguageSwitchButton = ({ style }) => {
  const { language, toggleLanguage } = useLanguage();

  return (
    <TouchableOpacity
      style={[styles.switchButton, style]}
      onPress={toggleLanguage}
      accessibilityLabel="Switch language"
      accessibilityRole="button"
      testID="language-switch-button"
    >
      <View style={styles.switchContent}>
        <Text style={styles.switchFlag}>
          {language === LANGUAGES.EN ? '🇺🇸' : '🇻🇳'}
        </Text>
        <Text style={styles.switchText}>
          {language === LANGUAGES.EN ? 'EN' : 'VI'}
        </Text>
      </View>
    </TouchableOpacity>
  );
};

/**
 * Language Menu Item - For use in settings/profile menus
 */
export const LanguageMenuItem = ({ onPress, style }) => {
  const { language, t } = useLanguage();

  return (
    <TouchableOpacity
      style={[styles.menuItem, style]}
      onPress={onPress}
      accessibilityLabel={t('language.selectLanguage')}
      accessibilityRole="button"
      testID="language-menu-item"
    >
      <View style={styles.menuItemLeft}>
        <Text style={styles.menuItemIcon}>🌐</Text>
        <View>
          <Text style={styles.menuItemTitle}>{t('language.title')}</Text>
          <Text style={styles.menuItemSubtitle}>
            {LANGUAGE_NAMES[language]}
          </Text>
        </View>
      </View>
      <Text style={styles.menuItemArrow}>›</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginBottom: 12,
  },
  toggleContainer: {
    flexDirection: 'row',
    backgroundColor: '#f5f5f5',
    borderRadius: 12,
    padding: 4,
  },
  option: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
  },
  optionActive: {
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  flag: {
    fontSize: 20,
    marginRight: 8,
  },
  optionText: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
  },
  optionTextActive: {
    color: '#333',
    fontWeight: '600',
  },
  // Compact styles
  compactContainer: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
  },
  compactText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  // Switch button styles
  switchButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#fff',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  switchContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  switchFlag: {
    fontSize: 16,
    marginRight: 4,
  },
  switchText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
  },
  // Menu item styles
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  menuItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  menuItemIcon: {
    fontSize: 24,
    marginRight: 16,
  },
  menuItemTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  menuItemSubtitle: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
  menuItemArrow: {
    fontSize: 24,
    color: '#ccc',
  },
});

export default LanguageToggle;
