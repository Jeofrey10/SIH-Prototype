# Troubleshooting & Operational Guide (TROUBLESHOOTING.md)

This guide addresses common setup and operational issues when running the **AICTE Complaint Dashboard**.

---

## 1. Database Connection Refused / PostgreSQL Missing
### Symptom
`psycopg.OperationalError: connection to server at "localhost", port 5432 failed: Connection refused`

### Resolution
1. **Option A: With Docker Compose (Recommended)**:
   ```powershell
   docker compose up -d db
   ```
   Check container status: `docker compose ps`
2. **Option B: Local PostgreSQL (Fallback without Docker)**:
   If Docker is not installed on the machine:
   - Install PostgreSQL 15+ from [postgresql.org](https://www.postgresql.org/download/).
   - Start the service:
     ```powershell
     Start-Service postgresql-x64-16
     ```
   - Connect to PostgreSQL as admin and create the user and database:
     ```sql
     CREATE USER aicte WITH PASSWORD 'aicte_dev_pw';
     CREATE DATABASE aicte_dashboard OWNER aicte;
     CREATE DATABASE aicte_dashboard_test OWNER aicte;
     GRANT ALL PRIVILEGES ON DATABASE aicte_dashboard TO aicte;
     GRANT ALL PRIVILEGES ON DATABASE aicte_dashboard_test TO aicte;
     ```

---

## 2. Port Conflicts (5432, 8000, 5173)
### Symptom
`Error: listen EADDRINUSE: address already in use 0.0.0.0:8000` or `5173`

### Resolution
Check which process is using the port:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
```
Terminate the conflicting process:
```powershell
Stop-Process -Id <PID> -Force
```
Alternatively, configure a different port:
- Backend: `uvicorn app.main:app --port 8001`
- Frontend: `npm run dev -- --port 5174`

---

## 3. Python 3.13 Wheel Compatibility with Psycopg
### Symptom
`ERROR: Could not find a version that satisfies the requirement psycopg-binary==3.2.1`

### Resolution
Prebuilt wheels on Windows for Python 3.13 were introduced in `psycopg 3.2.3+`. The project dependencies specify `psycopg[binary]>=3.2.3`, which installs cleanly without requiring C compiler toolchains.

---

## 4. Resetting the Database / Deterministic Re-seed
### Symptom
Want to restore the database to the clean initial fixture state from Section 16/19.

### Resolution
Run the seed command with `--reset`:
```powershell
cd backend
python -m app.cli seed --reset
```
This drops all complaint/relation tables and recreates the deterministic synthetic scenario fixture (`SYN-TN-0001` Meridian Institute).

---

## 5. Token Expiry & Unauthorized Loops
### Symptom
Repeated redirects to `/login` or 401 Unauthorized API responses.

### Resolution
The JWT token is stored in `sessionStorage` under `aicte_token`. If expired, click the Logout button or clear session storage and log back in using one of the demo quick-fill buttons on the login screen.
