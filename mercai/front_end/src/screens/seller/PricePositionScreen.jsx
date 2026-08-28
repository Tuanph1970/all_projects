import React, { useCallback, useEffect, useState } from 'react';
import { View, ScrollView, StyleSheet, RefreshControl, Alert } from 'react-native';
import {
  Text, Card, ActivityIndicator, Button, Chip, Divider, TextInput, IconButton,
} from 'react-native-paper';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import intelService from '../../services/intelService.js';
import { colors, spacing } from '../../constants/theme.js';

const formatVnd = (value) =>
  value == null ? '—' : `${Math.round(value).toLocaleString('vi-VN')}₫`;

/**
 * Deliberately positional, never a verdict.
 *
 * Artisan sellers price on materials, hours and reputation. A screen that
 * scolds them for sitting above the median is wrong about their business and
 * will be switched off -- so the label describes where they are and the
 * interpretation stays with them.
 */
const POSITION_COPY = {
  below_market: {
    label: 'Below market',
    tone: colors.info,
    blurb: 'Most comparable listings ask more than you do.',
  },
  in_range: {
    label: 'In range',
    tone: colors.success,
    blurb: 'Your price sits inside the middle half of comparable listings.',
  },
  above_market: {
    label: 'Above market',
    tone: colors.warning,
    blurb: 'Most comparable listings ask less. That can be exactly right for a piece like yours.',
  },
};

/** A scale drawn from p25/p75, with the seller's own price marked on it. */
const PriceScale = ({ p25, median, p75, min, max, own }) => {
  const lo = Math.min(min ?? own, own);
  const hi = Math.max(max ?? own, own);
  const span = hi - lo || 1;
  const pct = (v) => `${Math.min(100, Math.max(0, ((v - lo) / span) * 100))}%`;

  return (
    <View style={styles.scaleWrap}>
      <View style={styles.scaleTrack}>
        {/* The interquartile band: where the middle half of the market sits. */}
        <View
          style={[
            styles.scaleBand,
            { left: pct(p25), width: `${((p75 - p25) / span) * 100}%` },
          ]}
        />
        <View style={[styles.scaleMedian, { left: pct(median) }]} />
        <View style={[styles.scaleOwn, { left: pct(own) }]} />
      </View>
      <View style={styles.scaleLabels}>
        <Text style={styles.scaleLabel}>{formatVnd(lo)}</Text>
        <Text style={styles.scaleLabel}>{formatVnd(hi)}</Text>
      </View>
      <View style={styles.legendRow}>
        <View style={styles.legendItem}>
          <View style={[styles.legendSwatch, { backgroundColor: colors.primaryContainer }]} />
          <Text style={styles.legendText}>Middle half (p25–p75)</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendSwatch, { backgroundColor: colors.secondary }]} />
          <Text style={styles.legendText}>Median</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendSwatch, { backgroundColor: colors.primary }]} />
          <Text style={styles.legendText}>You</Text>
        </View>
      </View>
    </View>
  );
};

