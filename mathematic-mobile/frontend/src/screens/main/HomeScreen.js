import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

const HomeScreen = ({ navigation }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Good Morning!</Text>
          <Text style={styles.subtitle}>Ready to solve some math problems?</Text>
        </View>

        <View style={styles.quickActions}>
          <TouchableOpacity
            style={styles.cameraCard}
            onPress={() => navigation.navigate('Camera')}
          >
            <View style={styles.cardIcon}>
              <Ionicons name="camera" size={32} color="#FFFFFF" />
            </View>
            <Text style={styles.cardTitle}>Scan Problem</Text>
            <Text style={styles.cardDescription}>Take a photo to solve instantly</Text>
          </TouchableOpacity>

          <View style={styles.actionRow}>
            <TouchableOpacity
              style={styles.actionCard}
              onPress={() => navigation.navigate('Problems')}
            >
              <Ionicons name="library-outline" size={24} color={colors.primary} />
              <Text style={styles.actionText}>My Problems</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.actionCard}
              onPress={() => navigation.navigate('Profile')}
            >
              <Ionicons name="person-outline" size={24} color={colors.primary} />
              <Text style={styles.actionText}>Profile</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Activity</Text>
          <View style={styles.placeholder}>
            <Ionicons name="document-outline" size={48} color={colors.textSecondary} />
            <Text style={styles.placeholderText}>No recent problems yet</Text>
            <Text style={styles.placeholderSubtext}>Start by scanning your first math problem!</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    scrollView: {
      flex: 1,
    },
    header: {
      padding: 24,
      paddingTop: 12,
    },
    greeting: {
      fontSize: 28,
      fontWeight: 'bold',
      color: colors.text,
      marginBottom: 4,
    },
    subtitle: {
      fontSize: 16,
      color: colors.textSecondary,
    },
    quickActions: {
      padding: 24,
      paddingTop: 0,
    },
    cameraCard: {
      backgroundColor: colors.primary,
      borderRadius: 16,
      padding: 24,
      alignItems: 'center',
      marginBottom: 16,
    },
    cardIcon: {
      width: 64,
      height: 64,
      borderRadius: 32,
      backgroundColor: 'rgba(255, 255, 255, 0.2)',
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 16,
    },
    cardTitle: {
      fontSize: 20,
      fontWeight: 'bold',
      color: '#FFFFFF',
      marginBottom: 4,
    },
    cardDescription: {
      fontSize: 14,
      color: 'rgba(255, 255, 255, 0.8)',
      textAlign: 'center',
    },
    actionRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
    },
    actionCard: {
      flex: 1,
      backgroundColor: colors.surface,
      borderRadius: 12,
      padding: 20,
      alignItems: 'center',
      marginHorizontal: 4,
    },
    actionText: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.text,
      marginTop: 8,
    },
    section: {
      padding: 24,
      paddingTop: 8,
    },
    sectionTitle: {
      fontSize: 20,
      fontWeight: 'bold',
      color: colors.text,
      marginBottom: 16,
    },
    placeholder: {
      backgroundColor: colors.surface,
      borderRadius: 12,
      padding: 32,
      alignItems: 'center',
    },
    placeholderText: {
      fontSize: 16,
      fontWeight: '600',
      color: colors.textSecondary,
      marginTop: 12,
      marginBottom: 4,
    },
    placeholderSubtext: {
      fontSize: 14,
      color: colors.textSecondary,
      textAlign: 'center',
    },
  });

export default HomeScreen;