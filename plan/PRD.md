# Vietnamese AI Tourism Platform — Detailed Agentic RAG Development Plan

---

# 1. Project Vision

Build an AI-native Vietnamese tourism platform that combines:

* Conversational AI
* Agentic RAG
* Planner-based orchestration
* Tool calling
* Self-hosted LLM inference
* Travel analytics and visualization

The system should evolve from a traditional RAG chatbot into a multi-tool AI tourism assistant capable of planning, reasoning, retrieval, and deterministic execution.

---

# 2. Final Product Goals

The final platform should support:

* Tourism question answering
* Itinerary generation
* Weather-aware travel planning
* Budget estimation and analysis
* Transportation suggestions
* Personalized recommendations
* Structured travel analytics
* Real-time AI interaction

---

# 3. High-Level System Architecture

```text id="j7u0j5"
Frontend (Next.js)
    ↓
FastAPI Gateway
    ↓
Planner & Router Layer
    ↓
Tool Execution Layer
    ├── Tourism RAG Tool
    ├── Weather Tool
    ├── Budget Tool
    ├── Itinerary Tool
    ├── Recommendation Tool
    └── Analytics Tool
    ↓
Generator Model (Qwen2.5-3B)
    ↓
Langfuse Observability
```

---

# 4. Core Agentic RAG Architecture

## 4.1 Traditional RAG

```text id="r4o77o"
User
 ↓
Retrieve
 ↓
Generate
```

---

## 4.2 Agentic RAG

```text id="5i5wde"
User
 ↓
Planner
 ↓
Decision Making
 ↓
Tool Calling / Retrieval
 ↓
Orchestration
 ↓
Generation
```

---

# 5. Core AI Layers

| Layer               | Responsibility                        |
| ------------------- | ------------------------------------- |
| Planner Layer       | Understand intent and decide workflow |
| Router Layer        | Route tasks to RAG or tools           |
| Retrieval Layer     | Retrieve tourism knowledge            |
| Tool Layer          | Execute deterministic operations      |
| Generator Layer     | Generate grounded responses           |
| Observability Layer | Monitor and evaluate workflows        |

---

# 6. Planner & Router Layer

## Purpose

This is the “brain” of the Agentic RAG system.

The planner layer decides:

* Whether to use RAG
* Whether to call external tools
* Whether to execute multiple tools
* Whether query rewriting is needed
* How to orchestrate workflows

---

# 6.1 Example Routing Logic

| User Query                        | Planner Decision                   |
| --------------------------------- | ---------------------------------- |
| “Đà Lạt có gì chơi?”              | Tourism RAG                        |
| “Tuần sau Đà Lạt có mưa không?”   | Weather Tool                       |
| “Tôi có 5 triệu đi Đà Lạt 3 ngày” | Budget Tool + Itinerary Tool + RAG |
| “Đi Phú Quốc mùa nào đẹp?”        | Query Rewrite + RAG                |

---

# 6.2 Example Planner Output

```json id="0d47ow"
{
  "actions": [
    {
      "tool": "weather_tool",
      "args": {
        "location": "Da Lat"
      }
    }
  ]
}
```

---

# 6.3 Multi-Step Workflow Example

## User Query

> “Tôi có 5 triệu đi Đà Lạt 3 ngày.”

---

## Planner Workflow

```text id="g0vwv6"
1. Estimate budget
2. Generate itinerary
3. Retrieve tourism context
4. Combine results
5. Generate grounded response
```

---

# 7. Model Architecture

---

# 7.1 Planner Model

## Suggested Model

* Qwen2.5-0.5B

---

## Responsibilities

* Intent classification
* Tool routing
* Query rewriting
* Retrieval planning
* Workflow orchestration

---

# 7.2 Generator Model

## Suggested Model

* Qwen2.5-3B

---

## Responsibilities

* Grounded response generation
* Tourism QA
* Itinerary explanation
* Conversational interaction
* Context summarization

---

# 8. Tool Architecture

---

# 8.1 Tourism RAG Tool

## Purpose

Retrieve tourism knowledge from vector database.

---

## Responsibilities

* Hybrid retrieval
* Semantic search
* Context retrieval
* Reranking

---

## Example Functions

```python id="8t3m6k"
retrieve_documents()
rerank_documents()
```

---

# 8.2 Weather Tool

## Purpose

Provide weather-aware travel planning.

---

## Example Functions

```python id="x5dlnh"
get_weather()
get_forecast()
```

---

# 8.3 Budget Tool

## Purpose

Estimate trip expenses.

---

## Example Functions

```python id="yj0n7j"
estimate_hotel_cost()
estimate_transport_cost()
estimate_food_cost()
```

---

# 8.4 Itinerary Tool

## Purpose

Generate structured travel plans.

---

## Example Functions

```python id="xjlwm9"
generate_itinerary()
```

---

# 8.5 Recommendation Tool

## Purpose

Personalized travel recommendations.

---

## Example Functions

```python id="p76k2s"
recommend_destinations()
recommend_hotels()
```

