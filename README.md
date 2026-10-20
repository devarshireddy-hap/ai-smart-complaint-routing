# AI Smart Complaint Routing System

AI-powered smart complaint routing and resolution system using RAG, vector search, RBAC, and manual dashboard-based complaint tracking.

## Project Overview

This system automates complaint routing across multiple departments using:
- **Semantic AI routing** (no keyword matching)
- **RAG (Retrieval-Augmented Generation)** for intelligent suggestions
- **Vector search** with pgvector for similarity matching
- **Role-Based Access Control (RBAC)** for authorization
- **Google SSO** for authentication
- **Audit logs** for compliance

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: Flask
- **ORM**: SQLAlchemy
- **Authentication**: Google OAuth 2.0
- **Vector Processing**: sentence-transformers
- **LLM Integration**: Google Gemini API

### Database
- **Primary DB**: PostgreSQL 15+
- **Vector Extension**: pgvector
- **Caching** (optional): Redis

### Frontend
- **Framework**: React
- **State Management**: Redux/Context API
- **Styling**: Tailwind CSS / Material-UI

### AI/ML
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
- **RAG Framework**: LangChain
- **Vector Search**: pgvector

### DevOps
- **Containerization**: Docker + Docker Compose
- **Version Control**: Git + GitHub
- **CI/CD** (optional): GitHub Actions

## Fixed System Values

### Departments (Frozen - Cannot be created/deleted)
- TECHNICAL
- FINANCE
- ELECTRICAL
- PLUMBING
- SECURITY

Note: departmental structure is fixed and complaint assignment is handled from the dashboard using complaint status.

### User Types
- STUDENT
- FACULTY
- WORKING_STAFF

### System Roles
- CITIZEN (Users submitting complaints)
- OFFICER (Department staff handling complaints)
- ADMIN (System administrators)

Department-level assignment is recorded through the complaint status in the dashboard; there is no separate assignment table.

### Complaint Status Workflow
```
SUBMITTED → ASSIGNED → IN_PROGRESS → RESOLVED
                                ↓
                             REJECTED
```

### Priority Levels
- LOW
- MEDIUM
- HIGH
- URGENT

### Manual Handling Rule
Complaint assignment is a dashboard action. The database stores department and the current complaint status only; there is no separate resolution table.

## Project Structure

```
ai-smart-complaint-routing/
│
├── backend/                    # Flask backend
│   ├── app.py
│   ├── config.py
│   ├── routes/                 # API endpoints
│   ├── services/               # Business logic
│   ├── middleware/             # Auth, authorization, audit
│   ├── models/                 # Database models (SQLAlchemy)
│   └── utils/                  # Helpers, validators, logger
│
├── frontend/                   # React frontend
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   └── public/
│
├── ai/                         # AI/RAG components
│   ├── embeddings/             # Embedding generation
│   ├── rag/                    # RAG pipeline
│   ├── routing/                # Department/priority prediction
│   └── prompts/                # LLM prompts
│
├── database/                   # Database scripts
│   ├── schema/                 # Table definitions
│   ├── migrations/
│   ├── seeds/                  # Initial data
│   ├── functions/              # Stored procedures
│   ├── triggers/               # Database triggers
│   ├── indexes/                # Optimization indexes
│   ├── views/                  # Database views
│   └── backup/                 # Backup/restore scripts
│
├── docs/                       # Documentation
│   ├── requirements/
│   ├── architecture/
│   ├── database/
│   ├── api/
│   ├── security/
│   ├── ai/
│   ├── database_operations/
│   └── publication/
│
├── tests/                      # Test suite
│   ├── backend/
│   ├── database/
│   ├── ai/
│   └── integration/
│
├── docker/                     # Docker configurations
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── database.Dockerfile
│
├── scripts/                    # Utility scripts
│   ├── setup_database.py
│   ├── seed_database.py
│   └── generate_test_data.py
│
├── .env.example                # Environment variables template
├── .gitignore
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Multi-container setup
└── README.md                   # This file
```

## API Base URL

Development: `http://localhost:5000/api/v1`

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Node.js 18+
- Docker (optional)

### Setup Instructions

1. **Clone repository**
   ```bash
   git clone https://github.com/devarshireddy-hap/ai-smart-complaint-routing.git
   cd ai-smart-complaint-routing
   ```

2. **Backend setup**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Configure and start the database**
   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   # Edit .env and set a private DB_PASSWORD before starting services.
   docker compose up -d postgres
   docker compose ps
   ```

   On the first startup with an empty PostgreSQL data volume, Compose runs
   `database/schema/00_init.sql` followed by `database/seeds/01_init_data.sql`.
   `00_init.sql` is the canonical complete schema. Do not run the other files in
   `database/schema` as part of this initialization; they are overlapping
   standalone/older schema fragments.

   PostgreSQL initialization scripts run only when the data directory is empty.
   If the `postgres_data` volume already exists, these mounts will not apply the
   schema or seeds again; inspect the existing database and use an appropriate
   migration rather than deleting the volume.

4. **Frontend setup**
   ```bash
   cd frontend
   npm install
   ```

5. **Start the application**
   ```powershell
   docker compose up -d
   ```

   From the host machine, the database is available at `localhost:5432`.
   Containers in this Compose project should connect to `postgres:5432`.
   Keep `.env` private and do not commit real credentials. If the database
   password contains reserved URL characters, URL-encode it when using
   `DATABASE_URL`.

## Important Notes

### No Keyword-Based Routing
❌ DO NOT implement rules like:
```python
if "water" in complaint.text:
    department = PLUMBING
```

✅ DO implement semantic analysis:
```
Complaint → Embedding (384-dim) → Vector Similarity Search → Historical Complaints → RAG → LLM → Department
```

### User Deletion Policy
- Users are NEVER physically deleted
- Use `is_active = FALSE` for soft delete
- Historical records remain intact
- Essential for audit trail and compliance

### Department Management
- The 5 departments are FROZEN and immutable
- Cannot create new departments
- Cannot delete existing departments
- Admins can only manage categories under departments

## Timeline

- **Phase 1** (Week 1): Database setup, authentication, API foundation
- **Phase 2** (Weeks 1-2): Backend API, AI/RAG integration
- **Phase 3** (Week 2): Frontend, full integration
- **Phase 4** (Week 2.5): Testing, documentation, deployment

## License

Internal project - Team based

## Contact

For questions or clarifications, contact the team lead.
