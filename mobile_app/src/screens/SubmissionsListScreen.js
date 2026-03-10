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
import { getSubmissions, deleteSubmission } from '../api/submissions';
import { colors, spacing, radius } from '../theme/theme';

export default function SubmissionsListScreen({ navigation }) {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadSubmissions = useCallback(async () => {
    try {
      const data = await getSubmissions();
      setSubmissions(data.submissions || []);
    } catch (e) {
      Alert.alert('Error', 'Failed to load submissions.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadSubmissions();
  }, [loadSubmissions]);

  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      loadSubmissions();
    });
    return unsubscribe;
  }, [navigation, loadSubmissions]);

  function handleDelete(submissionId, clientName) {
    Alert.alert(
      'Delete Submission',
      `Delete your submission to ${clientName}? This will permanently remove all answers.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteSubmission(submissionId);
              setSubmissions((prev) =>
                prev.filter((s) => s.submission_id !== submissionId)
              );
              Alert.alert('Deleted', 'Submission has been removed.');
            } catch (e) {
              Alert.alert('Error', 'Failed to delete submission.');
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
        <Text style={styles.emptyText}>You haven't submitted any questionnaires yet.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={submissions}
        keyExtractor={(item) => String(item.submission_id)}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              loadSubmissions();
            }}
            colors={[colors.primary]}
          />
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={styles.cardInfo}>
                <Text style={styles.clientName}>{item.client_name}</Text>
                {item.questionnaire_name && (
                  <Text style={styles.questionnaireName}>{item.questionnaire_name}</Text>
                )}
              </View>
              <View
                style={[
                  styles.badge,
                  item.consent_withdrawn ? styles.badgeWithdrawn : styles.badgeActive,
                ]}
              >
                <Text
                  style={[
                    styles.badgeText,
                    item.consent_withdrawn ? styles.badgeTextWithdrawn : styles.badgeTextActive,
                  ]}
                >
                  {item.consent_withdrawn ? 'Withdrawn' : 'Active'}
                </Text>
              </View>
            </View>

            <View style={styles.cardActions}>
              <TouchableOpacity
                style={styles.editBtn}
                onPress={() =>
                  navigation.navigate('EditSubmission', {
                    submissionId: item.submission_id,
                    clientName: item.client_name,
                    questionnaireName: item.questionnaire_name,
                  })
                }
              >
                <Text style={styles.editBtnText}>Edit Answers</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.deleteBtn}
                onPress={() => handleDelete(item.submission_id, item.client_name)}
              >
                <Text style={styles.deleteBtnText}>Delete</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
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
  list: {
    padding: spacing.md,
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
  cardHeader: {
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
  cardActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  editBtn: {
    flex: 1,
    backgroundColor: colors.primaryBg,
    paddingVertical: 10,
    borderRadius: radius.sm,
    alignItems: 'center',
  },
  editBtnText: {
    color: colors.primary,
    fontWeight: '600',
    fontSize: 14,
  },
  deleteBtn: {
    flex: 1,
    backgroundColor: colors.dangerBg,
    paddingVertical: 10,
    borderRadius: radius.sm,
    alignItems: 'center',
  },
  deleteBtnText: {
    color: colors.danger,
    fontWeight: '600',
    fontSize: 14,
  },
});
