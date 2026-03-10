import React from 'react';
import { View, Text, TouchableOpacity, Alert, StyleSheet, ScrollView } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { logoutAPI } from '../api/auth';
import { deleteAccount, deleteUserData } from '../api/data';
import { colors, spacing, radius } from '../theme/theme';

export default function SettingsScreen() {
  const { username, logout } = useAuth();

  async function handleLogout() {
    try {
      await logoutAPI();
    } catch (e) {
      // Proceed with local logout even if the API call fails
    }
    await logout();
  }

  function handleDeleteData() {
    Alert.alert(
      'Delete My Data',
      'This will delete all your submitted questionnaire data but keep your account. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Data',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteUserData();
              Alert.alert('Done', 'Your questionnaire data has been deleted.');
            } catch (e) {
              Alert.alert('Error', 'Failed to delete data. Please try again.');
            }
          },
        },
      ]
    );
  }

  function handleDeleteAccount() {
    Alert.alert(
      'Delete Account',
      'This will permanently delete your account and ALL your data. This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Everything',
          style: 'destructive',
          onPress: () => {
            // Second confirmation for account deletion
            Alert.alert(
              'Are you sure?',
              'This is your last chance. All data will be permanently erased.',
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Yes, Delete My Account',
                  style: 'destructive',
                  onPress: async () => {
                    try {
                      await deleteAccount();
                      await logout();
                    } catch (e) {
                      Alert.alert('Error', 'Failed to delete account. Please try again.');
                    }
                  },
                },
              ]
            );
          },
        },
      ]
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{(username || '?')[0].toUpperCase()}</Text>
        </View>
        <Text style={styles.username}>{username}</Text>
      </View>

      <Text style={styles.sectionLabel}>DATA MANAGEMENT</Text>

      <TouchableOpacity style={styles.card} onPress={handleDeleteData}>
        <Text style={styles.cardTitle}>Delete My Data</Text>
        <Text style={styles.cardSubtitle}>
          Remove all questionnaire submissions while keeping your account active
        </Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.dangerCard} onPress={handleDeleteAccount}>
        <Text style={styles.dangerTitle}>Delete Account</Text>
        <Text style={styles.dangerSubtitle}>
          Right to Erasure (GDPR Art. 17) - Permanently delete your account and all associated data
        </Text>
      </TouchableOpacity>

      <Text style={styles.sectionLabel}>SESSION</Text>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    padding: spacing.lg,
  },
  profileCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.lg,
    alignItems: 'center',
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  avatarText: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  username: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
  },
  sectionLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.textTertiary,
    letterSpacing: 1,
    marginBottom: spacing.sm,
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.warning,
    marginBottom: 4,
  },
  cardSubtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  dangerCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.dangerLight,
  },
  dangerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.danger,
    marginBottom: 4,
  },
  dangerSubtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  logoutBtn: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  logoutText: {
    color: colors.textSecondary,
    fontSize: 16,
    fontWeight: '600',
  },
});
