# SeerLord AI Installation Guide

This guide will help you install and deploy SeerLord AI. The project supports one-click deployment via Docker (Recommended) and manual step-by-step deployment.

## 1. Requirements

*   **OS**: Linux, Windows, macOS
*   **Docker**: 20.10+ (For Docker deployment)
*   **Python**: 3.10+ (For manual backend deployment)
*   **Node.js**: 18+ (For manual frontend deployment)
*   **PostgreSQL**: 16+

## 2. Quick Start (Docker) - Recommended

This is the simplest way to deploy. It automatically builds the frontend, backend, and starts the database.

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-repo/seerlord_ai.git
    cd seerlord_ai
    ```

2.  **Configure Environment Variables**
    Copy the example configuration file:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and fill in your API Keys (e.g., OpenAI API Key). The database configuration can be left as default.

3.  **Start Services**
    ```bash
    docker-compose up -d --build
    ```

4.  **Access the Application**
    Wait a few minutes for the build to complete, then visit:
    *   **URL**: `http://localhost:8000`
    *   **Note**: The backend service automatically serves the frontend static files. No separate Nginx configuration is required.

## 3. Manual Deployment

Use this method for development or if you need fine-grained control.

### 3.1 Database Preparation

1.  Install and start PostgreSQL.
2.  Create an empty database (e.g., `seerlord`).
    ```sql
    CREATE DATABASE seerlord;
    ```

### 3.2 Backend Deployment (Python)

1.  **Create Virtual Environment**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Copy `.env.example` to `.env` and update the database connection info:
    ```ini
    DATABASE_URL=postgresql://user:password@localhost:5432/seerlord
    ```

4.  **Database Initialization**
    The system automatically checks and creates table structures on startup. If you need to manually initialize using SQL, use the `db_schema.sql` file in the root directory.
    
    Alternatively, run the Python script to initialize (if tables do not exist):
    ```bash
    python scripts/init_db.py
    ```

5.  **Start Backend**
    ```bash
    uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The Backend API will run at `http://localhost:8000`.

### 3.3 Frontend Deployment (Vue3)

1.  **Enter Frontend Directory**
    ```bash
    cd admin
    ```

2.  **Install Dependencies**
    ```bash
    npm install
    ```

3.  **Run in Development Mode**
    ```bash
    npm run dev
    ```
    The frontend will run at `http://localhost:5173`. In dev mode, ensure the API URL in `.env` points to your backend.

4.  **Production Build**
    If you want to integrate the frontend into the backend service:
    ```bash
    npm run build
    ```
    After building, copy all files from `admin/dist` to `server/static/`. Restart the backend service, and you can access the frontend via `http://localhost:8000`.

## 4. Database Initialization Details

This project uses SQLAlchemy ORM to manage database structures.

*   **Automatic Initialization**: Every time the app starts (`server/main.py`) or you run `scripts/init_db.py`, the system automatically detects and creates missing tables.
*   **Manual SQL**: If you are in an environment where you cannot run Python, or need to audit the SQL structure, you can execute the `db_schema.sql` file located in the root directory directly against your database.
    ```bash
    psql -U user -d seerlord -f db_schema.sql
    ```

## 5. Troubleshooting

**Q: "FATAL: password authentication failed for user" on startup**
A: Check if the `DATABASE_URL` in your `.env` matches your local or Docker database password.

**Q: Page shows 404 Not Found**
A: If accessing `http://localhost:8000` returns 404, it means static files are not loaded correctly. Ensure you have run `npm run build` and copied the artifacts to `server/static`, or use Docker deployment (which handles this automatically).
