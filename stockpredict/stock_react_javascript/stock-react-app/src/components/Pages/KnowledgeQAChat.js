import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Trash2, Database, FileText, ChevronDown, ChevronUp, AlertCircle, Loader2 } from 'lucide-react';
import { askQuestion, getHistory, clearSession, getGraphStats } from '../../services/knowledgeQAService';
import '../../styles/knowledge-qa.css';

const SESSION_KEY = 'knowledge_qa_session_id';

const getSessionId = () => {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = `kqa-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
};

const KnowledgeQAChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const messagesEndRef = useRef(null);
  const abortRef = useRef(null);
  const sessionId = useRef(getSessionId());

  // Load history and stats on mount
  useEffect(() => {
    loadHistory();
    loadStats();
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadHistory = async () => {
    const result = await getHistory(sessionId.current);
    if (result.success && result.data.messages?.length > 0) {
      setMessages(result.data.messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        sources: m.sources || [],
        timestamp: m.timestamp,
      })));
    }
  };

  const loadStats = async () => {
    const result = await getGraphStats();
    if (result.success) {
      setStats(result.data);
    }
  };

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isStreaming) return;

    setInput('');
    setError(null);

    // Add user message
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      sources: [],
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    // Add placeholder assistant message
    const assistantId = `assistant-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }]);

    setIsStreaming(true);

    abortRef.current = askQuestion(question, sessionId.current, {
      onToken: (token) => {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: m.content + token }
            : m
        ));
      },
      onSources: (sources) => {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, sources: sources || [] }
            : m
        ));
      },
      onDone: () => {
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, isStreaming: false }
            : m
        ));
        setIsStreaming(false);
      },
      onError: (err) => {
        setError(err);
        setIsStreaming(false);
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: m.content || 'An error occurred while generating the response.', isStreaming: false }
            : m
        ));
      },
    });
  }, [input, isStreaming]);

  const handleClear = async () => {
    if (isStreaming && abortRef.current) {
      abortRef.current.abort();
    }
    await clearSession(sessionId.current);
    setMessages([]);
    setError(null);
    setIsStreaming(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleSources = (msgId) => {
    setExpandedSources(prev => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="kqa-container">
      {/* Header */}
      <div className="kqa-header">
        <div className="kqa-header-left">
          <Database size={20} />
          <h2>Knowledge QA</h2>
          {stats && (
            <div className="kqa-stats">
              <span>{stats.total_notes} notes</span>
              <span>{stats.total_tags} tags</span>
              <span>{stats.total_links} links</span>
            </div>
          )}
        </div>
        <button
          className="kqa-clear-btn"
          onClick={handleClear}
          title="Clear chat"
        >
          <Trash2 size={16} />
          <span>Clear</span>
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="kqa-error">
          <AlertCircle size={16} />
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Messages */}
      <div className="kqa-messages">
        {messages.length === 0 && (
          <div className="kqa-empty">
            <Database size={48} className="kqa-empty-icon" />
            <h3>Ask anything about your knowledge base</h3>
            <p>Your questions will be answered using your Obsidian notes stored in Neo4j.</p>
            <div className="kqa-suggestions">
              {[
                'What topics are covered in my notes?',
                'Summarize my notes about investing',
                'What are the key concepts in my knowledge base?',
              ].map((suggestion, i) => (
                <button
                  key={i}
                  className="kqa-suggestion"
                  onClick={() => {
                    setInput(suggestion);
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`kqa-message kqa-message-${msg.role}`}>
            <div className="kqa-message-avatar">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="kqa-message-body">
              <div className="kqa-message-content">
                {msg.content}
                {msg.isStreaming && <span className="kqa-cursor">▊</span>}
              </div>

              {/* Sources panel */}
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div className="kqa-sources">
                  <button
                    className="kqa-sources-toggle"
                    onClick={() => toggleSources(msg.id)}
                  >
                    <FileText size={14} />
                    <span>{msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}</span>
                    {expandedSources[msg.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {expandedSources[msg.id] && (
                    <div className="kqa-sources-list">
                      {msg.sources.map((source, i) => (
                        <div key={i} className="kqa-source-item">
                          <div className="kqa-source-title">
                            <FileText size={12} />
                            <span>{source.title}</span>
                            <span className="kqa-source-score">
                              {(source.relevance_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          {source.snippet && (
                            <p className="kqa-source-snippet">{source.snippet.slice(0, 200)}...</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="kqa-input-area">
        <div className="kqa-input-wrapper">
          <textarea
            className="kqa-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your knowledge base..."
            rows={1}
            disabled={isStreaming}
          />
          <button
            className="kqa-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
          >
            {isStreaming ? <Loader2 size={18} className="kqa-spinner" /> : <Send size={18} />}
          </button>
        </div>
        <p className="kqa-input-hint">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};

export default KnowledgeQAChat;
