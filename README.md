# 🤖 AI Job Agent (Multi-Agent System)

An AI-powered job automation system that searches, scores, and applies to jobs using a **multi-agent architecture**.

Built with modern AI tools like **LLMs, RAG, and vector databases**, this system simulates how real hiring pipelines work.

---

## 🌟 Features

- 🔍 **Job Search Automation**  
  Scrapes job listings based on role & location

- 🎯 **AI Job Scoring (0–10)**  
  Matches jobs against your profile using intelligent scoring

- 📄 **Resume Tailoring (RAG + FAISS)**  
  Uses semantic search to customize resume for each job

- ✍️ **Cover Letter Generation**  
  Generates personalized, ATS-friendly cover letters

- 📄 **Resume Upload (PDF Supported)**  
  Upload resume → auto extract → use in pipeline

- 💾 **Application Tracking System**  
  Track status: Pending → Applied → Interview → Offer → Rejected

---

## 🧠 How It Works (5 AI Agents)

1. **🔍 Research Agent**
   - Finds jobs
   - Extracts required skills using LLM

2. **🎯 Decision Agent**
   - Scores jobs (0–10)
   - Decides Apply / Skip

3. **📄 Resume Agent**
   - Uses FAISS (vector DB)
   - Retrieves relevant resume sections
   - Tailors resume with job keywords

4. **✍️ Cover Letter Agent**
   - Generates human-like personalized cover letters

5. **💾 Application Agent**
   - Saves applications in database
   - Tracks job status

---

## ⚙️ Tech Stack

- **Language:** Python  
- **Frontend:** Streamlit  
- **Backend:** FastAPI  
- **LLM:** Groq (LLaMA 3)  
- **Framework:** LangChain  
- **Vector DB:** FAISS  
- **Embeddings:** HuggingFace  
- **Database:** SQLite  

---

## 📸 Demo

![App Screenshot](app.png)
![App Screenshot](app.png)
![App Screenshot](app.png)

---

## 🛠️ Installation

```bash
git clone https://github.com/yourusername/ai-job-agent.git
cd ai-job-agent
pip install -r requirements.txt
````

---

## ▶️ Run Locally

### Start Backend (FastAPI)

```bash
uvicorn main:app --reload --port 8000
```

### Start Frontend (Streamlit)

```bash
streamlit run app.py
```

---

## 📄 Usage

1. Enter job role (e.g. AI Engineer)
2. Add your profile (skills + experience)
3. Upload your resume (PDF)
4. Click **Run Agent Pipeline**

---

## 📊 Example Output

* Jobs Found: 5
* Apply: 2
* Skip: 3

---

## 🧠 Key Concepts Used

* Multi-Agent Systems
* Retrieval-Augmented Generation (RAG)
* Semantic Search
* LLM Prompt Engineering
* AI Decision Systems

---

## 🚀 Why This Project?

This project demonstrates:

* Real-world AI system design
* Production-ready architecture
* End-to-end AI pipeline
* Practical use of LLMs in automation

👉 Inspired by modern AI-driven hiring systems

---

## 📌 Future Improvements

* Real job APIs (LinkedIn / Indeed)
* Resume skill gap analysis
* Job recommendation system
* Dashboard analytics
* Auto-apply integration

---

## 👨‍💻 Author

**Chintan Dabhi**
AI/ML Engineer

---

## ⭐ Support

If you like this project:

👉 Star the repo ⭐
👉 Share with others

---

## 📜 License

MIT License

::contentReference[oaicite:3]{index=3}
```
