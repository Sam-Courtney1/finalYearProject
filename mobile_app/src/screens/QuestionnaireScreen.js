import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Switch,
  ActivityIndicator,
  Alert,
  StyleSheet,
} from 'react-native';
import { getQuestionnaireFields, submitQuestionnaire } from '../api/questionnaire';
import { colors, spacing, radius } from '../theme/theme';

export default function QuestionnaireScreen({ route, navigation }) {
  const { clientId, clientName, questionnaireName } = route.params;
  const [fields, setFields] = useState([]);
  const [answers, setAnswers] = useState({});
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getQuestionnaireFields(clientId, questionnaireName);
        setFields(data.fields || []);
      } catch (e) {
        Alert.alert('Error', 'Failed to load questionnaire fields.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [clientId, questionnaireName]);

  function updateAnswer(fieldId, value) {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
  }

  async function handleSubmit() {
    if (!consent) {
      Alert.alert('Consent Required', 'You must consent to the use of your data before submitting.');
      return;
    }

    const missing = fields.find((f) => !answers[f.field_id] || answers[f.field_id].trim() === '');
    if (missing) {
      Alert.alert('Missing Fields', `Please fill in: ${missing.field_label}`);
      return;
    }

    setSubmitting(true);
    try {
      await submitQuestionnaire(clientId, questionnaireName, answers, true);
      Alert.alert('Success', 'Questionnaire submitted successfully.', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (e) {
      Alert.alert('Error', 'Failed to submit questionnaire. Please try again.');
    } finally {
      setSubmitting(false);
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
        <Text style={styles.empty}>This questionnaire has no fields yet.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>{questionnaireName}</Text>
      <Text style={styles.subheading}>{clientName}</Text>

      {fields.map((field) => (
        <View key={field.field_id} style={styles.fieldContainer}>
          <Text style={styles.label}>{field.field_label}</Text>
          <TextInput
            style={styles.input}
            placeholder={`Enter ${field.field_label.toLowerCase()}`}
            value={answers[field.field_id] || ''}
            onChangeText={(val) => updateAnswer(field.field_id, val)}
            keyboardType={field.field_type === 'number' ? 'numeric' : 'default'}
          />
        </View>
      ))}

      <View style={styles.consentRow}>
        <Switch
          value={consent}
          onValueChange={setConsent}
          trackColor={{ true: colors.primary }}
        />
        <Text style={styles.consentText}>I consent to the use of my data</Text>
      </View>

      <TouchableOpacity
        style={[styles.submitBtn, submitting && styles.btnDisabled]}
        onPress={handleSubmit}
        disabled={submitting}
      >
        <Text style={styles.submitText}>
          {submitting ? 'Submitting...' : 'Submit'}
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
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: 6,
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
  consentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.sm,
    marginBottom: 20,
    backgroundColor: colors.surface,
    padding: 14,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  consentText: {
    fontSize: 15,
    color: colors.text,
    marginLeft: 12,
    flex: 1,
  },
  submitBtn: {
    backgroundColor: colors.success,
    padding: spacing.md,
    borderRadius: radius.md,
    alignItems: 'center',
  },
  btnDisabled: {
    opacity: 0.6,
  },
  submitText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: 'bold',
  },
  empty: {
    fontSize: 16,
    color: colors.textTertiary,
  },
});
