import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
  RefreshControl,
} from 'react-native';
import { getConsentStatus, withdrawConsent, reinstateConsent } from '../api/consent';
import { colors, spacing, radius } from '../theme/theme';

export default function ConsentManagementScreen() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);

  const loadConsent = useCallback(async () => {
    try {
      const data = await getConsentStatus();
      setSubmissions(data.consents || []);
    } catch (e) {
      Alert.alert('Error', 'Failed to load consent status.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadConsent();
  }, [loadConsent]);

  function handleWithdraw(submissionId, clientName) {
    Alert.alert(
      'Withdraw Consent',
      `Withdraw your consent for the submission to ${clientName}? The organisation will no longer be able to use this data.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Withdraw',
          style: 'destructive',
          onPress: async () => {
            setActionLoading(submissionId);
            try {
              await withdrawConsent(submissionId);
              setSubmissions((prev) =>
                prev.map((s) =>
                  s.submission_id === submissionId
                    ? { ...s, consent_withdrawn: true }
                    : s
                )
              );
            } catch (e) {
              Alert.alert('Error', 'Failed to withdraw consent.');
            } finally {
              setActionLoading(null);
            }
          },
        },
      ]
    );
  }

  function handleReinstate(submissionId, clientName) {
    Alert.alert(
      'Reinstate Consent',
      `Re-grant your consent for the submission to ${clientName}? The organisation will be able to use this data again.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reinstate',
          onPress: async () => {
            setActionLoading(submissionId);
            try {
              await reinstateConsent(submissionId);
              setSubmissions((prev) =>
                prev.map((s) =>
                  s.submission_id === submissionId
                    ? { ...s, consent_withdrawn: false }
                    : s
                )
              );
            } catch (e) {
              Alert.alert('Error', 'Failed to reinstate consent.');
            } finally {
              setActionLoading(null);
            }
          },
        },
      ]
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (submissions.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyTitle}>No Submissions</Text>
        <Text style={styles.emptyText}>You have no submissions to manage consent for.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.info}>
        Under GDPR Article 7, you can withdraw or reinstate consent for each submission at any time.
      </Text>
      <FlatList
        data={submissions}
        keyExtractor={(item) => String(item.submission_id)}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              loadConsent();
            }}
            colors={[colors.primary]}
          />
        }
        renderItem={({ item }) => {
          const isWithdrawn = item.consent_withdrawn;
          const isLoading = actionLoading === item.submission_id;

          return (
            <View style={styles.card}>
              <View style={styles.cardTop}>
                <View style={styles.cardInfo}>
                  <Text style={styles.clientName}>{item.client_name}</Text>
                  {item.questionnaire_name && (
                    <Text style={styles.questionnaireName}>{item.questionnaire_name}</Text>
                  )}
                </View>
                <View style={[styles.badge, isWithdrawn ? styles.badgeWithdrawn : styles.badgeActive]}>
                  <Text style={[styles.badgeText, isWithdrawn ? styles.badgeTextWithdrawn : styles.badgeTextActive]}>
                    {isWithdrawn ? 'Withdrawn' : 'Active'}
                  </Text>
                </View>
              </View>

              {isWithdrawn ? (
                <TouchableOpacity
                  style={[styles.reinstateBtn, isLoading && styles.btnDisabled]}
                  onPress={() => handleReinstate(item.submission_id, item.client_name)}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <ActivityIndicator size="small" color={colors.success} />
                  ) : (
                    <Text style={styles.reinstateBtnText}>Reinstate Consent</Text>
                  )}
                </TouchableOpacity>
              ) : (
                <TouchableOpacity
                  style={[styles.withdrawBtn, isLoading && styles.btnDisabled]}
                  onPress={() => handleWithdraw(item.submission_id, item.client_name)}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <ActivityIndicator size="small" color={colors.danger} />
                  ) : (
                    <Text style={styles.withdrawBtnText}>Withdraw Consent</Text>
                  )}
                </TouchableOpacity>
              )}
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  info: {
    fontSize: 13,
    color: colors.textSecondary,
    padding: spacing.md,
    paddingBottom: spacing.sm,
    lineHeight: 18,
  },
  list: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: spacing.sm,
  },
  emptyText: {
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  cardInfo: {
    flex: 1,
    marginRight: spacing.sm,
  },
  clientName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  questionnaireName: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 2,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.sm,
  },
  badgeActive: {
    backgroundColor: 'rgba(5, 150, 105, 0.1)',
  },
  badgeWithdrawn: {
    backgroundColor: colors.dangerBg,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '600',
  },
  badgeTextActive: {
    color: colors.success,
  },
  badgeTextWithdrawn: {
    color: colors.danger,
  },
  withdrawBtn: {
    backgroundColor: colors.dangerBg,
    paddingVertical: 10,
    borderRadius: radius.sm,
    alignItems: 'center',
  },
  withdrawBtnText: {
    color: colors.danger,
    fontWeight: '600',
    fontSize: 14,
  },
  reinstateBtn: {
    backgroundColor: 'rgba(5, 150, 105, 0.1)',
    paddingVertical: 10,
    borderRadius: radius.sm,
    alignItems: 'center',
  },
  reinstateBtnText: {
    color: colors.success,
    fontWeight: '600',
    fontSize: 14,
  },
  btnDisabled: {
    opacity: 0.6,
  },
});
