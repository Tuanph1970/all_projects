# Stock Market Chatbot Agent System

## Overview

An intelligent chatbot system for Vietnamese stock market analysis powered by LLM-based agent routing. The system uses design patterns (Strategy, Chain of Responsibility, Factory) to route user questions to specialized agents that handle different categories of stock market queries.

## Architecture

### Design Patterns

1. **Strategy Pattern**: Each agent implements a strategy for handling specific question categories
2. **Chain of Responsibility**: Questions are routed through a chain of agents until one can handle it
3. **Factory Pattern**: Agent creation and initialization through orchestrator
4. **Singleton Pattern**: Single orchestrator instance manages all agents

### Components

```
┌─────────────────────────────────────────────────────────┐
│                  User Question                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           LLMQuestionRouter                              │
│  - Pattern matching and NLP                              │
│  - Entity extraction                                     │
│  - Category classification                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│        ChatbotAgentOrchestrator                         │
│  - Agent management                                      │
│  - Response coordination                                 │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┬───────────────┐
         ▼                       ▼               ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ MarketOverview   │  │StockPerformance  │  │ SectorAnalysis   │
│     Agent        │  │     Agent        │  │     Agent        │
└──────────────────┘  └──────────────────┘  └──────────────────┘

         ▼                       ▼               ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  MarketTrends    │  │TechnicalIndicator│  │  Prediction      │
│     Agent        │  │     Agent        │  │     Agent        │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Question Categories

### 1. Market Overview (`market_overview`)
**Handles**: Market indices, trading volumes, market volatility

**Example Questions**:
- "What is the current VN-Index level?"
- "How did the VN-Index perform today?"
- "What's the VN30 Index movement this week?"
- "What's the trading volume on HOSE today?"

**Agent**: `MarketOverviewAgent`

**Data Sources**: Market Service, VCI Market Data

---

### 2. Stock Performance (`stock_performance`)
**Handles**: Individual stock prices, top gainers/losers, trading volumes

**Example Questions**:
- "What's the current price of VCB stock?"
- "Which stocks are gaining the most today?"
- "Show me the top 10 stocks by trading volume"
- "What stocks hit ceiling price today?"

**Agent**: `StockPerformanceAgent`

**Data Sources**: Company Service, Market Data

---

### 3. Sector Analysis (`sector_analysis`)
**Handles**: Sector performance, industry comparisons

**Example Questions**:
- "Which sectors are leading the market today?"
- "How is the banking sector performing?"
- "What's happening with real estate stocks?"

**Agent**: `SectorAnalysisAgent`

**Data Sources**: Market Service, Sector Data

---

### 4. Market Trends (`market_trends`)
**Handles**: Trend direction, market breadth, foreign investor activity, sentiment

**Example Questions**:
- "Is the market in an uptrend or downtrend?"
- "What's the market breadth today?"
- "Are foreign investors buying or selling?"
- "Is there a bullish or bearish sentiment?"

**Agent**: `MarketTrendsAgent`

**Data Sources**: Market Service, Trend Analysis

---

### 5. Technical Indicators (`technical_indicators`)
**Handles**: RSI, MACD, moving averages, chart patterns

**Example Questions**:
- "What's the RSI for VCB?"
- "Show me the MACD for VNINDEX"
- "Calculate 20-day moving average for HPG"

**Agent**: `TechnicalIndicatorAgent`

**Data Sources**: Technical Analysis Service

---

### 6. Predictions (`predictions`)
**Handles**: Price predictions, market outlook, forecasts

**Example Questions**:
- "Will the market go up or down tomorrow?"
- "What's the outlook for VN-Index this week?"
- "Predict the price of VCB for next month"

**Agent**: `PredictionAgent`

**Data Sources**: Time Series Service, ML Models (RNN, XGBoost, etc.)

---

## API Endpoints

### POST `/api/chatbot/ask/`
Ask a question to the chatbot

**Request**:
```json
{
  "question": "What is the current VN-Index level?",
  "user_id": "optional_user_id"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "index": "VNINDEX",
    "current_level": 1250.45,
    "change": 5.23,
    "change_percent": 0.42
  },
  "message": "Market overview for VNINDEX retrieved successfully",
  "category": "market_overview",
  "confidence": 0.95,
  "sources": ["VCI Market Data", "Stock Market Service"],
  "metadata": {
    "agent": "MarketOverviewAgent",
    "timestamp": "2025-10-07T10:30:00"
  }
}
```

---

### GET `/api/chatbot/capabilities/`
Get chatbot capabilities

**Response**:
```json
{
  "categories": ["market_overview", "stock_performance", ...],
  "agents": ["MarketOverviewAgent", "StockPerformanceAgent", ...],
  "sample_questions": [...]
}
```

---

### GET `/api/chatbot/categories/`
Get all question categories with examples

**Response**:
```json
{
  "categories": [
    {
      "name": "market_overview",
      "description": "Market indices and overview questions",
      "examples": [...]
    },
    ...
  ]
}
```

---

### POST `/api/chatbot/feedback/`
Submit feedback on chatbot responses

**Request**:
```json
{
  "question": "...",
  "response_helpful": true,
  "feedback_text": "Great answer!",
  "category": "market_overview"
}
```

---

### GET `/api/chatbot/health/`
Check chatbot service health

**Response**:
```json
{
  "status": "healthy",
  "agents_count": 6,
  "timestamp": "2025-10-07T10:30:00"
}
```

---

## Integration Guide

### Backend Integration

1. **Import the orchestrator**:
```python
from services.chatbot_agent_service import ChatbotAgentOrchestrator

