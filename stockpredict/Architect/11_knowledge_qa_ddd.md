# 11 — Knowledge-QA Service — Deep Dive (DDD + Graph RAG)

## 11.1 Architecture Overview

This service is the most architecturally sophisticated in the platform. It implements full DDD layering with Hexagonal Architecture (Ports & Adapters) and uses Graph RAG (Retrieval-Augmented Generation) for knowledge-grounded Q&A.

```mermaid
flowchart TD
    subgraph EXTERNAL_IN["External Actors (Driving Side)"]
        USER_API["User via REST API\nPOST /chat\nGET /search\nGET /stats"]
    end

    subgraph HEXAGON["Hexagonal Architecture — knowledge-qa-service"]
        subgraph API_ADAPTER["Primary Adapters (API)"]
            ROUTER["knowledge_qa_router.py\nFastAPI routes\nPydantic schemas\nDependency injection"]
            DEPS["dependencies.py\nUseCase factories\nRepository injection"]
            ERR["error_handlers.py\nException → HTTP status mapping"]
            MW["middleware.py\nRequest logging\nTiming\nAuth validation"]
        end

        subgraph APP["Application Layer (Use Cases)"]
            UC1["AskQuestion\nUseCase\n\n1. Parse question\n2. Retrieve graph context\n3. Generate LLM answer\n4. Store in session\n5. Return response + citations"]
            UC2["GetChatHistory\nUseCase\n\n1. Load session\n2. Return messages[]"]
            UC3["SearchNotes\nUseCase\n\n1. Parse search query\n2. Query graph\n3. Return ranked notes[]"]
            UC4["GetGraphStats\nUseCase\n\n1. Query graph metadata\n2. Return node/edge counts"]
            UC5["ClearSession\nUseCase\n\n1. Delete session\n2. Return confirmation"]
        end

        subgraph DOMAIN["Domain Layer (Core Business Logic)"]
            subgraph ENTITIES["Entities"]
                E1["ChatSession\n- session_id\n- user_id\n- messages[]\n- created_at"]
                E2["ChatMessage\n- message_id\n- role (user|assistant)\n- content\n- references[]"]
                E3["KnowledgeNote\n- note_id\n- title\n- content\n- tags[]\n- source"]
            end

            subgraph VALUE_OBJECTS["Value Objects (Immutable)"]
                VO1["SearchQuery\n- query_text\n- max_results\n- filters\n+ normalize()"]
                VO2["GraphContext\n- relevant_notes[]\n- relationships[]\n- relevance_score\n+ format()"]
                VO3["LLMResponse\n- answer\n- citations[]\n- confidence\n- model_used"]
                VO4["NoteReference\n- note_id\n- title\n- relevance_score\n- excerpt"]
            end

            subgraph DOMAIN_SERVICES["Domain Services"]
                DS1["QueryUnderstanding\n- extractKeywords()\n- identifyEntities()\n- buildSearchQuery()"]
                DS2["GraphRetrieval\n- searchNotes(query)\n- getRelatedNotes(id)\n- buildContext()"]
                DS3["AnswerGeneration\n- buildPrompt(ctx, question)\n- callLLM(prompt)\n- extractCitations()"]
            end

            subgraph PORTS["Ports (Interfaces)"]
                P1["LLMPort\n<<interface>>\n+ generate(prompt) LLMResponse\n+ embed(text) Vector"]
                P2["KnowledgeGraphRepository\n<<interface>>\n+ search(query) List~Note~\n+ getRelated(id) List~Note~\n+ getStats() Dict"]
                P3["ChatSessionRepository\n<<interface>>\n+ get(session_id) ChatSession\n+ save(session) void\n+ delete(session_id) void"]
            end
        end

        subgraph INFRA_ADAPTERS["Secondary Adapters (Infrastructure)"]
            OLLAMA_A["OllamaAdapter\nimplements LLMPort\n\n- ollama_host: str\n- model: str (llama2/mistral)\n+ generate(prompt) LLMResponse\n+ embed(text) Vector\n(POST :11434/api/generate)"]
            NEO4J_A["Neo4jKnowledgeGraphRepository\nimplements KnowledgeGraphRepository\n\n- driver: Neo4jDriver\n+ search(query) List~Note~\n+ getRelated(id) List~Note~\n+ getStats() Dict\n(Cypher queries)"]
            MEM_A["InMemorySessionRepository\nimplements ChatSessionRepository\n\n- sessions: Dict[str, ChatSession]\n(ephemeral, per-process)"]
            PROMPT_B["PromptBuilder\n\n- system_prompt: str\n+ buildRAGPrompt(ctx, question) str\n+ buildSearchPrompt(query) str"]
            FACTORY["GraphContextFactory\n\n+ fromNotes(notes) GraphContext\n+ withRelationships(notes, rels) GraphContext"]
        end
    end

    subgraph EXTERNAL_OUT["External Systems (Driven Side)"]
        NEO4J_DB[("Neo4j\nGraph Database\nbolt://host.docker.internal:7687")]
        OLLAMA_SVC["Ollama\nLocal LLM Service\nhttp://ollama:11434"]
    end

    USER_API --> ROUTER
    ROUTER --> DEPS
    DEPS --> UC1 & UC2 & UC3 & UC4 & UC5
    UC1 --> DS1 & DS2 & DS3
    DS1 --> VO1
    DS2 --> P2 & VO2
    DS3 --> P1 & VO3
    UC2 --> P3
    UC3 --> P2
    UC4 --> P2

    P1 -->|"impl"| OLLAMA_A
    P2 -->|"impl"| NEO4J_A
    P3 -->|"impl"| MEM_A
    DS3 --> PROMPT_B
    DS2 --> FACTORY

    OLLAMA_A --> OLLAMA_SVC
    NEO4J_A --> NEO4J_DB

    style HEXAGON fill:#f8fafc
    style API_ADAPTER fill:#dbeafe,stroke:#3b82f6
    style APP fill:#dcfce7,stroke:#22c55e
    style DOMAIN fill:#f3e8ff,stroke:#9333ea
    style INFRA_ADAPTERS fill:#fef9c3,stroke:#ca8a04
    style EXTERNAL_IN fill:#e0f2fe,stroke:#0284c7
    style EXTERNAL_OUT fill:#fee2e2,stroke:#ef4444
```

