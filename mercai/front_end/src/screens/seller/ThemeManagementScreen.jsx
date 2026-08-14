import React, { useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Alert, TouchableOpacity } from 'react-native';
import {
  Text,
  Appbar,
  Card,
  Button,
  TextInput,
  ActivityIndicator,
  Chip,
  Divider
} from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerProfileService from '../../services/sellerProfileService.js';

const DEFAULT_THEME = {
  theme_name: 'My Store Theme',
  primary_color: '#007bff',
  secondary_color: '#6c757d',
  accent_color: '#28a745',
  background_color: '#ffffff',
  text_color: '#333333',
  heading_font: 'Arial, sans-serif',
  body_font: 'Arial, sans-serif',
  layout_style: 'modern',
  header_style: 'default',
  footer_style: 'default',
};

const COLOR_PRESETS = [
  { name: 'Blue', primary: '#007bff', secondary: '#6c757d', accent: '#28a745' },
  { name: 'Green', primary: '#28a745', secondary: '#6c757d', accent: '#007bff' },
  { name: 'Purple', primary: '#6f42c1', secondary: '#495057', accent: '#fd7e14' },
  { name: 'Red', primary: '#dc3545', secondary: '#6c757d', accent: '#ffc107' },
  { name: 'Teal', primary: '#20c997', secondary: '#495057', accent: '#e83e8c' },
  { name: 'Orange', primary: '#fd7e14', secondary: '#6c757d', accent: '#007bff' },
];

const LAYOUT_STYLES = ['modern', 'classic', 'minimal', 'bold'];
const HEADER_STYLES = ['default', 'centered', 'sidebar', 'transparent'];
const FOOTER_STYLES = ['default', 'minimal', 'extended', 'centered'];

