import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  View,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

const BUTTON_SIZES = {
  small: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    fontSize: 14,
    iconSize: 16,
    minHeight: 36,
  },
  medium: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    fontSize: 16,
    iconSize: 20,
    minHeight: 44,
  },
  large: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    fontSize: 18,
    iconSize: 24,
    minHeight: 52,
  },
};

const Button = ({
  // Content
  title,
  icon,
  iconPosition = 'left',
  
  // Styling
  variant = 'filled', // filled, outlined, text, tonal
  size = 'medium',
  color,
  textColor,
  
  // State
  disabled = false,
  loading = false,
  
  // Interaction
  onPress,
  onLongPress,
  
  // Layout
  fullWidth = false,
  style,
  textStyle,
  
  // Accessibility
  accessibilityLabel,
  testID,
  
  ...props
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const buttonSize = BUTTON_SIZES[size];
  
  const getVariantStyles = () => {
    const baseColor = color || colors.primary;
    
    switch (variant) {
      case 'filled':
        return {
          backgroundColor: disabled ? colors.surfaceDisabled : baseColor,
          borderWidth: 0,
        };
      case 'outlined':
        return {
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderColor: disabled ? colors.outlineDisabled : baseColor,
        };
      case 'text':
        return {
          backgroundColor: 'transparent',
          borderWidth: 0,
        };
      case 'tonal':
        return {
          backgroundColor: disabled 
            ? colors.surfaceDisabled 
            : `${baseColor}20`, // 20% opacity
          borderWidth: 0,
        };
      default:
        return {};
    }
  };
  
  const getTextColor = () => {
    if (textColor) return textColor;
    if (disabled) return colors.onSurfaceDisabled;
    
    const baseColor = color || colors.primary;
    
    switch (variant) {
      case 'filled':
        return colors.onPrimary;
      case 'outlined':
      case 'text':
      case 'tonal':
        return baseColor;
      default:
        return colors.onPrimary;
    }\n  };\n  \n  const renderIcon = () => {\n    if (!icon || loading) return null;\n    \n    return (\n      <Ionicons\n        name={icon}\n        size={buttonSize.iconSize}\n        color={getTextColor()}\n        style={[\n          iconPosition === 'right' && { marginLeft: 8 },\n          iconPosition === 'left' && { marginRight: 8 },\n        ]}\n      />\n    );\n  };\n  \n  const renderContent = () => {\n    if (loading) {\n      return (\n        <ActivityIndicator\n          size={buttonSize.iconSize}\n          color={getTextColor()}\n        />\n      );\n    }\n    \n    const textElement = title && (\n      <Text\n        style={[\n          {\n            fontSize: buttonSize.fontSize,\n            fontWeight: '600',\n            color: getTextColor(),\n          },\n          textStyle,\n        ]}\n      >\n        {title}\n      </Text>\n    );\n    \n    if (!icon) {\n      return textElement;\n    }\n    \n    return (\n      <View style={styles.contentContainer}>\n        {iconPosition === 'left' && renderIcon()}\n        {textElement}\n        {iconPosition === 'right' && renderIcon()}\n      </View>\n    );\n  };\n  \n  return (\n    <TouchableOpacity\n      style={[\n        styles.button,\n        {\n          paddingVertical: buttonSize.paddingVertical,\n          paddingHorizontal: buttonSize.paddingHorizontal,\n          minHeight: buttonSize.minHeight,\n        },\n        getVariantStyles(),\n        fullWidth && styles.fullWidth,\n        disabled && styles.disabled,\n        style,\n      ]}\n      onPress={disabled || loading ? undefined : onPress}\n      onLongPress={disabled || loading ? undefined : onLongPress}\n      disabled={disabled || loading}\n      activeOpacity={0.7}\n      accessibilityLabel={accessibilityLabel || title}\n      testID={testID}\n      {...props}\n    >\n      {renderContent()}\n    </TouchableOpacity>\n  );\n};\n\n// Specialized button variants\nexport const PrimaryButton = (props) => (\n  <Button variant=\"filled\" {...props} />\n);\n\nexport const SecondaryButton = (props) => (\n  <Button variant=\"outlined\" {...props} />\n);\n\nexport const TextButton = (props) => (\n  <Button variant=\"text\" {...props} />\n);\n\nexport const TonalButton = (props) => (\n  <Button variant=\"tonal\" {...props} />\n);\n\n// Icon-only button\nexport const IconButton = ({\n  icon,\n  size = 'medium',\n  variant = 'text',\n  style,\n  ...props\n}) => {\n  const buttonSize = BUTTON_SIZES[size];\n  \n  return (\n    <Button\n      icon={icon}\n      variant={variant}\n      size={size}\n      style={[\n        {\n          width: buttonSize.minHeight,\n          height: buttonSize.minHeight,\n          paddingHorizontal: 0,\n        },\n        style,\n      ]}\n      {...props}\n    />\n  );\n};\n\n// Floating Action Button\nexport const FAB = ({\n  icon = 'add',\n  size = 'medium',\n  color,\n  style,\n  ...props\n}) => {\n  const { colors } = useTheme();\n  const styles = createStyles(colors);\n  const buttonSize = BUTTON_SIZES[size];\n  \n  const fabSize = size === 'small' ? 40 : size === 'large' ? 64 : 56;\n  \n  return (\n    <TouchableOpacity\n      style={[\n        styles.fab,\n        {\n          width: fabSize,\n          height: fabSize,\n          borderRadius: fabSize / 2,\n          backgroundColor: color || colors.primary,\n        },\n        style,\n      ]}\n      activeOpacity={0.8}\n      {...props}\n    >\n      <Ionicons\n        name={icon}\n        size={buttonSize.iconSize + 4}\n        color={colors.onPrimary}\n      />\n    </TouchableOpacity>\n  );\n};\n\n// Toggle Button\nexport const ToggleButton = ({\n  selected = false,\n  onToggle,\n  selectedColor,\n  unselectedColor,\n  children,\n  style,\n  ...props\n}) => {\n  const { colors } = useTheme();\n  \n  return (\n    <Button\n      variant={selected ? 'filled' : 'outlined'}\n      color={selected ? (selectedColor || colors.primary) : (unselectedColor || colors.outline)}\n      onPress={() => onToggle?.(!selected)}\n      style={[\n        selected && { borderColor: selectedColor || colors.primary },\n        style,\n      ]}\n      {...props}\n    >\n      {children}\n    </Button>\n  );\n};\n\nconst createStyles = (colors) =>\n  StyleSheet.create({\n    button: {\n      borderRadius: 8,\n      justifyContent: 'center',\n      alignItems: 'center',\n      flexDirection: 'row',\n      ...Platform.select({\n        ios: {\n          shadowColor: '#000',\n          shadowOffset: { width: 0, height: 1 },\n          shadowOpacity: 0.1,\n          shadowRadius: 2,\n        },\n        android: {\n          elevation: 2,\n        },\n      }),\n    },\n    contentContainer: {\n      flexDirection: 'row',\n      alignItems: 'center',\n      justifyContent: 'center',\n    },\n    fullWidth: {\n      alignSelf: 'stretch',\n    },\n    disabled: {\n      opacity: 0.6,\n      ...Platform.select({\n        ios: {\n          shadowOpacity: 0,\n        },\n        android: {\n          elevation: 0,\n        },\n      }),\n    },\n    fab: {\n      justifyContent: 'center',\n      alignItems: 'center',\n      ...Platform.select({\n        ios: {\n          shadowColor: '#000',\n          shadowOffset: { width: 0, height: 4 },\n          shadowOpacity: 0.3,\n          shadowRadius: 8,\n        },\n        android: {\n          elevation: 8,\n        },\n      }),\n    },\n  });\n\nexport default Button;"
},
{"old_string": "  };\n  \n  const renderIcon = () => {\n    if (!icon || loading) return null;\n    \n    return (\n      <Ionicons\n        name={icon}\n        size={buttonSize.iconSize}\n        color={getTextColor()}\n        style={[\n          iconPosition === 'right' && { marginLeft: 8 },\n          iconPosition === 'left' && { marginRight: 8 },\n        ]}\n      />\n    );\n  };\n  \n  const renderContent = () => {\n    if (loading) {\n      return (\n        <ActivityIndicator\n          size={buttonSize.iconSize}\n          color={getTextColor()}\n        />\n      );\n    }\n    \n    const textElement = title && (\n      <Text\n        style={[\n          {\n            fontSize: buttonSize.fontSize,\n            fontWeight: '600',\n            color: getTextColor(),\n          },\n          textStyle,\n        ]}\n      >\n        {title}\n      </Text>\n    );\n    \n    if (!icon) {\n      return textElement;\n    }\n    \n    return (\n      <View style={styles.contentContainer}>\n        {iconPosition === 'left' && renderIcon()}\n        {textElement}\n        {iconPosition === 'right' && renderIcon()}\n      </View>\n    );\n  };", "new_string": "  };\n  \n  const renderIcon = () => {\n    if (!icon || loading) return null;\n    \n    return (\n      <Ionicons\n        name={icon}\n        size={buttonSize.iconSize}\n        color={getTextColor()}\n        style={[\n          iconPosition === 'right' && { marginLeft: 8 },\n          iconPosition === 'left' && { marginRight: 8 },\n        ]}\n      />\n    );\n  };\n  \n  const renderContent = () => {\n    if (loading) {\n      return (\n        <ActivityIndicator\n          size={buttonSize.iconSize}\n          color={getTextColor()}\n        />\n      );\n    }\n    \n    const textElement = title && (\n      <Text\n        style={[\n          {\n            fontSize: buttonSize.fontSize,\n            fontWeight: '600',\n            color: getTextColor(),\n          },\n          textStyle,\n        ]}\n      >\n        {title}\n      </Text>\n    );\n    \n    if (!icon) {\n      return textElement;\n    }\n    \n    return (\n      <View style={styles.contentContainer}>\n        {iconPosition === 'left' && renderIcon()}\n        {textElement}\n        {iconPosition === 'right' && renderIcon()}\n      </View>\n    );\n  };"}]