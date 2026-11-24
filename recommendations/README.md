# Recommendations and AI Module

## Module Overview
This folder contains the recommendation systems, trending topic analyzers, anomaly/spam detectors, and the RAG-powered research assistant for **Research Commons**.

- **Assigned Team Member:** Siddharth
- **Primary Tech Stack:** Python, scikit-learn, MLxtend (FP-Growth), Ollama (Local LLM), LangChain / LlamaIndex (or lightweight RAG scripts)

---

## Planned Responsibilities & Features
1. **Paper & Researcher Recommendations:**
   - Content-based suggestions based on user research interests and saved library papers.
   - Researcher matching for faculty and student collaboration.
   - Cold-start handling for new users without history.
2. **Co-Saved Paper Associations (FP-Growth):**
   - Frequent pattern mining to find papers commonly bookmarked together.
3. **Trending Topics & Spike Detection:**
   - Sliding time window tracking on paper tags and discussion topics.
   - Z-score calculations to detect sudden surges and breaking topics.
4. **Spam & Anomaly Detection:**
   - Isolation Forest algorithms to flag abnormal posting patterns or spam accounts.
5. **Research Assistant (RAG):**
   - Grounded Q&A assistant using Ollama with a local language model.
   - Strict retrieval-augmented generation ensuring answers cite specific papers or passages.

---

## Getting Started (Planned)
1. Install machine learning and RAG dependencies:
   ```bash
   pip install scikit-learn mlxtend ollama
   ```
2. Verify Ollama is running locally with the agreed model (e.g., `llama3` or `mistral`):
   ```bash
   ollama pull llama3
   ollama run llama3
   ```
3. Expose recommendation and assistant query interfaces to connect with the backend service.
