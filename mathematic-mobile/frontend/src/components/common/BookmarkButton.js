import React from 'react';
import { TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSelector, useDispatch } from 'react-redux';
import { useTheme } from '../../hooks/useTheme';
import {
  addBookmark,
  removeBookmark,
  selectIsBookmarked,
  selectBookmarkById,
} from '../../store/slices/bookmarkSlice';

/**
 * BookmarkButton Component
 * Displays a bookmark icon that toggles bookmark state
 */
const BookmarkButton = ({ solution, size = 24, style }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const dispatch = useDispatch();
  
  const isBookmarked = useSelector((state) =>
    selectIsBookmarked(state, solution?.id)
  );
  const bookmark = useSelector((state) =>
    selectBookmarkById(state, solution?.id)
  );

  const handleToggleBookmark = async () => {
    try {
      if (isBookmarked) {
        Alert.alert(
          'Remove Bookmark',
          'Are you sure you want to remove this bookmark?',
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Remove',
              style: 'destructive',
              onPress: () => dispatch(removeBookmark(solution.id)),
            },
          ]
        );
      } else {
        await dispatch(addBookmark(solution)).unwrap();
        Alert.alert('Success', 'Solution bookmarked!');
      }
    } catch (error) {
      if (error !== 'Already bookmarked') {
        Alert.alert('Error', 'Failed to update bookmark');
      }
    }
  };

  return (
    <TouchableOpacity
      style={[styles.button, style]}
      onPress={handleToggleBookmark}
      activeOpacity={0.7}
    >
      <Ionicons
        name={isBookmarked ? 'bookmark' : 'bookmark-outline'}
        size={size}
        color={isBookmarked ? colors.primary : colors.text}
      />
    </TouchableOpacity>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    button: {
      padding: 4,
      alignItems: 'center',
      justifyContent: 'center',
    },
  });

export default BookmarkButton;
