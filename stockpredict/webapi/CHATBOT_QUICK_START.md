# Chatbot Agent System - Quick Start Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Django REST Framework
- React 16.8+
- Node.js 14+

### Backend Setup

1. **Install dependencies**:
```bash
cd webapi
pip install -r requirements.txt
```

2. **Run migrations** (if needed):
```bash
python manage.py migrate
```

3. **Start Django server**:
```bash
python manage.py runserver
```

4. **Test the chatbot endpoint**:
```bash
curl -X POST http://localhost:8000/api/chatbot/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the current VN-Index level?"}'
```

### Frontend Setup

1. **Install dependencies**:
```bash
cd stock_react_javascript/stock-react-app
npm install
```

2. **Import CSS in your main App.js**:
```javascript
import './styles/chatbot-agent.css';
```

3. **Add route to ChatbotAgent**:
```javascript
import ChatbotAgent from './components/Pages/ChatbotAgent';

// In your routes
<Route path="/chatbot" component={ChatbotAgent} />
```

4. **Start React app**:
```bash
npm start
```

5. **Access chatbot**:
Open browser: `http://localhost:3000/chatbot`

---

## 📝 Usage Examples

### Backend (Python)

```python
from services.chatbot_agent_service import ChatbotAgentOrchestrator

# Initialize orchestrator
orchestrator = ChatbotAgentOrchestrator()

# Ask a question
response = orchestrator.process_question("What is the current VN-Index level?")

# Access response
if response.success:
    print(f"Category: {response.category.value}")
    print(f"Data: {response.data}")
    print(f"Confidence: {response.confidence}")
    print(f"Sources: {response.sources}")
```

### Frontend (JavaScript/React)

```javascript
import chatbotAgentService from '../../services/chatbotAgentService';

// Ask a question
const askQuestion = async (question) => {
  try {
    const response = await chatbotAgentService.askQuestion(question);

    if (response.success) {
      console.log('Category:', response.category);
      console.log('Data:', response.data);
      console.log('Confidence:', response.confidence);
    } else {
      console.error('Error:', response.message);
    }
  } catch (error) {
    console.error('Failed to ask question:', error);
  }
};

// Get capabilities
const getCapabilities = async () => {
  const capabilities = await chatbotAgentService.getChatbotCapabilities();
  console.log('Supported categories:', capabilities.categories);
  console.log('Available agents:', capabilities.agents);
};
```

---

## 🎯 Sample Questions by Category

### Market Overview
```
✅ "What is the current VN-Index level?"
✅ "How did the VN-Index perform today?"
✅ "What's the VN30 Index movement this week?"
✅ "What's the trading volume on HOSE today?"
✅ "How volatile is the Vietnamese stock market?"
```

### Stock Performance
```
✅ "What's the current price of VCB stock?"
✅ "Which stocks are gaining the most today?"
✅ "Show me the top 10 stocks by trading volume"
✅ "What stocks hit ceiling price today?"
✅ "What's the 52-week high for HPG?"
```

### Sector Analysis
```
✅ "Which sectors are leading the market today?"
✅ "How is the banking sector performing?"
✅ "What's happening with real estate stocks?"
✅ "Are tech stocks rising or falling?"
```

### Market Trends
```
✅ "Is the market in an uptrend or downtrend?"
✅ "What's the market breadth today?"
✅ "Are foreign investors buying or selling?"
✅ "Is there a bullish or bearish sentiment?"
```

### Technical Indicators
```
✅ "What's the RSI for VCB?"
✅ "Show me the MACD for VNINDEX"
✅ "Calculate 20-day moving average for HPG"
✅ "What are the technical indicators for VHM?"
```

### Predictions
```
✅ "Will the market go up or down tomorrow?"
✅ "What's the outlook for VN-Index this week?"
✅ "Predict the price of VCB for next month"
✅ "Is now a good time to invest?"
```

---

## 🔧 Configuration

### Customize Agent Behavior

Edit `/webapi/services/chatbot_agent_service.py`:

