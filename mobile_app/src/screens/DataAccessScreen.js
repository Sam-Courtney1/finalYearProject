import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from 'react-native';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { getUserData } from '../api/data';
import { colors, spacing, radius } from '../theme/theme';

export default function DataAccessScreen() {
  const [staticData, setStaticData] = useState([]);
  const [dynamicData, setDynamicData] = useState({});
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const rawData = useRef(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getUserData();
        rawData.current = data;
        setStaticData(data.static_data || []);
        setDynamicData(data.dynamic_data || {});
      } catch (e) {
        Alert.alert('Error', 'Failed to load your data.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleExport() {
    if (!rawData.current) {
      Alert.alert('Error', 'No data to export.');
      return;
    }

    setExporting(true);
    try {
      const jsonString = JSON.stringify(rawData.current, null, 2);
      const fileName = `gdpr_data_export_${new Date().toISOString().split('T')[0]}.json`;
      const filePath = `${FileSystem.documentDirectory}${fileName}`;

      await FileSystem.writeAsStringAsync(filePath, jsonString);

      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(filePath, {
          mimeType: 'application/json',
          dialogTitle: 'Export Your Data (GDPR Art. 20)',
        });
      } else {
        Alert.alert('Exported', `Data saved to ${fileName}`);
      }
    } catch (e) {
      Alert.alert('Error', 'Failed to export data.');
    } finally {
      setExporting(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading your data...</Text>
      </View>
    );
  }

  const companies = Object.keys(dynamicData);
  const hasData = staticData.length > 0 || companies.length > 0;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {hasData && (
        <TouchableOpacity
          style={[styles.exportBtn, exporting && styles.btnDisabled]}
          onPress={handleExport}
          disabled={exporting}
        >
          <Text style={styles.exportBtnText}>
            {exporting ? 'Exporting...' : 'Export as JSON (Art. 20)'}
          </Text>
        </TouchableOpacity>
      )}

      <Text style={styles.sectionTitle}>Core Information</Text>
      {staticData.length > 0 ? (
        staticData.map((item, index) => (
          <View key={index} style={styles.card}>
            <Row label="Name" value={item.first_name} />
            <Row label="Address" value={item.address} />
            <Row label="Age" value={String(item.age)} />
          </View>
        ))
      ) : (
        <Text style={styles.empty}>No core data found.</Text>
      )}

      {companies.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Questionnaire Data</Text>
          {companies.map((company) => (
            <View key={company} style={styles.card}>
              <Text style={styles.companyName}>{company}</Text>
              {dynamicData[company].map((field, idx) => (
                <Row
                  key={idx}
                  label={field.field_label}
                  value={field.value}
                  sub={field.category}
                />
              ))}
            </View>
          ))}
        </>
      )}

      {!hasData && (
        <Text style={styles.empty}>No data stored about you.</Text>
      )}
    </ScrollView>
  );
}

function Row({ label, value, sub }) {
  return (
    <View style={styles.row}>
      <View style={styles.rowLeft}>
        <Text style={styles.rowLabel}>{label}</Text>
        {sub && <Text style={styles.rowSub}>{sub}</Text>}
      </View>
      <Text style={styles.rowValue}>{value || '-'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    padding: spacing.md,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: colors.textSecondary,
    fontSize: 15,
  },
  exportBtn: {
    backgroundColor: colors.primaryBg,
    padding: 12,
    borderRadius: radius.sm,
    alignItems: 'center',
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  exportBtnText: {
    color: colors.primary,
    fontWeight: '600',
    fontSize: 14,
  },
  btnDisabled: {
    opacity: 0.6,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 12,
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: colors.border,
  },
  companyName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: colors.primary,
    marginBottom: 10,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  rowLeft: {
    flex: 1,
  },
  rowLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  rowSub: {
    fontSize: 12,
    color: colors.textTertiary,
  },
  rowValue: {
    fontSize: 14,
    color: colors.text,
    flex: 1,
    textAlign: 'right',
  },
  empty: {
    fontSize: 15,
    color: colors.textTertiary,
    textAlign: 'center',
    marginTop: 20,
  },
});