---

## 11.2 Graph RAG Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as API Router
    participant UC as AskQuestion UseCase
    participant QU as QueryUnderstanding Service
    participant GR as GraphRetrieval Service
    participant NEO4J as Neo4j Graph DB
    participant AG as AnswerGeneration Service
    participant PROMPT as PromptBuilder
    participant OLLAMA as Ollama LLM
    participant SESSION as Session Repository

    User->>API: POST /chat\n{"question": "RSI của VNM đang ở mức nào?", "session_id": "abc"}
    API->>UC: AskQuestionCommand{session_id, question}

    UC->>QU: parseQuestion(question)
    QU->>QU: Extract keywords: ["RSI", "VNM"]
    QU->>QU: Identify entities: stock=VNM, indicator=RSI
    QU-->>UC: SearchQuery{query="RSI VNM", filters=[stock:VNM, type:indicator]}

    UC->>GR: retrieveContext(searchQuery)
    GR->>NEO4J: MATCH (n:KnowledgeNote)\nWHERE n.content CONTAINS 'RSI'\n  AND (n)-[:MENTIONS]->(:Stock {symbol:'VNM'})\nRETURN n ORDER BY score DESC LIMIT 5
    NEO4J-->>GR: [note1: "RSI là chỉ số...", note2: "VNM RSI vượt 70..."]
    GR->>NEO4J: MATCH (n)-[:RELATED_TO]-(related) WHERE n.note_id IN [ids]\nRETURN related LIMIT 3
    NEO4J-->>GR: [note3: "Overbought conditions..."]
    GR-->>UC: GraphContext{notes: [note1, note2, note3], relevance: 0.87}

    UC->>AG: generateAnswer(question, graphContext)
    AG->>PROMPT: buildRAGPrompt(context, question)
    PROMPT-->>AG: """Bạn là chuyên gia phân tích chứng khoán.\nDựa trên thông tin sau:\n[note1 content]\n[note2 content]\n[note3 content]\n\nHãy trả lời: RSI của VNM đang ở mức nào?\nChỉ sử dụng thông tin đã cung cấp."""
    AG->>OLLAMA: POST /api/generate {model:"llama2", prompt:...}
    OLLAMA-->>AG: "RSI của VNM hiện tại đang ở mức 68, tiến gần vùng overbought (>70)..."

    AG-->>UC: LLMResponse{answer: "...", citations: [note1_id, note2_id], confidence: 0.82}

    UC->>SESSION: save(ChatMessage{role:user, content:question})
    UC->>SESSION: save(ChatMessage{role:assistant, content:answer, refs:[note1, note2]})

    UC-->>API: {answer, citations, session_id}
    API-->>User: 200 {answer: "RSI của VNM...", references: [{title, excerpt}], session_id}
