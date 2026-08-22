import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, Card } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing } from '../../constants/theme.js';

const SEVERITY = {
  warn: { icon: 'warning', color: '#B45309' },
  info: { icon: 'info-outline', color: '#2563EB' },
};

const SCORE_LABEL = {
  excellent: 'Photos look great',
  good: 'Photos look good',
  needs_work: 'Photos could be better',
  missing: 'No photos yet',
};

/**
 * Renders the deterministic photo checks from the AI service.
 *
 * These are measurements (resolution, aspect, brightness), not model output,
 * so they are stated plainly rather than hedged.
 */
export const ImageQualityReport = ({ report }) => {
  // 'not_applicable' means this was a draft: the photos are still on the
  // device and there was nothing to inspect. Saying nothing beats a warning
  // we cannot support.
  if (!report || report.score === 'not_applicable') return null;

  const findings = report.findings || [];

  return (
    <Card style={styles.card} mode="outlined">
      <Card.Content>
        <Text style={styles.title}>{SCORE_LABEL[report.score] || 'Photo check'}</Text>

        {findings.length === 0 ? (
          <View style={styles.row}>
            <Icon name="check-circle" size={18} color="#15803D" />
            <Text style={styles.clean}>Nothing to fix here.</Text>
          </View>
        ) : (
          findings.map((finding, index) => {
            const style = SEVERITY[finding.severity] || SEVERITY.info;
            return (
              <View key={`${finding.code}-${index}`} style={styles.row}>
                <Icon name={style.icon} size={18} color={style.color} />
                <Text style={styles.message}>{finding.message}</Text>
              </View>
            );
          })
        )}
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { marginBottom: spacing.md, backgroundColor: colors.surface },
  title: { fontSize: 15, fontWeight: '600', marginBottom: spacing.sm, color: colors.text },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm, marginBottom: spacing.xs },
  message: { flex: 1, fontSize: 13, color: colors.textSecondary, lineHeight: 18 },
  clean: { flex: 1, fontSize: 13, color: '#15803D' },
});

export default ImageQualityReport;