export const PricePositionScreen = ({ route, navigation }) => {
  const { productId } = route.params || {};
  const insets = useSafeAreaInsets();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const [tracked, setTracked] = useState([]);
  const [supportedHosts, setSupportedHosts] = useState([]);
  const [newUrl, setNewUrl] = useState('');
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const response = await intelService.getPricePosition(productId);
      setData(response?.data || response);
    } catch (err) {
      setError(
        err?.response?.status === 404
          ? 'Price insights are not switched on for your account yet.'
          : 'Could not load price insights. Pull down to try again.',
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [productId]);

  const loadComparables = useCallback(async () => {
    try {
      const response = await intelService.listComparables(productId);
      const body = response?.data || response;
      setTracked(body?.comparables || []);
      setSupportedHosts(body?.supported_hosts || []);
    } catch (err) {
      // Non-fatal: the market view is still worth showing without this.
      setTracked([]);
    }
  }, [productId]);

  const handleAdd = async () => {
    const url = newUrl.trim();
    if (!url) return;
    try {
      setAdding(true);
      const response = await intelService.addComparable({ productId, url });
      const added = response?.data || response;
      setNewUrl('');
      await Promise.all([loadComparables(), load()]);
      // Adding fetches once, so the seller learns immediately whether we can
      // read the page. Saying nothing here would leave a silent dead row.
      if (added?.latest && added.latest.status !== 'ok') {
        Alert.alert('Added, but we couldn’t read a price', added.latest.message);
      }
    } catch (err) {
      Alert.alert(
        'Could not add that link',
        err?.response?.data?.detail || 'Please check the URL and try again.',
      );
    } finally {
      setAdding(false);
    }
  };

  const handleRefreshOne = async (comparableId) => {
    try {
      await intelService.refreshComparable(comparableId);
      await Promise.all([loadComparables(), load()]);
    } catch (err) {
      Alert.alert(
        'Not right now',
        err?.response?.data?.detail || 'Could not re-check that listing.',
      );
    }
  };

  const handleRemove = (comparableId) => {
    Alert.alert('Stop tracking this listing?', 'Its price history is kept.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Stop tracking',
        style: 'destructive',
        onPress: async () => {
          await intelService.removeComparable(comparableId);
          await Promise.all([loadComparables(), load()]);
        },
      },
    ]);
  };

  useEffect(() => {
    load();
    loadComparables();
  }, [load, loadComparables]);

  if (loading) {
    return (
      <View style={styles.centered} testID="price-position-loading">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered} testID="price-position-error">
        <Text style={styles.errorText}>{error}</Text>
        <Button mode="outlined" onPress={load} style={{ marginTop: spacing.base }}>
          Try again
        </Button>
      </View>
    );
  }

  const hasMarket = data?.basis !== 'none' && data?.position;
  const copy = POSITION_COPY[data?.position] || null;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ paddingBottom: Math.max(insets.bottom, spacing.xl) }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            load();
          }}
        />
      }
      testID="price-position-screen"
    >
      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.productName}>{data?.product_name}</Text>
          <Text style={styles.ownPrice}>{formatVnd(data?.own_price)}</Text>

          {hasMarket ? (
            <>
              <Chip
                style={[styles.positionChip, { backgroundColor: `${copy.tone}22` }]}
                textStyle={{ color: copy.tone, fontWeight: '600' }}
                testID="price-position-label"
              >
                {copy.label}
              </Chip>
              <Text style={styles.blurb}>{copy.blurb}</Text>
            </>
          ) : (
            /* Not an error state. Genuine one-off pieces frequently have no
               comparable, and a blank screen would teach those sellers the
               feature is broken. */
            <Text style={styles.blurb} testID="price-position-no-market">
              There aren’t enough comparable listings yet to show a market range.
              We need at least {data?.min_comparable_n} from other sellers
              {data?.comparable_count ? ` (we found ${data.comparable_count})` : ''}.
            </Text>
          )}
        </Card.Content>
      </Card>

      {hasMarket && (
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.sectionTitle}>The market</Text>
            <Text style={styles.sectionCaption}>
              {data.comparable_count} listings from other sellers in{' '}
              {data.basis_label}
              {data.basis === 'parent_category'
                ? ' — the broader category, because your own has too few to compare'
                : ''}
              .
            </Text>

            <PriceScale
              p25={data.p25}
              median={data.median}
              p75={data.p75}
              min={data.min}
              max={data.max}
              own={data.own_price}
            />

            <View style={styles.statRow}>
              {[
                ['Lowest', data.min],
                ['p25', data.p25],
                ['Median', data.median],
                ['p75', data.p75],
                ['Highest', data.max],
              ].map(([label, value]) => (
                <View key={label} style={styles.stat}>
                  <Text style={styles.statLabel}>{label}</Text>
                  <Text style={styles.statValue}>{formatVnd(value)}</Text>
                </View>
              ))}
            </View>
          </Card.Content>
        </Card>
      )}

      {hasMarket && data.comparables?.length > 0 && (
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.sectionTitle}>Comparable listings</Text>
            <Text style={styles.sectionCaption}>
              A sample across the range. Shop names are not shown.
            </Text>
            {data.comparables.map((item, index) => (
              <View key={item.product_id}>
                {index > 0 && <Divider />}
                <View style={styles.comparableRow}>
                  <Text style={styles.comparableName} numberOfLines={2}>
                    {item.name}
                  </Text>
                  <Text style={styles.comparablePrice}>{formatVnd(item.price)}</Text>
                </View>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      {data?.benchmark && (
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.sectionTitle}>The wider market</Text>
            <Text style={styles.sectionCaption}>
              {data.benchmark.label} — {data.benchmark.sample_size} of{' '}
              {data.benchmark.catalogue_total} listings sampled
              {data.benchmark.stale ? ', last checked a while ago' : ''}.
            </Text>

            <View style={styles.statRow}>
              {[
                ['p25', data.benchmark.p25],
                ['Median', data.benchmark.median],
                ['p75', data.benchmark.p75],
              ].map(([label, value]) => (
                <View key={label} style={styles.stat}>
                  <Text style={styles.statLabel}>{label}</Text>
                  <Text style={styles.statValue}>{formatVnd(value)}</Text>
                </View>
              ))}
            </View>

            {/* The caveat travels with the numbers. A median means nothing
                without knowing what it is a median of. */}
            {data.benchmark.caveat && (
              <Text style={styles.benchmarkCaveat} testID="benchmark-caveat">
                {data.benchmark.caveat}
              </Text>
            )}
            <Text style={styles.benchmarkNote}>
              Shown for context only. It’s a different marketplace with a
              different mix of products, so it isn’t counted in your position
              above.
            </Text>
          </Card.Content>
        </Card>
      )}

      <Card style={styles.card}>
        <Card.Content>
          <Text style={styles.sectionTitle}>Listings you’re tracking</Text>
          <Text style={styles.sectionCaption}>
            Paste a competitor’s product page. We check it when you ask, and only
            count it towards the range above when we’re confident we read it right.
          </Text>

          {tracked.map((item) => (
            <View key={item.id} style={styles.trackedRow}>
              <View style={styles.trackedMain}>
                <Text style={styles.trackedHost}>{item.source_host}</Text>
                <Text style={styles.trackedStatus} numberOfLines={2}>
                  {item.latest
                    ? item.latest.status === 'ok'
                      ? `${formatVnd(item.latest.price)}${item.latest.stale ? ' · last checked a while ago' : ''}`
                      : item.latest.message
                    : 'Not checked yet'}
                </Text>
                {item.latest?.status === 'ok' && !item.latest.trusted && (
                  <Text style={styles.trackedCaveat}>
                    Shown for reference — not confident enough to count.
                  </Text>
                )}
              </View>
              <IconButton icon="refresh" size={18} onPress={() => handleRefreshOne(item.id)} />
              <IconButton icon="close" size={18} onPress={() => handleRemove(item.id)} />
            </View>
          ))}

          <TextInput
            mode="outlined"
            label="Competitor product URL"
            value={newUrl}
            onChangeText={setNewUrl}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            style={styles.urlInput}
            testID="comparable-url-input"
          />
          <Button
            mode="contained-tonal"
            onPress={handleAdd}
            loading={adding}
            disabled={adding || !newUrl.trim()}
            contentStyle={{ height: 48 }}
            testID="comparable-add-button"
          >
            Track this listing
          </Button>
          {supportedHosts.length > 0 && (
            <Text style={styles.hostsHint}>
              Sites we can read so far: {supportedHosts.join(', ')}
            </Text>
          )}
        </Card.Content>
      </Card>

      {data?.trend?.length > 1 && (
        <Card style={styles.card}>
          <Card.Content>
            <Text style={styles.sectionTitle}>Your price history</Text>
            <Text style={styles.sectionCaption}>
              Every change, exactly as recorded.
            </Text>
            {data.trend.map((point, index) => (
              <View key={`${point.at}-${index}`} style={styles.trendRow}>
                <Text style={styles.trendDate}>
                  {point.at ? new Date(point.at).toLocaleDateString('vi-VN') : '—'}
                </Text>
                <Text style={styles.trendReason}>{point.reason}</Text>
                <Text style={styles.trendPrice}>{formatVnd(point.price)}</Text>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      <Button
        mode="outlined"
        onPress={() => navigation.navigate('AddProduct', { productId })}
        style={styles.editButton}
        // react-native-paper's default Button is 40dp tall, below Android's
        // 48dp minimum tap target. AddProductScreen, CheckoutScreen and
        // CartScreen all set this explicitly; this one did not, and the
        // layout suite caught it at exactly 40.0dp.
        contentStyle={{ height: 48 }}
        testID="price-position-edit-button"
      >
        Edit this listing
      </Button>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.surface },
  centered: {
    flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.lg,
    backgroundColor: colors.surface,
  },
  errorText: { color: colors.textSecondary, textAlign: 'center' },

  card: { margin: spacing.base, marginBottom: 0, backgroundColor: colors.card },

  productName: { fontSize: 14, color: colors.textSecondary },
  ownPrice: { fontSize: 30, fontWeight: '700', color: colors.text, marginTop: spacing.xs },
  positionChip: { alignSelf: 'flex-start', marginTop: spacing.sm },
  blurb: { marginTop: spacing.sm, color: colors.textSecondary, lineHeight: 20 },

  sectionTitle: { fontSize: 16, fontWeight: '600', color: colors.text },
  sectionCaption: {
    fontSize: 12, color: colors.textSecondary, marginTop: spacing.xs,
    marginBottom: spacing.base, lineHeight: 17,
  },

  scaleWrap: { marginBottom: spacing.base },
  scaleTrack: {
    height: 10, borderRadius: 5, backgroundColor: colors.surfaceVariant,
    justifyContent: 'center',
  },
  scaleBand: {
    position: 'absolute', height: 10, borderRadius: 5,
    backgroundColor: colors.primaryContainer,
  },
  scaleMedian: {
    position: 'absolute', width: 2, height: 18, backgroundColor: colors.secondary,
    marginLeft: -1,
  },
  scaleOwn: {
    position: 'absolute', width: 4, height: 24, borderRadius: 2,
    backgroundColor: colors.primary, marginLeft: -2,
  },
  scaleLabels: {
    flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.sm,
  },
  scaleLabel: { fontSize: 11, color: colors.textMuted },
  legendRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginRight: spacing.base },
  legendSwatch: { width: 10, height: 10, borderRadius: 2, marginRight: spacing.xs },
  legendText: { fontSize: 11, color: colors.textMuted },

  statRow: { flexDirection: 'row', justifyContent: 'space-between' },
  stat: { alignItems: 'center', flex: 1 },
  statLabel: { fontSize: 10, color: colors.textMuted, textTransform: 'uppercase' },
  statValue: { fontSize: 12, fontWeight: '600', color: colors.text, marginTop: 2 },

  comparableRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.sm,
  },
  comparableName: { flex: 1, fontSize: 13, color: colors.text, paddingRight: spacing.sm },
  comparablePrice: { fontSize: 13, fontWeight: '600', color: colors.text },

  trendRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.xs },
  trendDate: { fontSize: 12, color: colors.textSecondary, width: 90 },
  trendReason: { flex: 1, fontSize: 12, color: colors.textMuted },
  trendPrice: { fontSize: 13, fontWeight: '600', color: colors.text },

  benchmarkCaveat: {
    fontSize: 12, color: colors.warning, marginTop: spacing.base, lineHeight: 17,
  },
  benchmarkNote: {
    fontSize: 11, color: colors.textMuted, marginTop: spacing.sm, lineHeight: 16,
  },

  trackedRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: spacing.xs,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border,
  },
  trackedMain: { flex: 1, paddingRight: spacing.sm },
  trackedHost: { fontSize: 12, color: colors.textSecondary },
  trackedStatus: { fontSize: 13, color: colors.text, marginTop: 2 },
  trackedCaveat: { fontSize: 11, color: colors.warning, marginTop: 2 },
  urlInput: { marginTop: spacing.base, marginBottom: spacing.sm },
  hostsHint: {
    fontSize: 11, color: colors.textMuted, marginTop: spacing.sm, lineHeight: 16,
  },

  editButton: { margin: spacing.base },
});

export default PricePositionScreen;
