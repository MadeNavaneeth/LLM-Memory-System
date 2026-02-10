# 🛠️ Installation & Setup Guide

This guide will walk you through the process of setting up the **LLM Memory Management System** on your local machine.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.9+**
- **MongoDB** (Local Community Edition or MongoDB Atlas connection string)
- **Git**

---

## 🚀 Step-by-Step Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Navaneeth/llm-memory-system.git
cd llm-memory-system
```

### 2. Create a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup NLP Model (SpaCy)
The system uses `spaCy` for high-performance Named Entity Recognition.
```bash
python -m spacy download en_core_web_sm
```

### 5. Configure Environment Variables
Copy the `.env.example` file and fill in your details:
```bash
cp .env.example .env
```

Open `.env` and configure your API keys:
- `GEMINI_API_KEY`: Required for Gemini models (recommended).
- `OPENAI_API_KEY`: Required for OpenAI models.
- `OPENROUTER_API_KEY`: Required for OpenRouter models.
- `MONGODB_URI`: Defaults to `mongodb://localhost:27017/`.

---

## 🗄️ Database Setup

### SQLite (SQL)
No manual setup required. The system will automatically create `data/memory.db` on your first run.

### MongoDB (NoSQL)
1. Ensure your MongoDB service is running.
2. If using a local installation, the default URI in `.env` should work out of the box.
3. If using Atlas, update the `MONGODB_URI` in your `.env` file.

---

## 🏃 Running the Application

### Option A: Windows (Automatic)
We provide a simple batch script to start the server:
```powershell
.\START.bat
```

### Option B: Manual (Cross-platform)
Start the FastAPI server using Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The application will be available at: **[http://localhost:8000](http://localhost:8000)**

---

## 🛠️ Troubleshooting

- **MongoDB Connection Error**: Ensure the MongoDB service is started. On Windows, check "Services" for `MongoDB`.
- **ModuleNotFoundError**: Ensure you have activated your virtual environment before running the server.
- **API Rate Limits**: If you encounter 429 errors, check your API key usage logs on the respective provider's dashboard.

---

## 📄 Additional Resources
- [API Documentation](http://localhost:8000/docs) (Swagger UI)
- [Project Report Walkthrough](./walkthrough.md)
