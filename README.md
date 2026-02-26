# NCBW Training Portal

Simple Python (Flask) backend + React frontend.
No PostgreSQL needed — uses SQLite (file-based, zero setup).

---

## 🚀 How to Run

### 1. Backend (Python Flask)

Open a terminal:

```bash
cd backend

# Create virtual environment (first time only)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install packages (first time only)
pip install -r requirements.txt

# Run the server
python app.py
```

Backend runs at: http://localhost:5000

A `ncbw.db` file will be created automatically (your database).

---

### 2. Frontend (React)

Open a second terminal:

```bash
cd frontend

# Install packages (first time only)
npm install

# Run the dev server
npm run dev
```

Frontend runs at: http://localhost:5173

---

## 🔐 Default Login

| Role  | Email                  | Password    |
|-------|------------------------|-------------|
| Admin | admin@nc100bw.org      | Admin@1234  |

To create trainee accounts, use the "Create Account" tab on the login page.

---

## 📁 Structure

```
ncbw-project/
├── backend/
│   ├── app.py           ← Flask server (all API routes)
│   ├── requirements.txt ← Python packages
│   └── ncbw.db          ← SQLite database (auto-created)
│
└── frontend/
    ├── src/
    │   ├── components/  ← UI components
    │   ├── data/        ← Training course data
    │   └── utils/
    │       └── api.ts   ← Calls Flask backend
    └── package.json
```

---

## 🔌 API Endpoints

| Method | Path                        | Description              |
|--------|-----------------------------|--------------------------|
| POST   | /api/auth/signup            | Register new user        |
| POST   | /api/auth/signin            | Login                    |
| GET    | /api/auth/user              | Get current user         |
| POST   | /api/auth/signout           | Logout                   |
| POST   | /api/track/select           | Select training track    |
| GET    | /api/progress/:trackId      | Get progress             |
| POST   | /api/progress/course        | Mark course complete     |
| POST   | /api/progress/quiz          | Submit quiz score        |
| GET    | /api/admin/users            | Admin: list all users    |
| GET    | /api/admin/reports          | Admin: progress reports  |
| DELETE | /api/admin/users/:id        | Admin: delete user       |
