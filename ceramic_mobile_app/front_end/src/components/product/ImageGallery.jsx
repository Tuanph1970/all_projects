import React, { useState, useRef } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Modal,
  Dimensions,
  StatusBar,
} from 'react-native';
import { IconButton, Text } from 'react-native-paper';
import FastImage from 'react-native-fast-image';
import { colors, spacing, borderRadius, shadows } from '../../constants/theme.js';

const { width, height } = Dimensions.get('window');
const THUMBNAIL_SIZE = 60;
const MAIN_IMAGE_HEIGHT = 300;

export const ImageGallery = ({
  images,
  productName,
  initialIndex = 0,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(initialIndex);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalImageIndex, setModalImageIndex] = useState(0);
  const thumbnailsRef = useRef(null);
  const mainImageRef = useRef(null);

  if (!images || images.length === 0) {
    return (
      <View style={styles.placeholderContainer}>
        <Text style={styles.placeholderText}>📷</Text>
        <Text style={styles.placeholderSubtext}>Không có hình ảnh</Text>
      </View>
    );
  }

  const handleThumbnailPress = (index) => {
    setSelectedIndex(index);
    mainImageRef.current?.scrollToIndex({ index, animated: true });
    
    if (thumbnailsRef.current) {
      const offset = index * (THUMBNAIL_SIZE + spacing.sm) - width / 2 + THUMBNAIL_SIZE / 2;
      thumbnailsRef.current.scrollToOffset({ offset, animated: true });
    }
  };

  const handleMainImagePress = () => {
    setModalImageIndex(selectedIndex);
    setIsModalVisible(true);
  };

  const onMainImageViewableItemsChanged = ({ viewableItems }) => {
    if (viewableItems.length > 0) {
      const newIndex = viewableItems[0].index || 0;
      setSelectedIndex(newIndex);
      
      if (thumbnailsRef.current && newIndex !== selectedIndex) {
        const offset = newIndex * (THUMBNAIL_SIZE + spacing.sm) - width / 2 + THUMBNAIL_SIZE / 2;
        thumbnailsRef.current.scrollToOffset({ offset, animated: true });
      }
    }
  };

  const renderMainImage = ({ item, index }) => (
    <TouchableOpacity onPress={handleMainImagePress} activeOpacity={0.9}>
      <FastImage
        source={{ uri: item.url || item }}
        style={styles.mainImage}
        resizeMode={FastImage.resizeMode.cover}
      />
    </TouchableOpacity>
  );

  const renderThumbnail = ({ item, index }) => (
    <TouchableOpacity
      onPress={() => handleThumbnailPress(index)}
      style={[
        styles.thumbnailContainer,
        index === selectedIndex && styles.selectedThumbnailContainer,
      ]}
      activeOpacity={0.8}
    >
      <FastImage
        source={{ uri: item.url || item }}
        style={styles.thumbnail}
        resizeMode={FastImage.resizeMode.cover}
      />
      {index === selectedIndex && <View style={styles.selectedOverlay} />}
    </TouchableOpacity>
  );

  const renderModalImage = ({ item, index }) => (
    <View style={styles.modalImageContainer}>
      <FastImage
        source={{ uri: item.url || item }}
        style={styles.modalImage}
        resizeMode={FastImage.resizeMode.contain}
      />
    </View>
  );

  const onModalViewableItemsChanged = ({ viewableItems }) => {
    if (viewableItems.length > 0) {
      setModalImageIndex(viewableItems[0].index || 0);
    }
  };

  const viewabilityConfig = {
    itemVisiblePercentThreshold: 80,
  };

  return (
    <View style={styles.container}>
      <View style={styles.mainImageContainer}>
        <FlatList
          ref={mainImageRef}
          data={images}
          renderItem={renderMainImage}
          keyExtractor={(item, index) => `main-${index}`}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          onViewableItemsChanged={onMainImageViewableItemsChanged}
          viewabilityConfig={viewabilityConfig}
          getItemLayout={(data, index) => ({
            length: width,
            offset: width * index,
            index,
          })}
          initialScrollIndex={initialIndex}
        />
        
        <View style={styles.imageCounter}>
          <Text style={styles.imageCounterText}>
            {selectedIndex + 1} / {images.length}
          </Text>
        </View>

        <IconButton
          icon="magnify-plus"
          iconColor={colors.onPrimary}
          size={24}
          onPress={handleMainImagePress}
          style={styles.zoomButton}
          containerColor="rgba(0, 0, 0, 0.6)"
        />
      </View>

      {images.length > 1 && (
        <View style={styles.thumbnailsContainer}>
          <FlatList
            ref={thumbnailsRef}
            data={images}
            renderItem={renderThumbnail}
            keyExtractor={(item, index) => `thumb-${index}`}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.thumbnailsContent}
            ItemSeparatorComponent={() => <View style={styles.thumbnailSeparator} />}
          />
        </View>
      )}

      <Modal
        visible={isModalVisible}
        animationType="fade"
        statusBarTranslucent
        onRequestClose={() => setIsModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <IconButton
            icon="close"
            iconColor={colors.onPrimary}
            size={28}
            onPress={() => setIsModalVisible(false)}
            style={styles.closeButton}
          />

          <FlatList
            data={images}
            renderItem={renderModalImage}
            keyExtractor={(item, index) => `modal-${index}`}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onViewableItemsChanged={onModalViewableItemsChanged}
            viewabilityConfig={viewabilityConfig}
            initialScrollIndex={selectedIndex}
            getItemLayout={(data, index) => ({
              length: width,
              offset: width * index,
              index,
            })}
          />
          
          <View style={styles.modalImageCounter}>
            <Text style={styles.modalImageCounterText}>
              {modalImageIndex + 1} / {images.length}
            </Text>
          </View>

          <View style={styles.modalProductName}>
            <Text style={styles.modalProductNameText}>
              {productName}
            </Text>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  mainImageContainer: {
    height: MAIN_IMAGE_HEIGHT,
    backgroundColor: colors.surface,
  },
  mainImage: {
    width,
    height: MAIN_IMAGE_HEIGHT,
  },
  imageCounter: {
    position: 'absolute',
    bottom: spacing.md,
    right: spacing.md,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.sm,
  },
  imageCounterText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.onPrimary,
  },
  zoomButton: {
    position: 'absolute',
    top: spacing.md,
    right: spacing.md,
  },
  zoomIcon: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: borderRadius.sm,
  },
  thumbnailsContainer: {
    paddingVertical: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.outline,
    backgroundColor: colors.surface,
  },
  thumbnailsContent: {
    paddingHorizontal: spacing.md,
  },
  thumbnailContainer: {
    width: THUMBNAIL_SIZE,
    height: THUMBNAIL_SIZE,
    borderRadius: borderRadius.sm,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: colors.outline,
  },
  selectedThumbnailContainer: {
    borderColor: colors.primary,
    ...shadows.md,
  },
  thumbnail: {
    width: THUMBNAIL_SIZE,
    height: THUMBNAIL_SIZE,
  },
  selectedOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
    opacity: 0.3,
  },
  thumbnailSeparator: {
    width: spacing.sm,
  },
  placeholderContainer: {
    height: MAIN_IMAGE_HEIGHT,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.surfaceVariant,
  },
  placeholderText: {
    fontSize: 48,
    marginBottom: spacing.sm,
  },
  placeholderSubtext: {
    fontSize: 16,
    color: colors.onSurfaceVariant,
  },
  
  // Modal Styles
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    justifyContent: 'center',
  },
  closeButton: {
    position: 'absolute',
    top: StatusBar.currentHeight + spacing.md,
    right: spacing.md,
    zIndex: 1000,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    borderRadius: borderRadius.full,
  },
  modalImageContainer: {
    width,
    height,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalImage: {
    width,
    height,
  },
  modalImageCounter: {
    position: 'absolute',
    bottom: spacing.xl * 3,
    alignSelf: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.sm,
  },
  modalImageCounterText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.onPrimary,
  },
  modalProductName: {
    position: 'absolute',
    bottom: spacing.xl,
    left: spacing.md,
    right: spacing.md,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.sm,
  },
  modalProductNameText: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.onPrimary,
    textAlign: 'center',
  },
});