import React, { useState, useRef, useCallback } from 'react';
import {
  View,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Image,
} from 'react-native';
import {
  Text,
  IconButton,
  Surface,
} from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';
import { ImagePicker } from './ImagePicker.jsx';

export const ChatInput = ({
  onSendMessage,
  onTyping,
  placeholder = 'Type a message...',
  disabled = false,
  maxLength = 1000,
}) => {
  const [inputText, setInputText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [isImagePickerVisible, setIsImagePickerVisible] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  
  const typingTimeoutRef = useRef(null);
  const textInputRef = useRef(null);

  const handleTextChange = useCallback((text) => {
    setInputText(text);
    
    if (text.length > 0 && !isTyping) {
      setIsTyping(true);
      onTyping(true);
    }
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    typingTimeoutRef.current = setTimeout(() => {
      if (isTyping) {
        setIsTyping(false);
        onTyping(false);
      }
    }, 2000);
  }, [isTyping, onTyping]);

  const handleSendMessage = useCallback(() => {
    const trimmedText = inputText.trim();
    
    if (selectedImage) {
      onSendMessage(
        trimmedText || 'Shared an image',
        'image',
        selectedImage
      );
      setSelectedImage(null);
    } else if (trimmedText) {
      onSendMessage(trimmedText, 'text');
    } else {
      return;
    }
    
    setInputText('');
    
    if (isTyping) {
      setIsTyping(false);
      onTyping(false);
    }
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
    
    textInputRef.current?.focus();
  }, [inputText, selectedImage, isTyping, onSendMessage, onTyping]);

  const handleImageSelected = useCallback((imageUri, imageType) => {
    setSelectedImage(imageUri);
  }, []);

  const handleRemoveImage = useCallback(() => {
    setSelectedImage(null);
  }, []);

  const canSend = (inputText.trim().length > 0 || selectedImage) && !disabled;

  return (
    <Surface style={styles.container}>
      <View style={styles.content}>
        {selectedImage && (
          <View style={styles.imagePreview}>
            <Image source={{ uri: selectedImage }} style={styles.previewImage} />
            <TouchableOpacity
              style={styles.removeImageButton}
              onPress={handleRemoveImage}
            >
              <Text style={styles.removeImageText}>×</Text>
            </TouchableOpacity>
          </View>
        )}
        
        <View style={styles.inputRow}>
          <IconButton
            icon="attachment"
            onPress={() => setIsImagePickerVisible(true)}
            disabled={disabled}
            style={styles.attachButton}
          />
          
          <TextInput
            ref={textInputRef}
            style={[
              styles.textInput,
              disabled && styles.textInputDisabled,
            ]}
            value={inputText}
            onChangeText={handleTextChange}
            placeholder={placeholder}
            placeholderTextColor={colors.outline}
            multiline
            maxLength={maxLength}
            editable={!disabled}
          />
          
          <TouchableOpacity
            style={[
              styles.sendButton,
              canSend ? styles.sendButtonActive : styles.sendButtonInactive,
            ]}
            onPress={handleSendMessage}
            disabled={!canSend}
          >
            <Text
              style={[
                styles.sendButtonText,
                canSend ? styles.sendButtonTextActive : styles.sendButtonTextInactive,
              ]}
            >
              Send
            </Text>
          </TouchableOpacity>
        </View>
        
        {inputText.length > maxLength * 0.8 && (
          <View style={styles.characterCount}>
            <Text
              style={[
                styles.characterCountText,
                inputText.length >= maxLength && styles.characterCountError,
              ]}
            >
              {inputText.length}/{maxLength}
            </Text>
          </View>
        )}
      </View>
      
      <ImagePicker
        visible={isImagePickerVisible}
        onDismiss={() => setIsImagePickerVisible(false)}
        onImageSelected={handleImageSelected}
      />
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    borderTopWidth: 1,
    borderTopColor: colors.outline,
    elevation: 4,
  },
  content: {
    backgroundColor: colors.surface,
  },
  imagePreview: {
    margin: spacing.md,
    marginBottom: spacing.sm,
  },
  previewImage: {
    width: 80,
    height: 80,
    borderRadius: 8,
    backgroundColor: colors.surfaceVariant,
  },
  removeImageButton: {
    position: 'absolute',
    top: -8,
    right: -8,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: colors.error,
    justifyContent: 'center',
    alignItems: 'center',
  },
  removeImageText: {
    color: colors.onError,
    fontSize: 16,
    fontWeight: 'bold',
    lineHeight: 20,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: spacing.md,
  },
  attachButton: {
    marginRight: spacing.sm,
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.outline,
    borderRadius: 20,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    maxHeight: 100,
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    backgroundColor: colors.surface,
    textAlignVertical: 'top',
  },
  textInputDisabled: {
    backgroundColor: colors.surfaceVariant,
    opacity: 0.6,
  },
  sendButton: {
    marginLeft: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 20,
    minWidth: 60,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonActive: {
    backgroundColor: colors.primary,
  },
  sendButtonInactive: {
    backgroundColor: colors.surfaceVariant,
  },
  sendButtonText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
  },
  sendButtonTextActive: {
    color: colors.onPrimary,
  },
  sendButtonTextInactive: {
    color: colors.outline,
  },
  characterCount: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
  },
  characterCountText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  characterCountError: {
    color: colors.error,
  },
});