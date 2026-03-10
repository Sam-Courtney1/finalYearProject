import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { colors, spacing, radius } from '../theme/theme';

export default function MenuCard({ title, subtitle, onPress, variant = 'default' }) {
  const cardStyle = variant === 'danger' ? styles.cardDanger : styles.card;
  const titleStyle = variant === 'danger' ? styles.titleDanger : styles.title;

  return (
    <TouchableOpacity style={cardStyle} onPress={onPress} activeOpacity={0.7}>
      <Text style={titleStyle}>{title}</Text>
      {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardDanger: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.dangerLight,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  titleDanger: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.danger,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
});
