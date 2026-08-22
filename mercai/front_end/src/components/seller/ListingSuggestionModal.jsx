import React, { useMemo, useState } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Button, Card, Modal, Portal, Divider, Chip } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing } from '../../constants/theme.js';
import ImageQualityReport from './ImageQualityReport.jsx';

const FIELD_LABELS = {
  name: 'Title',
  description: 'Description',
  tags: 'Tags',
  material: 'Material',
  color: 'Colour',
  technique: 'Technique',
  dimensions: 'Dimensions',
};

/**
 * Review sheet for AI listing suggestions.
 *
 * The seller accepts or skips each field individually; nothing is applied
 * until they press Apply, and even then the parent only updates form state --
 * the listing is still saved by the seller pressing Save. Suggestions the
 * model could not support arrive as questions ("ask_seller") rather than
 * guesses, and are shown as prompts, never as accept-able values.
 */
export const ListingSuggestionModal = ({ visible, result, onDismiss, onApply }) => {
  const [skipped, setSkipped] = useState({});

  // Flatten top-level fields and attributes into one reviewable list.
  const items = useMemo(() => {
    if (!result?.suggestions) return [];
    const out = [];

    ['name', 'description', 'tags'].forEach((key) => {
      const entry = result.suggestions[key];
      if (entry?.proposed) {
        out.push({ key, ...entry, kind: 'field' });
      }
    });

    const attributes = result.suggestions.attributes || {};
    Object.keys(attributes).forEach((key) => {
      const entry = attributes[key];
      if (entry?.proposed) {
        out.push({ key, ...entry, kind: 'attribute' });
      } else if (entry?.ask_seller) {
        out.push({ key, ...entry, kind: 'question' });
      }
    });

    return out;
  }, [result]);

  const acceptable = items.filter((item) => item.kind !== 'question');
  const questions = items.filter((item) => item.kind === 'question');
  const accepted = acceptable.filter((item) => !skipped[item.key]);

  const toggle = (key) => setSkipped((prev) => ({ ...prev, [key]: !prev[key] }));

  const handleApply = () => {
    const patch = {};
    accepted.forEach((item) => { patch[item.key] = item.proposed; });
    onApply(patch, accepted.map((item) => item.key));
    setSkipped({});
  };

  const handleDismiss = () => {
    setSkipped({});
    onDismiss();
  };

  return (
    <Portal>
      <Modal visible={visible} onDismiss={handleDismiss} contentContainerStyle={styles.modal}>
        <View style={styles.header}>
          <Icon name="auto-awesome" size={22} color={colors.primary} />
          <Text style={styles.headerText}>Suggested improvements</Text>
        </View>
        <Text style={styles.subtitle}>
          Review each change. Nothing is saved until you press Save on the form.
        </Text>

        <ScrollView style={styles.body}>
          {acceptable.length === 0 && questions.length === 0 && (
            <Text style={styles.empty}>
              No changes suggested — this listing already looks complete.
            </Text>
          )}

          {acceptable.map((item) => {
            const isSkipped = Boolean(skipped[item.key]);
            return (
              <Card key={item.key} style={[styles.card, isSkipped && styles.cardSkipped]} mode="outlined">
                <Card.Content>
                  <Text style={styles.fieldLabel}>{FIELD_LABELS[item.key] || item.key}</Text>

                  {item.current ? (
                    <Text style={styles.current} numberOfLines={3}>{item.current}</Text>
                  ) : (
                    <Text style={styles.emptyCurrent}>(empty)</Text>
                  )}

                  <View style={styles.arrowRow}>
                    <Icon name="arrow-downward" size={16} color={colors.textSecondary} />
                  </View>

                  <Text style={styles.proposed}>{item.proposed}</Text>

                  {!!item.rationale && (
                    <Text style={styles.rationale}>{item.rationale}</Text>
                  )}

                  {/* Sentences asserting something the seller never wrote.
                      Shown, not removed -- only the seller knows whether the
                      claim is actually true of their own piece. */}
                  {(item.unsupported || []).length > 0 && (
                    <View style={styles.unsupportedBox}>
                      <View style={styles.unsupportedHeader}>
                        <Icon name="report-problem" size={16} color="#B45309" />
                        <Text style={styles.unsupportedTitle}>Check this before using</Text>
                      </View>
                      {item.unsupported.map((flag, i) => (
                        <View key={i} style={styles.unsupportedItem}>
                          <Text style={styles.unsupportedSentence}>"{flag.sentence}"</Text>
                          <Text style={styles.unsupportedWhy}>
                            You didn't mention {flag.claims.join(', ')} — keep it only if it's true.
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  <Button
                    mode={isSkipped ? 'outlined' : 'contained-tonal'}
                    compact
                    onPress={() => toggle(item.key)}
                    style={styles.toggle}
                  >
                    {isSkipped ? 'Include' : 'Skip'}
                  </Button>
                </Card.Content>
              </Card>
            );
          })}

          {questions.length > 0 && (
            <>
              <Divider style={styles.divider} />
              <Text style={styles.questionsTitle}>Needs your input</Text>
              <Text style={styles.questionsHint}>
                These were left blank rather than guessed. Fill them in yourself.
              </Text>
              {questions.map((item) => (
                <Chip key={item.key} icon="help-circle-outline" style={styles.question}>
                  {item.ask_seller}
                </Chip>
              ))}
            </>
          )}

          <ImageQualityReport report={result?.image_report} />
        </ScrollView>

        <Divider />
        <View style={styles.actions}>
          <Button mode="text" onPress={handleDismiss}>Discard</Button>
          <Button
            mode="contained"
            onPress={handleApply}
            disabled={accepted.length === 0}
          >
            {accepted.length > 0 ? `Apply ${accepted.length}` : 'Apply'}
          </Button>
        </View>
      </Modal>
    </Portal>
  );
};

const styles = StyleSheet.create({
  modal: {
    backgroundColor: colors.background,
    margin: spacing.md,
    borderRadius: 12,
    maxHeight: '85%',
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: spacing.sm,
    paddingHorizontal: spacing.md, paddingTop: spacing.md,
  },
  headerText: { fontSize: 18, fontWeight: '700', color: colors.text },
  subtitle: {
    fontSize: 13, color: colors.textSecondary,
    paddingHorizontal: spacing.md, paddingTop: spacing.xs, paddingBottom: spacing.sm,
  },
  body: { paddingHorizontal: spacing.md },
  card: { marginBottom: spacing.md, backgroundColor: colors.surface },
  cardSkipped: { opacity: 0.5 },
  fieldLabel: {
    fontSize: 11, fontWeight: '700', letterSpacing: 0.8,
    textTransform: 'uppercase', color: colors.textSecondary, marginBottom: spacing.xs,
  },
  current: { fontSize: 13, color: colors.textSecondary, textDecorationLine: 'line-through' },
  emptyCurrent: { fontSize: 13, color: colors.textSecondary, fontStyle: 'italic' },
  arrowRow: { alignItems: 'center', paddingVertical: 2 },
  proposed: { fontSize: 15, color: colors.text, fontWeight: '500' },
  rationale: { fontSize: 12, color: colors.textSecondary, marginTop: spacing.xs, fontStyle: 'italic' },
  toggle: { marginTop: spacing.sm, alignSelf: 'flex-start' },
  unsupportedBox: {
    marginTop: spacing.sm,
    padding: spacing.sm,
    borderRadius: 8,
    backgroundColor: '#FEF3C7',
    borderLeftWidth: 3,
    borderLeftColor: '#B45309',
  },
  unsupportedHeader: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  unsupportedTitle: { fontSize: 12, fontWeight: '700', color: '#92400E' },
  unsupportedItem: { marginTop: spacing.xs },
  unsupportedSentence: { fontSize: 13, color: '#78350F', fontStyle: 'italic' },
  unsupportedWhy: { fontSize: 12, color: '#92400E', marginTop: 2 },
  divider: { marginVertical: spacing.md },
  questionsTitle: { fontSize: 15, fontWeight: '600', color: colors.text },
  questionsHint: { fontSize: 12, color: colors.textSecondary, marginBottom: spacing.sm },
  question: { marginBottom: spacing.sm, alignSelf: 'flex-start' },
  empty: { fontSize: 14, color: colors.textSecondary, paddingVertical: spacing.lg, textAlign: 'center' },
  actions: {
    flexDirection: 'row', justifyContent: 'flex-end', gap: spacing.sm,
    padding: spacing.md,
  },
});

export default ListingSuggestionModal;
