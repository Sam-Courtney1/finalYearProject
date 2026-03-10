import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  StyleSheet,
} from 'react-native';
import { getSubmissionAnswers, updateSubmissionAnswers } from '../api/submissions';
import { colors, spacing, radius } from '../theme/theme';

export default function EditSubmissionScreen({ route, navigation }) {
  const { submissionId, clientName, questionnaireName } = route.params;
  const [fields, setFields] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const originalAnswers = useRef({});

  useEffect(() => {
    async function load() {
      try {
        const data = await getSubmissionAnswers(submissionId);
        const answerFields = data.fields || [];
        setFields(answerFields);
        const initial = {};
        answerFields.forEach((f) => {
          initial[f.field_id] = f.value || '';
        });
        setAnswers(initial);
        originalAnswers.current = { ...initial };
      } catch (e) {
        Alert.alert('Error', 'Failed to load submission answers.');
        navigation.goBack();
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [submissionId, navigation]);

  function updateAnswer(fieldId, value) {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
  }

  async function handleSave() {
    // Only send changed fields
    const changed = {};
    for (const [fieldId, value] of Object.entries(answers)) {
      if (value !== originalAnswers.current[fieldId]) {
        changed[fieldId] = value;
      }
    }

    if (Object.keys(changed).length === 0) {
      Alert.alert('No Changes', 'You haven\'t changed any answers.');
      return;
    }

    setSaving(true);
    try {
      const result = await updateSubmissionAnswers(submissionId, changed);
      Alert.alert(
        'Saved',
        `${result.changed_count || Object.keys(changed).length} field(s) updated.`,
        [{ text: 'OK', onPress: () => navigation.goBack() }]
      );
    } catch (e) {
      Alert.alert('Error', 'Failed to save changes. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (fields.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.empty}>No editable fields found.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>{questionnaireName || 'Edit Answers'}</Text>
      <Text style={styles.subheading}>{clientName}</Text>

      {fields.map((field) => (
        <View key={field.field_id} style={styles.fieldContainer}>
          <View style={styles.labelRow}>
            <Text style={styles.label}>{field.field_label}</Text>
            {field.category && (
              <Text style={styles.category}>{field.category}</Text>
            )}
          </View>
          <TextInput
            style={styles.input}
            value={answers[field.field_id] || ''}
            onChangeText={(val) => updateAnswer(field.field_id, val)}
            keyboardType={field.field_type === 'number' ? 'numeric' : 'default'}
          />
        </View>
      ))}

      <TouchableOpacity
        style={[styles.saveBtn, saving && styles.btnDisabled]}
        onPress={handleSave}
        disabled={saving}
      >
        <Text style={styles.saveBtnText}>
          {saving ? 'Saving...' : 'Save Changes'}
        </Text>
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
    padding: spacing.md,
    paddingBottom: 40,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  heading: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 4,
  },
  subheading: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 20,
  },
  fieldContainer: {
    marginBottom: spacing.md,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  category: {
    fontSize: 11,
    color: colors.textTertiary,
    backgroundColor: colors.borderLight,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: 14,
    fontSize: 16,
    color: colors.text,
  },
  saveBtn: {
    backgroundColor: colors.primary,
    padding: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  saveBtnText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: 'bold',
  },
  empty: {
    fontSize: 16,
    color: colors.textTertiary,
  },
});
