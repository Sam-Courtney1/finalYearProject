import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useAuth } from '../context/AuthContext';
import MenuCard from '../components/MenuCard';
import { colors, spacing } from '../theme/theme';

export default function HomeScreen({ navigation }) {
  const { username } = useAuth();

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.welcome}>Welcome, {username}</Text>
      <Text style={styles.subtitle}>Your GDPR rights at your fingertips</Text>

      <Text style={styles.sectionLabel}>YOUR DATA</Text>

      <MenuCard
        title="View My Data"
        subtitle="Right to Access (GDPR Art. 15) - See all data held about you"
        onPress={() => navigation.navigate('DataAccess')}
      />

      <MenuCard
        title="Fill Questionnaire"
        subtitle="Submit data to an organisation's questionnaire"
        onPress={() => navigation.navigate('QuestionnaireSelect')}
      />

      <Text style={styles.sectionLabel}>MANAGE</Text>

      <MenuCard
        title="My Submissions"
        subtitle="Right to Rectification (GDPR Art. 16) - Edit or delete your submissions"
        onPress={() => navigation.navigate('Submissions')}
      />

      <MenuCard
        title="Manage Consent"
        subtitle="Right to Withdraw (GDPR Art. 7) - Control consent per submission"
        onPress={() => navigation.navigate('ConsentManagement')}
      />

      <Text style={styles.sectionLabel}>ACCOUNT</Text>

      <MenuCard
        title="Settings"
        subtitle="Data deletion, account management, and sign out"
        onPress={() => navigation.navigate('Settings')}
      />
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
    paddingBottom: 40,
  },
  welcome: {
    fontSize: 26,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 15,
    color: colors.textSecondary,
    marginBottom: spacing.lg,
  },
  sectionLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.textTertiary,
    letterSpacing: 1,
    marginBottom: spacing.sm,
    marginTop: spacing.sm,
  },
});