export const ThemeManagementScreen = () => {
  const navigation = useNavigation();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasExistingTheme, setHasExistingTheme] = useState(false);
  const [themeForm, setThemeForm] = useState(DEFAULT_THEME);

  // Fetch current theme on mount and focus
  const fetchTheme = useCallback(async () => {
    try {
      setLoading(true);
      const theme = await sellerProfileService.getTheme();
      if (theme && Object.keys(theme).length > 0) {
        setThemeForm({
          theme_name: theme.theme_name || DEFAULT_THEME.theme_name,
          primary_color: theme.primary_color || DEFAULT_THEME.primary_color,
          secondary_color: theme.secondary_color || DEFAULT_THEME.secondary_color,
          accent_color: theme.accent_color || DEFAULT_THEME.accent_color,
          background_color: theme.background_color || DEFAULT_THEME.background_color,
          text_color: theme.text_color || DEFAULT_THEME.text_color,
          heading_font: theme.heading_font || DEFAULT_THEME.heading_font,
          body_font: theme.body_font || DEFAULT_THEME.body_font,
          layout_style: theme.layout_style || DEFAULT_THEME.layout_style,
          header_style: theme.header_style || DEFAULT_THEME.header_style,
          footer_style: theme.footer_style || DEFAULT_THEME.footer_style,
        });
        setHasExistingTheme(true);
      } else {
        setHasExistingTheme(false);
      }
    } catch (error) {
      console.log('Failed to fetch theme:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchTheme();
    }, [fetchTheme])
  );

  const handleSaveTheme = async () => {
    if (!themeForm.theme_name.trim()) {
      Alert.alert('Validation Error', 'Theme name is required');
      return;
    }

    setSaving(true);
    try {
      await sellerProfileService.saveTheme(themeForm);
      setHasExistingTheme(true);
      Alert.alert('Success', 'Theme saved successfully');
    } catch (error) {
      Alert.alert('Error', error.response?.data?.detail || error.message || 'Failed to save theme');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTheme = () => {
    Alert.alert(
      'Delete Theme',
      'Are you sure you want to delete your store theme?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await sellerProfileService.deleteTheme();
              setThemeForm(DEFAULT_THEME);
              setHasExistingTheme(false);
              Alert.alert('Success', 'Theme deleted successfully');
            } catch (error) {
              Alert.alert('Error', error.response?.data?.detail || error.message || 'Failed to delete theme');
            }
          }
        }
      ]
    );
  };

  const handleResetToDefault = () => {
    Alert.alert(
      'Reset Theme',
      'Reset all values to default?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          onPress: () => setThemeForm(DEFAULT_THEME)
        }
      ]
    );
  };

  const applyColorPreset = (preset) => {
    setThemeForm(prev => ({
      ...prev,
      primary_color: preset.primary,
      secondary_color: preset.secondary,
      accent_color: preset.accent,
    }));
  };

  const updateField = (field, value) => {
    setThemeForm(prev => ({ ...prev, [field]: value }));
  };

  const renderColorPicker = (label, field, value) => (
    <View style={styles.colorPickerContainer}>
      <Text style={styles.colorLabel}>{label}</Text>
      <View style={styles.colorInputRow}>
        <View style={[styles.colorPreview, { backgroundColor: value }]} />
        <TextInput
          value={value}
          onChangeText={(text) => updateField(field, text)}
          style={styles.colorInput}
          mode="outlined"
          placeholder="#000000"
          maxLength={7}
          testID={`${field}-input`}
        />
      </View>
    </View>
  );

  const renderStyleSelector = (label, field, options, value) => (
    <View style={styles.selectorContainer}>
      <Text style={styles.selectorLabel}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.chipRow}>
          {options.map((option) => (
            <Chip
              key={option}
              selected={value === option}
              onPress={() => updateField(field, option)}
              style={styles.chip}
              testID={`${field}-${option}`}
            >
              {option.charAt(0).toUpperCase() + option.slice(1)}
            </Chip>
          ))}
        </View>
      </ScrollView>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title="Theme Management" />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading theme...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="back-button" />
        <Appbar.Content title="Theme Management" />
        <Appbar.Action
          icon="content-save"
          onPress={handleSaveTheme}
          disabled={saving}
          testID="save-button"
        />
      </Appbar.Header>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Info Card */}
        <Card style={styles.infoCard}>
          <Card.Content>
            <Text style={styles.infoTitle}>Store Theme</Text>
            <Text style={styles.infoText}>
              Customize your store's appearance. These colors and styles will be displayed to your customers.
            </Text>
          </Card.Content>
        </Card>

        {/* Theme Name */}
        <Card style={styles.card}>
          <Card.Title title="Theme Name" />
          <Card.Content>
            <TextInput
              value={themeForm.theme_name}
              onChangeText={(text) => updateField('theme_name', text)}
              style={styles.input}
              mode="outlined"
              placeholder="Enter theme name"
              testID="theme-name-input"
            />
          </Card.Content>
        </Card>

        {/* Color Presets */}
        <Card style={styles.card}>
          <Card.Title title="Quick Color Presets" />
          <Card.Content>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <View style={styles.presetRow}>
                {COLOR_PRESETS.map((preset) => (
                  <TouchableOpacity
                    key={preset.name}
                    style={styles.presetButton}
                    onPress={() => applyColorPreset(preset)}
                    testID={`preset-${preset.name.toLowerCase()}`}
                  >
                    <View style={styles.presetColors}>
                      <View style={[styles.presetSwatch, { backgroundColor: preset.primary }]} />
                      <View style={[styles.presetSwatch, { backgroundColor: preset.secondary }]} />
                      <View style={[styles.presetSwatch, { backgroundColor: preset.accent }]} />
                    </View>
                    <Text style={styles.presetName}>{preset.name}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>
          </Card.Content>
        </Card>

        {/* Custom Colors */}
        <Card style={styles.card}>
          <Card.Title title="Custom Colors" />
          <Card.Content>
            {renderColorPicker('Primary Color', 'primary_color', themeForm.primary_color)}
            {renderColorPicker('Secondary Color', 'secondary_color', themeForm.secondary_color)}
            {renderColorPicker('Accent Color', 'accent_color', themeForm.accent_color)}
            {renderColorPicker('Background Color', 'background_color', themeForm.background_color)}
            {renderColorPicker('Text Color', 'text_color', themeForm.text_color)}
          </Card.Content>
        </Card>

        {/* Color Preview */}
        <Card style={styles.card}>
          <Card.Title title="Color Preview" />
          <Card.Content>
            <View style={styles.previewContainer}>
              <View style={[styles.previewBox, { backgroundColor: themeForm.background_color }]}>
                <Text style={[styles.previewTitle, { color: themeForm.primary_color }]}>
                  Store Title
                </Text>
                <Text style={[styles.previewText, { color: themeForm.text_color }]}>
                  This is how your text will look.
                </Text>
                <View style={[styles.previewButton, { backgroundColor: themeForm.primary_color }]}>
                  <Text style={styles.previewButtonText}>Primary Button</Text>
                </View>
                <View style={[styles.previewButton, { backgroundColor: themeForm.accent_color }]}>
                  <Text style={styles.previewButtonText}>Accent Button</Text>
                </View>
              </View>
            </View>
          </Card.Content>
        </Card>

        {/* Layout Settings */}
        <Card style={styles.card}>
          <Card.Title title="Layout Settings" />
          <Card.Content>
            {renderStyleSelector('Layout Style', 'layout_style', LAYOUT_STYLES, themeForm.layout_style)}
            {renderStyleSelector('Header Style', 'header_style', HEADER_STYLES, themeForm.header_style)}
            {renderStyleSelector('Footer Style', 'footer_style', FOOTER_STYLES, themeForm.footer_style)}
          </Card.Content>
        </Card>

        {/* Typography */}
        <Card style={styles.card}>
          <Card.Title title="Typography" />
          <Card.Content>
            <TextInput
              label="Heading Font"
              value={themeForm.heading_font}
              onChangeText={(text) => updateField('heading_font', text)}
              style={styles.input}
              mode="outlined"
              testID="heading-font-input"
            />
            <TextInput
              label="Body Font"
              value={themeForm.body_font}
              onChangeText={(text) => updateField('body_font', text)}
              style={styles.input}
              mode="outlined"
              testID="body-font-input"
            />
          </Card.Content>
        </Card>

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <Button
            mode="contained"
            onPress={handleSaveTheme}
            style={styles.saveButton}
            loading={saving}
            disabled={saving}
            icon="content-save"
            testID="save-theme-button"
          >
            Save Theme
          </Button>

          <Button
            mode="outlined"
            onPress={handleResetToDefault}
            style={styles.resetButton}
            icon="refresh"
            testID="reset-theme-button"
          >
            Reset to Default
          </Button>

          {hasExistingTheme && (
            <Button
              mode="outlined"
              onPress={handleDeleteTheme}
              style={styles.deleteButton}
              textColor={colors.error}
              icon="delete"
              testID="delete-theme-button"
            >
              Delete Theme
            </Button>
          )}
        </View>

        <View style={styles.bottomSpacing} />
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    backgroundColor: colors.surface,
    elevation: 2,
  },
  content: {
    flex: 1,
    padding: spacing.md,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.textSecondary,
  },
  infoCard: {
    marginBottom: spacing.md,
    borderRadius: 12,
    backgroundColor: colors.primaryLight || '#e3f2fd',
  },
  infoTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: 'bold',
    marginBottom: spacing.xs,
  },
  infoText: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
  },
  card: {
    marginBottom: spacing.md,
    borderRadius: 12,
  },
  input: {
    marginBottom: spacing.sm,
  },
  presetRow: {
    flexDirection: 'row',
    paddingVertical: spacing.sm,
  },
  presetButton: {
    alignItems: 'center',
    marginRight: spacing.md,
    padding: spacing.sm,
    borderRadius: 8,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  presetColors: {
    flexDirection: 'row',
    marginBottom: spacing.xs,
  },
  presetSwatch: {
    width: 24,
    height: 24,
    borderRadius: 4,
    marginHorizontal: 2,
  },
  presetName: {
    fontSize: typography.sizes.sm,
  },
  colorPickerContainer: {
    marginBottom: spacing.md,
  },
  colorLabel: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  colorInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  colorPreview: {
    width: 44,
    height: 44,
    borderRadius: 8,
    marginRight: spacing.sm,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  colorInput: {
    flex: 1,
  },
  previewContainer: {
    borderRadius: 8,
    overflow: 'hidden',
  },
  previewBox: {
    padding: spacing.md,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  previewTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: 'bold',
    marginBottom: spacing.sm,
  },
  previewText: {
    fontSize: typography.sizes.md,
    marginBottom: spacing.md,
  },
  previewButton: {
    padding: spacing.sm,
    borderRadius: 4,
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  previewButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  selectorContainer: {
    marginBottom: spacing.md,
  },
  selectorLabel: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  chipRow: {
    flexDirection: 'row',
    paddingVertical: spacing.xs,
  },
  chip: {
    marginRight: spacing.xs,
  },
  actionButtons: {
    marginTop: spacing.sm,
  },
  saveButton: {
    marginBottom: spacing.sm,
    paddingVertical: spacing.xs,
  },
  resetButton: {
    marginBottom: spacing.sm,
  },
  deleteButton: {
    borderColor: colors.error,
  },
  bottomSpacing: {
    height: spacing.xl,
  },
});

export default ThemeManagementScreen;