```

---

## 11.3 Neo4j Knowledge Graph Structure

```mermaid
graph LR
    subgraph GRAPH["Neo4j Knowledge Graph"]
        N1["(KnowledgeNote)\nnote_id: 'rsi-001'\ntitle: 'RSI Indicator Basics'\ntags: ['RSI', 'technical']"]
        N2["(KnowledgeNote)\nnote_id: 'vnm-rsi-2024'\ntitle: 'VNM RSI Analysis Q4 2024'\ntags: ['VNM', 'RSI', 'overbought']"]
        N3["(KnowledgeNote)\nnote_id: 'ob-001'\ntitle: 'Overbought Trading Strategies'\ntags: ['overbought', 'signals']"]

        T1["(Topic)\nname: 'Technical Analysis'\ncategory: 'Analysis'"]
        T2["(Topic)\nname: 'Oscillators'\ncategory: 'Indicators'"]

        S1["(Stock)\nsymbol: 'VNM'\nname: 'Vinamilk'"]

        C1["(Concept)\nname: 'RSI'\ndefinition: 'Relative Strength Index'"]
    end

    N1 -->|":ABOUT"| T1
    N1 -->|":ABOUT"| T2
    N2 -->|":ABOUT"| T1
    N2 -->|":MENTIONS"| S1
    N2 -->|":RELATED_TO"| N1
    N2 -->|":RELATED_TO"| N3
    N1 -->|":EXPLAINS"| C1
    T2 -->|":CHILD_OF"| T1
    C1 -->|":APPLIES_TO"| S1
```

---

## 11.4 Dependency Injection Map

```mermaid
flowchart TD
    subgraph DI["Dependency Injection (FastAPI dependencies.py)"]
        GET_SESSION_REPO["get_session_repository()\n→ InMemorySessionRepository()"]
        GET_GRAPH_REPO["get_graph_repository(neo4j_driver)\n→ Neo4jKnowledgeGraphRepository(driver)"]
        GET_LLM["get_llm_adapter(config)\n→ OllamaAdapter(host, model)"]
        GET_PROMPT["get_prompt_builder()\n→ PromptBuilder(system_prompt)"]
        GET_FACTORY["get_context_factory()\n→ GraphContextFactory()"]

        GET_QU["get_query_understanding()\n= QueryUnderstandingService()"]
        GET_GR["get_graph_retrieval(graph_repo, factory)\n= GraphRetrievalService(repo, factory)"]
        GET_AG["get_answer_generation(llm, prompt_builder)\n= AnswerGenerationService(llm, prompt_builder)"]

        GET_UC_ASK["get_ask_question_uc(\n  session_repo,\n  query_understanding,\n  graph_retrieval,\n  answer_generation\n) → AskQuestionUseCase(...)"]
        GET_UC_HIST["get_chat_history_uc(session_repo)\n→ GetChatHistoryUseCase(repo)"]
        GET_UC_SRCH["get_search_notes_uc(graph_repo)\n→ SearchNotesUseCase(repo)"]
    end

    GET_SESSION_REPO --> GET_UC_ASK
    GET_SESSION_REPO --> GET_UC_HIST
    GET_GRAPH_REPO --> GET_GR
    GET_GRAPH_REPO --> GET_UC_SRCH
    GET_LLM --> GET_AG
    GET_PROMPT --> GET_AG
    GET_FACTORY --> GET_GR

    GET_QU --> GET_UC_ASK
    GET_GR --> GET_UC_ASK
    GET_AG --> GET_UC_ASK
```
