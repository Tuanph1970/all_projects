/**
 * Knowledge QA Service
 * Handles API calls for the Knowledge QA feature (Graph RAG with Neo4j + Ollama)
 */
import { API_ENDPOINTS } from '../constants/api';

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };
};

/**
 * Ask a question via SSE streaming
 * @param {string} question - The question to ask
 * @param {string} sessionId - Chat session ID
 * @param {function} onToken - Callback for each token received
 * @param {function} onSources - Callback when sources are received
 * @param {function} onDone - Callback when streaming is complete
 * @param {function} onError - Callback on error
 * @returns {AbortController} - Controller to abort the request
 */
export const askQuestion = (question, sessionId, { onToken, onSources, onDone, onError }) => {
  const controller = new AbortController();

  fetch(API_ENDPOINTS.KNOWLEDGE_QA_CHAT, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      question,
      session_id: sessionId,
      max_context_notes: 5,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token' && onToken) {
              onToken(data.data);
            } else if (data.type === 'sources' && onSources) {
              onSources(data.data);
            } else if (data.type === 'done' && onDone) {
              onDone();
            } else if (data.type === 'error' && onError) {
              onError(data.data);
            }
          } catch (e) {
            // Skip malformed JSON
          }
        }
      }

      // Process any remaining buffer
      if (buffer.startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.slice(6));
          if (data.type === 'done' && onDone) onDone();
        } catch (e) {
          // Skip
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError' && onError) {
        onError(err.message);
      }
    });

  return controller;
};

/**
 * Get chat history for a session
 */
export const getHistory = async (sessionId) => {
  try {
    const response = await fetch(API_ENDPOINTS.KNOWLEDGE_QA_HISTORY(sessionId), {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { success: true, data: await response.json() };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * Clear a chat session
 */
export const clearSession = async (sessionId) => {
  try {
    const response = await fetch(API_ENDPOINTS.KNOWLEDGE_QA_CLEAR(sessionId), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { success: true, data: await response.json() };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * Search notes in the knowledge base
 */
export const searchNotes = async (query, limit = 10) => {
  try {
    const params = new URLSearchParams({ q: query, limit: limit.toString() });
    const response = await fetch(`${API_ENDPOINTS.KNOWLEDGE_QA_SEARCH}?${params}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { success: true, data: await response.json() };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

/**
 * Get knowledge graph statistics
 */
export const getGraphStats = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.KNOWLEDGE_QA_STATS, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { success: true, data: await response.json() };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

export default {
  askQuestion,
  getHistory,
  clearSession,
  searchNotes,
  getGraphStats,
};
