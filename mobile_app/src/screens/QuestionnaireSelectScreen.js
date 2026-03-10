import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from 'react-native';
import { getClients } from '../api/questionnaire';
import { colors, spacing, radius } from '../theme/theme';

export default function QuestionnaireSelectScreen({ navigation }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getClients();
        const clients = data.clients || [];
        // Flatten: one row per questionnaire per client
        const flattened = [];
        clients.forEach((client) => {
          (client.questionnaires || []).forEach((qName) => {
            flattened.push({
              key: `${client.client_id}-${qName}`,
              clientId: client.client_id,
              clientName: client.name,
              questionnaireName: qName,
            });
          });
        });
        setItems(flattened);
      } catch (e) {
        Alert.alert('Error', 'Failed to load organisations.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (items.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.empty}>No questionnaires available.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Select a questionnaire to fill</Text>
      <FlatList
        data={items}
        keyExtractor={(item) => item.key}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.item}
            onPress={() =>
              navigation.navigate('Questionnaire', {
                clientId: item.clientId,
                clientName: item.clientName,
                questionnaireName: item.questionnaireName,
              })
            }
          >
            <View style={styles.itemContent}>
              <Text style={styles.itemText}>{item.questionnaireName}</Text>
              <Text style={styles.itemSub}>{item.clientName}</Text>
            </View>
            <Text style={styles.arrow}>›</Text>
          </TouchableOpacity>
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
  },
  heading: {
    fontSize: 15,
    color: colors.textSecondary,
    padding: spacing.md,
    paddingBottom: spacing.sm,
  },
  item: {
    backgroundColor: colors.surface,
    padding: 18,
    marginHorizontal: spacing.md,
    marginBottom: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  itemContent: {
    flex: 1,
  },
  itemText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  itemSub: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 2,
  },
  arrow: {
    fontSize: 22,
    color: colors.textTertiary,
    marginLeft: spacing.sm,
  },
  empty: {
    fontSize: 16,
    color: colors.textTertiary,
  },
});
