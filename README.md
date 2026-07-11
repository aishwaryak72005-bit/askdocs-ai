# DocuMind AI — Multi PDF Question Answering System

Full-stack app: Django REST API backend + React (Vite) frontend, using
Google Gemini for question answering and summarization.

## 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste your Gemini API key

python manage.py migrate
python manage.py runserver
```

Backend runs at `http://127.0.0.1:8000`.

Get a Gemini API key at https://aistudio.google.com/apikey — keep it out of
version control (.env is already ignored by convention; don't commit it).

## 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://127.0.0.1:3000` and proxies `/api/*` requests to
the Django backend automatically (see `vite.config.js`).

## 3. Try it out

1. Open `http://localhost:3000`, register an account.
2. Upload a PDF from the Documents page. Each document is text-extracted,
   chunked, embedded, and indexed into a local vector store — you'll see
   an "Indexed · N chunks" tag on the card once that finishes.
3. Go to "Ask" and ask a question — the app embeds your question, retrieves
   the most relevant chunks (across all documents, or one if you select it),
   and answers using only those chunks. Answers show which document/page
   each fact came from.
4. Click "Summarize" on any document card for a quick summary (this still
   uses the full extracted text, not retrieval).
5. Check "History" for your past questions, answers, and citations.

## How the RAG pipeline works

```
Upload PDF
  → pdfplumber extracts text (page-tagged)
  → text is split into ~900-char chunks, tagged with page number
  → each chunk is embedded with Gemini's embedding model
  → chunks + embeddings + metadata (user, document, page) are stored in Chroma

Ask a question
  → question is embedded (RETRIEVAL_QUERY)
  → Chroma returns the top-K most similar chunks, scoped to the current
    user (and one document, if selected)
  → those chunks — not the whole document — are sent to Gemini as context
  → Gemini answers, citing which document/page each fact came from
```

This scales far better than stuffing whole documents into the prompt: a
100-page PDF still only sends ~6 relevant chunks per question, and it works
the same way whether you have 1 document or 10.

The vector store lives in `backend/chroma_db/` (created automatically,
gitignore this in a real repo). If Gemini's API is unreachable when a
document is uploaded, the upload and text extraction still succeed —
only indexing fails, and the document card will show "Not indexed" with
the reason. Re-upload the file once connectivity is restored.

**Rate limits:** Gemini's free tier caps embedding requests at ~100/minute.
If you upload several large PDFs back to back, you may hit a `429
RESOURCE_EXHAUSTED` error. The backend automatically retries these,
respecting the delay Google's API suggests (visible in `chat/gemini_client.py`
as `_call_with_retry`) — indexing will pause and resume rather than failing
outright. If you still hit it repeatedly, space out large uploads by a
minute or so.

## Project structure

```
backend/
  documind_backend/   Django settings, root URLs
  accounts/            register / login / logout / JWT refresh
  documents/           PDF upload, text extraction, list, delete
  chat/                Gemini Q&A, chat history, summaries
frontend/
  src/api/             axios instance with JWT auto-refresh
  src/context/          auth state
  src/pages/            Login, Register, Dashboard, Chat, History
  src/styles/theme.css  design tokens (Bootstrap 5, themed)
```

## API endpoints

| Method | Endpoint                    | Auth | Description               |
|--------|------------------------------|------|----------------------------|
| POST   | /api/register                | No   | Create account             |
| POST   | /api/login                   | No   | Get JWT tokens             |
| POST   | /api/logout                  | Yes  | Blacklist refresh token    |
| POST   | /api/token/refresh           | No   | Refresh access token       |
| POST   | /api/upload                  | Yes  | Upload 1+ PDFs (`files`) — extracts, chunks, and indexes each one |
| GET    | /api/documents                | Yes  | List your documents (includes indexing status) |
| DELETE | /api/document/{id}           | Yes  | Delete a document and its vector chunks |
| POST   | /api/ask                     | Yes  | Ask a question — RAG retrieval, returns `answer` + `sources` |
| GET    | /api/history                  | Yes  | List past Q&A with citations |
| GET    | /api/summary/{document_id}   | Yes  | Get/generate a summary (full-text, not RAG) |

## Production notes (not done here)

- Swap SQLite for PostgreSQL in `settings.py` `DATABASES`.
- Move media storage off local disk (e.g. S3) if deploying; the same goes
  for `chroma_db/` — consider a hosted vector DB (e.g. Chroma Cloud,
  Pinecone, Weaviate) instead of the local persistent client for multi-instance deployments.
- Set `DEBUG=False` and a real `SECRET_KEY`, restrict `ALLOWED_HOSTS`.
- Add rate limiting on `/api/ask` and `/api/upload` since both cost Gemini
  API calls (generation + embeddings).
- Add a background task queue (Celery/RQ) for indexing large PDFs instead
  of doing it synchronously inside the upload request.