---

# 9. Tool Calling Flow

---

# 9.1 Agentic Workflow

```text id="jlwm74"
User Query
    ↓
Planner Model
    ↓
Choose Tool
    ↓
Python Executes Function
    ↓
Tool Result
    ↓
Generator Model
    ↓
Final Response
```

---

# 9.2 Example Workflow

## User Query

> “Tuần sau Đà Lạt có mưa không?”

---

## Planner Decision

```json id="jlwm75"
{
  "tool": "weather_tool"
}
```

---

## Python Execution

```python id="jlwm76"
get_weather("Da Lat")
```

---

## Final Response

> “Tuần sau Đà Lạt có khả năng mưa nhẹ…”

---

# 10. Retrieval Architecture

---

# 10.1 Retrieval Pipeline

```text id="jlwm77"
Query
 ↓
Query Rewrite
 ↓
Hybrid Retrieval
 ↓
Reranking
 ↓
Context Filtering
 ↓
Generation
```

---

# 10.2 Retrieval Components

| Component         | Purpose            |
| ----------------- | ------------------ |
| BM25              | keyword retrieval  |
| Dense Embeddings  | semantic retrieval |
| Hybrid Search     | combine both       |
| Reranker          | improve relevance  |
| Semantic Chunking | preserve context   |

---

# 11. Self-Hosted Inference

---

# 11.1 Local Model Serving

## Tools

* Ollama
* FastAPI

---

# 11.2 Local Models

| Model        | Purpose   |
| ------------ | --------- |
| Qwen2.5-0.5B | planner   |
| Qwen2.5-3B   | generator |

---

# 11.3 Local Inference Flow

```text id="jlwm78"
Frontend
 ↓
FastAPI
 ↓
Ollama
 ↓
Qwen Models
```

---

# 11.4 Future Upgrade

Future migration path:

```text id="jlwm79"
Ollama
    ↓
vLLM
```

For:

* optimized inference
* GPU utilization
* concurrent serving

---

# 12. Frontend Features

---

# 12.1 Chat Interface

* Conversational AI interaction
* Streaming responses
* Source references
* Tool execution feedback

---

# 12.2 Budget Visualization

## Features

* Hotel cost charts
* Food cost analysis
* Transportation breakdown
* Budget allocation graphs

---

# 12.3 Travel Timeline

* Day-by-day itinerary
* Timeline visualization
* Activity scheduling

---

# 13. Observability & Evaluation

---

# 13.1 Langfuse Integration

Track:

* prompts
* retrieval traces
* tool calls
* latency
* hallucination cases
* token usage

---

# 13.2 Retrieval Evaluation

## Metrics

* Recall@K
* Precision@K
* MRR

---

# 13.3 Generation Evaluation

## Metrics

* Groundedness
* Faithfulness
* Hallucination rate
* Response relevance

---

# 14. Development Phases

---

# PHASE 1 — Core Tourism RAG

## Build

* Qdrant setup
* Tourism dataset
* Hybrid retrieval
* FastAPI backend
* Next.js frontend
* Ollama integration

---

# PHASE 2 — Planner & Router

## Build

* Intent classification
* Query rewriting
* Structured outputs
* Tool routing
* Multi-step workflows

---

# PHASE 3 — Tool System

## Build

* Weather tool
* Budget tool
* Itinerary tool
* Recommendation tool

---

# PHASE 4 — Agentic Workflows

## Build

* Multi-tool orchestration
* Retrieval planning
* Workflow coordination
* Context aggregation

---

# PHASE 5 — Evaluation & Observability

## Build

* Langfuse tracing
* Retrieval benchmarks
* Hallucination analysis
* Performance monitoring

---

# PHASE 6 — Visualization & UX

## Build

* Budget charts
* Travel timeline
* Structured UI outputs

---

# 15. Recommended Learning Order

| Step | Focus                      |
| ---- | -------------------------- |
| 1    | Core RAG                   |
| 2    | Ollama serving             |
| 3    | Planner model              |
| 4    | Tool calling               |
| 5    | Routing logic              |
| 6    | Multi-step orchestration   |
| 7    | Evaluation                 |
| 8    | Observability              |
| 9    | LangGraph (optional later) |

---

# 16. Important Design Principles

---

# AI SHOULD HANDLE

* Reasoning
* Planning
* Summarization
* Tool selection
* Conversational interaction

---

# TOOLS SHOULD HANDLE

* Calculations
* APIs
* Deterministic logic
* Budget computation
* External service execution

---

# 17. Final Project Positioning

## Final Identity

> Self-hosted Vietnamese Agentic RAG tourism platform with planner-based tool orchestration, retrieval-grounded generation, structured analytics, and AI-powered travel planning.

---

# 18. Career Positioning

This project is designed to demonstrate capabilities relevant to:

* AI Engineer
* Applied AI Engineer
* GenAI Engineer
* AI Backend Engineer
* LLM Systems Engineer
* AI Platform Engineer