```python
class MarketOverviewAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.market_service = StockMarketService()
        # Add custom configuration
        self.cache_timeout = 300  # 5 minutes
        self.data_source = "VCI"  # or "TCBS"
```

### Add Custom Patterns

```python
def _initialize_patterns(self) -> Dict[QuestionCategory, List[str]]:
    return {
        QuestionCategory.MARKET_OVERVIEW: [
            'vn-index', 'vn30', 'hnx',
            'your-custom-keyword'  # Add here
        ],
    }
```

### Configure Cache Timeout

In `/webapi/stock/view_chatbot_agent.py`:

```python
# Change cache timeout (default 300 seconds)
cache.set(cache_key, response_data, timeout=600)  # 10 minutes
```

---

## 🧪 Testing

### Test Individual Agents

```python
from services.chatbot_agent_service import (
    MarketOverviewAgent,
    QuestionContext,
    QuestionCategory
)
from datetime import datetime

# Create test context
context = QuestionContext(
    question="What is VN-Index?",
    category=QuestionCategory.MARKET_OVERVIEW,
    extracted_entities={'intent': 'current_level'},
    metadata={},
    timestamp=datetime.now()
)

# Test agent
agent = MarketOverviewAgent()
response = agent.process(context)

print(f"Success: {response.success}")
print(f"Data: {response.data}")
```

### Test API Endpoints

```bash
# Test ask endpoint
curl -X POST http://localhost:8000/api/chatbot/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the current VN-Index level?"}'

# Test capabilities
curl http://localhost:8000/api/chatbot/capabilities/

# Test categories
curl http://localhost:8000/api/chatbot/categories/

# Test health
curl http://localhost:8000/api/chatbot/health/
```

---

## 🐛 Troubleshooting

### Issue: "Agent not found"
**Solution**: Check that all agents are registered in `ChatbotAgentOrchestrator._initialize_agents()`

### Issue: "Incorrect category routing"
**Solution**: Review and update keyword patterns in `LLMQuestionRouter._initialize_patterns()`

### Issue: "No data returned"
**Solution**:
- Verify data service connections
- Check database connectivity
- Ensure external APIs are accessible

### Issue: "Frontend can't connect to backend"
**Solution**:
- Check CORS settings in Django
- Verify API base URL in frontend
- Check network/firewall settings

---

## 📚 Additional Resources

- [Full Documentation](./CHATBOT_AGENT_DOCUMENTATION.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [API Reference](./API_REFERENCE.md)

---

## 🎨 Customization Tips

### 1. Change UI Theme

Edit `/stock_react_javascript/stock-react-app/src/styles/chatbot-agent.css`:

```css
.chatbot-agent-container {
  background: linear-gradient(135deg, #your-color1 0%, #your-color2 100%);
}
```

### 2. Add Custom Response Formatting

In `ChatbotAgent.js`, add a new format function:

```javascript
const formatCustomCategory = (data, message) => {
  // Your custom formatting logic
  return formattedString;
};
```

### 3. Integrate with Existing Services

```python
class StockPerformanceAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.company_service = CompanyService()
        self.your_service = YourCustomService()  # Add here
```

---

## ✅ Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Database connected
- [ ] All agents initialized
- [ ] API endpoints accessible
- [ ] UI loads correctly
- [ ] Sample questions work
- [ ] Responses formatted properly

---

## 🚀 Next Steps

1. **Test with real data**: Connect to live market data sources
2. **Add authentication**: Implement user authentication
3. **Enhance predictions**: Integrate ML models
4. **Add analytics**: Track usage and performance
5. **Deploy to production**: Set up production environment

---

## 📞 Support

For help:
- Check [Documentation](./CHATBOT_AGENT_DOCUMENTATION.md)
- Review [Architecture](./ARCHITECTURE.md)
- Contact: support@stockpredict.com

---

## 🎉 You're All Set!

Your intelligent stock market chatbot is ready to use. Try asking questions and explore the capabilities!

Example:
```
"What is the current VN-Index level?"
"Which stocks are gaining the most today?"
"Is the banking sector performing well?"
"Will the market go up tomorrow?"
```