orchestrator = ChatbotAgentOrchestrator()
```

2. **Process questions**:
```python
response = orchestrator.process_question("What is VN-Index level?")
```

3. **Access response data**:
```python
if response.success:
    data = response.data
    category = response.category
    confidence = response.confidence
```

### Frontend Integration

1. **Import service**:
```javascript
import chatbotAgentService from '../../services/chatbotAgentService';
```

2. **Ask questions**:
```javascript
const response = await chatbotAgentService.askQuestion(
  "What is the current VN-Index level?"
);
```

3. **Handle responses**:
```javascript
if (response.success) {
  console.log(response.data);
  console.log(response.category);
  console.log(response.confidence);
}
```

---

## Adding New Agents

To add a new agent for a new question category:

1. **Define category** in `QuestionCategory` enum:
```python
class QuestionCategory(Enum):
    NEW_CATEGORY = "new_category"
```

2. **Create agent class**:
```python
class NewCategoryAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.supported_categories = [QuestionCategory.NEW_CATEGORY]

    def can_handle(self, context: QuestionContext) -> bool:
        return context.category == QuestionCategory.NEW_CATEGORY

    def process(self, context: QuestionContext) -> AgentResponse:
        # Implementation
        pass
```

3. **Register in orchestrator**:
```python
def _initialize_agents(self) -> List[BaseAgent]:
    return [
        # ... existing agents
        NewCategoryAgent(),
    ]
```

4. **Add routing patterns**:
```python
def _initialize_patterns(self) -> Dict[QuestionCategory, List[str]]:
    return {
        # ... existing patterns
        QuestionCategory.NEW_CATEGORY: ['keyword1', 'keyword2'],
    }
```

---

## Extending Agents

### Adding Data Sources

Agents can be extended to use additional data sources:

```python
class StockPerformanceAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.company_service = CompanyService()
        self.new_data_source = NewDataSource()  # Add new source

    def process(self, context: QuestionContext) -> AgentResponse:
        # Use new data source
        data = self.new_data_source.get_data(...)
        return self._create_response(...)
```

### Improving Question Router

Add more sophisticated NLP using libraries like spaCy or transformers:

```python
import spacy

class LLMQuestionRouter:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        # ... existing code

    def _extract_entities(self, question: str, category: QuestionCategory):
        doc = self.nlp(question)
        entities = {}

        for ent in doc.ents:
            if ent.label_ == "ORG":
                entities['ticker'] = ent.text

        # ... more advanced NLP
        return entities
```

---

## Performance Optimization

### Caching

Responses are automatically cached for 5 minutes:

```python
cache_key = f"chatbot_q_{hash(question.lower())}"
cached_response = cache.get(cache_key)

if cached_response:
    return cached_response

# Process and cache
cache.set(cache_key, response_data, timeout=300)
```

### Parallel Processing

For questions requiring multiple agents:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor() as executor:
    futures = [executor.submit(agent.process, context) for agent in agents]
    results = [f.result() for f in futures]
```

---

## Testing

### Unit Tests

```python
import unittest
from services.chatbot_agent_service import MarketOverviewAgent, QuestionContext, QuestionCategory

class TestMarketOverviewAgent(unittest.TestCase):
    def setUp(self):
        self.agent = MarketOverviewAgent()

    def test_can_handle_market_overview(self):
        context = QuestionContext(
            question="What is VN-Index?",
            category=QuestionCategory.MARKET_OVERVIEW,
            extracted_entities={},
            metadata={},
            timestamp=datetime.now()
        )
        self.assertTrue(self.agent.can_handle(context))

    def test_process_returns_response(self):
        context = QuestionContext(
            question="What is VN-Index level?",
            category=QuestionCategory.MARKET_OVERVIEW,
            extracted_entities={'intent': 'current_level', 'index': 'VNINDEX'},
            metadata={},
            timestamp=datetime.now()
        )
        response = self.agent.process(context)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.data)
```

### Integration Tests

```python
def test_end_to_end_question():
    orchestrator = ChatbotAgentOrchestrator()
    response = orchestrator.process_question("What is the current VN-Index level?")

    assert response.success == True
    assert response.category == QuestionCategory.MARKET_OVERVIEW
    assert response.data is not None
```

---

## Future Enhancements

### 1. Machine Learning Integration
- Use ML models for better question classification
- Train on historical question-answer pairs
- Implement reinforcement learning based on user feedback

### 2. Multi-Language Support
- Add Vietnamese language processing
- Support mixed English-Vietnamese queries

### 3. Conversational Context
- Maintain conversation history
- Support follow-up questions
- Implement context-aware responses

### 4. Advanced Analytics
- Track popular questions
- Analyze user behavior
- Optimize agent performance

### 5. Real-time Data
- WebSocket integration for live updates
- Real-time market data streaming
- Push notifications for alerts

---

## Troubleshooting

### Common Issues

1. **Agent not responding**
   - Check agent initialization in orchestrator
   - Verify routing patterns are correct
   - Check logs for errors

2. **Incorrect category routing**
   - Review keyword patterns
   - Add more specific patterns
   - Improve entity extraction

3. **Performance issues**
   - Enable caching
   - Optimize database queries
   - Use connection pooling

4. **Data accuracy**
   - Verify data source connections
   - Check API endpoints
   - Validate data transformations

---

## Support & Contact

For issues, questions, or contributions:
- GitHub Issues: [Link to repository]
- Documentation: [Link to full docs]
- Email: support@stockpredict.com

---

## License

[Your License Here]

---

## Changelog

### Version 1.0.0 (2025-10-07)
- Initial release
- 6 specialized agents
- LLM-based question routing
- REST API endpoints
- React frontend integration
