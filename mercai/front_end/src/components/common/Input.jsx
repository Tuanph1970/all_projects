import React, { forwardRef } from 'react';
import { StyleSheet, View } from 'react-native';
import { TextInput, HelperText } from 'react-native-paper';
import { colors, spacing, borderRadius } from '../../constants/theme.js';

export const Input  = forwardRef(({
  error,
  errorMessage,
  style,
  containerStyle,
  testID,
  ...props
}, ref) => {
  // Generate error testID from input testID
  const errorTestID = testID ? `${testID}-error` : undefined;

  return (
    <View style={containerStyle}>
      <TextInput
        ref={ref}
        testID={testID}
        style={[styles.input, style]}
        error={error}
        theme={{
          colors: {
            primary: colors.primary,
            error: colors.error,
          }
        }}
        {...props}
      />
      {error && errorMessage && (
        <HelperText type="error" visible={error} testID={errorTestID}>
          {errorMessage}
        </HelperText>
      )}
    </View>
  );
});

Input.displayName = 'Input';

const styles = StyleSheet.create({
  input: {
    marginVertical: spacing.xs,
  },
});