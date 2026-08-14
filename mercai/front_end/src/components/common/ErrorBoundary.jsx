import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Button, Card } from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';

/**
 * ErrorBoundary Component
 * Catches JavaScript errors in child components and displays a fallback UI
 * instead of crashing the entire app
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render shows the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging
    console.error('ErrorBoundary caught an error:', error);
    console.error('Error Info:', errorInfo);

    // Store error details in state
    this.setState({
      error,
      errorInfo,
    });

    // You can also log the error to an error reporting service here
    // Example: logErrorToService(error, errorInfo);
  }

  handleReset = () => {
    // Reset error state to try rendering the component again
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    // Call optional onReset callback if provided
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      // Render custom fallback UI
      return (
        <ScrollView style={styles.container}>
          <View style={styles.content}>
            <Card style={styles.errorCard}>
              <Card.Content style={styles.errorContent}>
                <Text style={styles.errorIcon}>⚠️</Text>
                <Text style={styles.errorTitle}>
                  Đã xảy ra lỗi
                </Text>
                <Text style={styles.errorMessage}>
                  Ứng dụng gặp sự cố không mong muốn. Vui lòng thử lại.
                </Text>

                {/* Show error details in development mode */}
                {__DEV__ && this.state.error && (
                  <View style={styles.errorDetails}>
                    <Text style={styles.errorDetailsTitle}>
                      Chi tiết lỗi (Development mode):
                    </Text>
                    <Text style={styles.errorDetailsText}>
                      {this.state.error.toString()}
                    </Text>
                    {this.state.errorInfo && (
                      <Text style={styles.errorStackText}>
                        {this.state.errorInfo.componentStack}
                      </Text>
                    )}
                  </View>
                )}

                <View style={styles.buttonContainer}>
                  <Button
                    mode="contained"
                    onPress={this.handleReset}
                    style={styles.retryButton}
                  >
                    Thử lại
                  </Button>
                </View>
              </Card.Content>
            </Card>
          </View>
        </ScrollView>
      );
    }

    // No error, render children normally
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.large,
    minHeight: '100%',
  },
  errorCard: {
    width: '100%',
    maxWidth: 500,
  },
  errorContent: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  errorIcon: {
    fontSize: 64,
    marginBottom: spacing.large,
  },
  errorTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.bold,
    color: colors.error,
    marginBottom: spacing.medium,
    textAlign: 'center',
  },
  errorMessage: {
    fontSize: typography.sizes.medium,
    color: colors.text,
    textAlign: 'center',
    marginBottom: spacing.large,
    paddingHorizontal: spacing.medium,
  },
  errorDetails: {
    width: '100%',
    marginTop: spacing.large,
    padding: spacing.medium,
    backgroundColor: colors.errorContainer,
    borderRadius: 8,
  },
  errorDetailsTitle: {
    fontSize: typography.sizes.medium,
    fontWeight: typography.weights.semibold,
    color: colors.error,
    marginBottom: spacing.small,
  },
  errorDetailsText: {
    fontSize: typography.sizes.small,
    color: colors.onErrorContainer,
    fontFamily: 'monospace',
    marginBottom: spacing.small,
  },
  errorStackText: {
    fontSize: typography.sizes.small,
    color: colors.outline,
    fontFamily: 'monospace',
  },
  buttonContainer: {
    marginTop: spacing.large,
    width: '100%',
    alignItems: 'center',
  },
  retryButton: {
    minWidth: 150,
  },
});

export default ErrorBoundary;
