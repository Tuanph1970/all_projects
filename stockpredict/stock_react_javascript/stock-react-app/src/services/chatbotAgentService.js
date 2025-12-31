/**
 * Chatbot Agent Service
 * Handles communication with LLM-based agent backend
 */

import httpClient from './httpClient';
import { API_ENDPOINTS } from '../constants/api';

/**
 * Ask a question to the chatbot
 * @param {string} question - The user's question
 * @param {string} userId - Optional user ID
 * @returns {Promise<Object>} Agent response
 */
export const askQuestion = async (question, userId = null) => {
  const response = await httpClient.post(API_ENDPOINTS.CHATBOT_ASK, {
    question,
    user_id: userId
  });

  if (!response.success) {
    console.error('Error asking question:', response.error);
    throw response.error;
  }

  return response.data;
};

/**
 * Get chatbot capabilities
 * @returns {Promise<Object>} Capabilities object
 */
export const getChatbotCapabilities = async () => {
  const response = await httpClient.get(API_ENDPOINTS.CHATBOT_CAPABILITIES);

  if (!response.success) {
    console.error('Error fetching capabilities:', response.error);
    throw response.error;
  }

  return response.data;
};

/**
 * Get available question categories
 * @returns {Promise<Object>} Categories object
 */
export const getQuestionCategories = async () => {
  const response = await httpClient.get(API_ENDPOINTS.CHATBOT_CATEGORIES);

  if (!response.success) {
    console.error('Error fetching categories:', response.error);
    return { categories: [] }; // Return empty categories on error
  }

  return response.data;
};

/**
 * Submit feedback on chatbot response
 * @param {Object} feedbackData - Feedback data
 * @returns {Promise<Object>} Success response
 */
export const submitFeedback = async (feedbackData) => {
  const response = await httpClient.post(API_ENDPOINTS.CHATBOT_FEEDBACK, feedbackData);

  if (!response.success) {
    console.error('Error submitting feedback:', response.error);
    throw response.error;
  }

  return response.data;
};

/**
 * Check chatbot service health
 * @returns {Promise<Object>} Health status
 */
export const checkHealth = async () => {
  const response = await httpClient.get(API_ENDPOINTS.CHATBOT_HEALTH);

  if (!response.success) {
    console.error('Error checking health:', response.error);
    throw response.error;
  }

  return response.data;
};

const chatbotAgentService = {
  askQuestion,
  getChatbotCapabilities,
  getQuestionCategories,
  submitFeedback,
  checkHealth
};

export default chatbotAgentService;
