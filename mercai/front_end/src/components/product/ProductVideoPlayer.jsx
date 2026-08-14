/**
 * ProductVideoPlayer Component
 * Displays product video with play button overlay for customer viewing
 */
import React, { useState, useRef } from 'react';
import { View, StyleSheet, TouchableOpacity, Text } from 'react-native';
import { ResizeMode, Video } from 'expo-av';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing } from '../../constants/theme';

const ProductVideoPlayer = ({ video }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const videoRef = useRef(null);

  if (!video) return null;

  const handlePlayPress = async () => {
    if (videoRef.current) {
      if (isPlaying) {
        await videoRef.current.pauseAsync();
      } else {
        await videoRef.current.playAsync();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handlePlayerReady = () => {
    setIsReady(true);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.videoWrapper}>
        <Video
          ref={videoRef}
          source={{ uri: video.video_url }}
          style={styles.video}
          useNativeControls={false} // Custom controls
          resizeMode={ResizeMode.COVER}
          shouldPlay={isPlaying}
          isLooping
          onReadyForDisplay={handlePlayerReady}
          onPlaybackStatusUpdate={(status) => {
            if (status.isLoaded) {
              setIsPlaying(status.isPlaying);
            }
          }}
        />

        {/* Play Button Overlay */}
        {!isPlaying && (
          <TouchableOpacity 
            style={styles.playButtonOverlay} 
            onPress={handlePlayPress}
            activeOpacity={0.8}
          >
            <View style={styles.playButton}>
              <Icon name="play-arrow" size={40} color={colors.white} />
            </View>
          </TouchableOpacity>
        )}

        {/* Video Duration Badge */}
        <View style={styles.durationBadge}>
          <Icon name="access-time" size={12} color={colors.white} />
          <Text style={styles.durationText}>
            {formatDuration(video.duration_seconds)}
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.medium,
  },
  videoWrapper: {
    position: 'relative',
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: colors.black,
    aspectRatio: 16 / 9,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  video: {
    width: '100%',
    height: '100%',
  },
  playButtonOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  playButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: colors.white,
  },
  durationBadge: {
    position: 'absolute',
    bottom: 12,
    right: 12,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  durationText: {
    color: colors.white,
    fontSize: 12,
    fontWeight: '600',
  },
});

export default ProductVideoPlayer;
