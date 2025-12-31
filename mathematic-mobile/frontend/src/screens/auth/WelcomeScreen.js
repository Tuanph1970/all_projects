import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../../hooks/useTheme';

const { width, height } = Dimensions.get('window');

const WelcomeScreen = ({ navigation }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);

  const handleLogin = () => {
    navigation.navigate('Login');
  };

  const handleRegister = () => {
    navigation.navigate('Register');
  };

  return (
    <SafeAreaView style={styles.container}>
      <LinearGradient
        colors={[colors.primary, colors.primaryDark]}
        style={styles.gradient}
      >
        <View style={styles.content}>
          {/* Logo/Icon placeholder */}
          <View style={styles.logoContainer}>
            <View style={styles.logoPlaceholder}>
              <Text style={styles.logoText}>📱</Text>
            </View>
            <Text style={styles.appName}>Mathematics Solver</Text>
            <Text style={styles.tagline}>
              Solve math problems instantly with AI
            </Text>
          </View>

          {/* Features */}
          <View style={styles.featuresContainer}>
            <View style={styles.feature}>
              <Text style={styles.featureIcon}>📸</Text>
              <Text style={styles.featureText}>Snap a photo of any math problem</Text>
            </View>
            <View style={styles.feature}>
              <Text style={styles.featureIcon}>🧠</Text>
              <Text style={styles.featureText}>Get step-by-step solutions</Text>
            </View>
            <View style={styles.feature}>
              <Text style={styles.featureIcon}>💡</Text>
              <Text style={styles.featureText}>Learn with detailed explanations</Text>
            </View>
          </View>

          {/* Buttons */}
          <View style={styles.buttonsContainer}>
            <TouchableOpacity style={styles.primaryButton} onPress={handleLogin}>
              <Text style={styles.primaryButtonText}>Sign In</Text>
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.secondaryButton} onPress={handleRegister}>
              <Text style={styles.secondaryButtonText}>Create Account</Text>
            </TouchableOpacity>
          </View>
        </View>
      </LinearGradient>
    </SafeAreaView>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
    },
    gradient: {
      flex: 1,
    },
    content: {
      flex: 1,
      justifyContent: 'space-between',
      padding: 24,
      paddingTop: height * 0.1,
      paddingBottom: 40,
    },
    logoContainer: {
      alignItems: 'center',
    },
    logoPlaceholder: {
      width: 100,
      height: 100,
      borderRadius: 50,
      backgroundColor: 'rgba(255, 255, 255, 0.2)',
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 24,
    },
    logoText: {
      fontSize: 40,
    },
    appName: {
      fontSize: 28,
      fontWeight: 'bold',
      color: '#FFFFFF',
      textAlign: 'center',
      marginBottom: 8,
    },
    tagline: {
      fontSize: 16,
      color: 'rgba(255, 255, 255, 0.8)',
      textAlign: 'center',
    },
    featuresContainer: {
      flex: 1,
      justifyContent: 'center',
      paddingVertical: 40,
    },
    feature: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 24,
      paddingHorizontal: 16,
    },
    featureIcon: {
      fontSize: 24,
      marginRight: 16,
    },
    featureText: {
      flex: 1,
      fontSize: 16,
      color: '#FFFFFF',
      lineHeight: 22,
    },
    buttonsContainer: {
      width: '100%',
    },
    primaryButton: {
      backgroundColor: '#FFFFFF',
      paddingVertical: 16,
      borderRadius: 12,
      marginBottom: 16,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
      elevation: 3,
    },
    primaryButtonText: {
      color: colors.primary,
      fontSize: 18,
      fontWeight: '600',
      textAlign: 'center',
    },
    secondaryButton: {
      backgroundColor: 'transparent',
      paddingVertical: 16,
      borderRadius: 12,
      borderWidth: 2,
      borderColor: '#FFFFFF',
    },
    secondaryButtonText: {
      color: '#FFFFFF',
      fontSize: 18,
      fontWeight: '600',
      textAlign: 'center',
    },
  });

export default WelcomeScreen;