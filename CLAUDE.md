# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Start the server:**
```bash
python -m app.main
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Database seeding:**
```bash
python -m app.db.seed.main
```

## Architecture Overview

This is a FastAPI-based chatbot server for SIT (Singapore Institute of Technology) with the following core architecture:

### Application Structure
- **FastAPI app** with async/await patterns throughout
- **SQLAlchemy 2.0** with async sessions for database operations
- **Pydantic v2** for settings and data validation
- **Google Cloud integration** (Document AI, Gemini AI)
- **LangChain** for AI workflow orchestration

### Key Components

**Database Layer (`app/db/`):**
- Async SQLAlchemy with PostgreSQL
- Models for students, staff, programs, submissions, notifications
- Enum-based status tracking (PENDING/APPROVED/REJECTED/MANUAL_REVIEW)
- Relationship-based design linking users, programs, and submissions

**Providers (`app/providers/`):**
- Service layer pattern with dedicated providers
- `LangChainServiceProvider`: AI workflow orchestration
- `NotificationServiceProvider`: Handles notifications 
- `StudentDataProvider`: Student-specific data operations
- `TextExtractionProvider`: Document processing via Google Document AI

**Router Architecture (`app/routers/`):**
- Clean separation: `/staff` and `/student` endpoints
- All routes prefixed with `settings.API_PREFIX`

**Models Organization (`app/models/`):**
- Separated by domain: `staff_models.py`, `student_models.py`, `template_models.py`
- Pydantic models for request/response validation

### Key Integrations
- **Google Cloud Document AI** for document processing
- **Google Gemini** for AI-powered responses
- **LangChain + LangSmith** for AI workflow tracking
- **Async database operations** throughout

### Configuration
- Environment-based settings via `.env` file
- All sensitive configs (API keys, database URLs) are templated in `settings.py`
- Google Cloud service account authentication via JSON key file

### Development Notes
- The app uses structured logging with request ID tracking
- CORS is configured for all origins (development setup)
- Health check endpoint available at `/health`
- Database models use UUID primary keys and enum-based status fields