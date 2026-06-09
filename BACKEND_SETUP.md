# Beginner Setup Guide — SpellScroll

Follow these step-by-step instructions to initialize and run the SpellScroll server on your local environment.

---

## 1. Prerequisites
Ensure you have the following installed on your machine:
- **Python 3.11**
- **Git**

---

## 2. Setting Up the Virtual Environment
A virtual environment keeps the project dependencies isolated from your main operating system python.

In your terminal, run:
```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
# On Windows (Command Prompt):
.\venv\Scripts\activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate
```
*What this does:* Initializes a sandboxed folder containing a copy of the Python compiler and the `pip` package manager.

---

## 3. Installing Dependencies
Run the installation command:
```bash
pip install -r requirements.txt
```
*What this does:* Downloads and installs Django, FastAPI, PyTorch (for sentence-transformers), ChromaDB, Uvicorn, and other packages listed in the requirements configuration.

---

## 4. Setup Environment Variables
Copy the environmental file template:
```bash
# Verify that '.env' exists in the root folder.
# Customize any keys if available (e.g. CERBERUS_API_KEY, SERPAPI_KEY).
```
*What this does:* Configures local credentials, SQLite paths, and flags. By default, mock overrides are configured, enabling the server to run fully offline without any API keys.

---

## 5. Perform Database Migrations
Initialize the relational schema:
```bash
python manage.py makemigrations auth_core webtoons feed
python manage.py migrate
```
*What this does:* Connects to the SQLite database and compiles the user, catalog, feed logs, and cycle tables.

---

## 6. Run the Test Suite
Ensure all components are operating correctly:
```bash
pytest
```
*What this does:* Validates the vector database indexes, local embeddings generation, and API endpoints using automated unit tests.

---

## 7. Start the Development Server
Launch the unified ASGI application:
```bash
python manage.py runserver 0.0.0.0:8000
```
*What this does:* Spawns a local web server binding to port `8000` accessible to any device on the local network (such as an Android phone connected to the same Wi-Fi) at `http://{your_local_ip}:8000`.

---

## 8. Admin Credentials
To access administrative operations:
- **URL**: `http://localhost:8000/admin-spell/`
- **Username**: `spellmaster`
- **Password**: `Scroll@Admin2025!`
*(These can be updated inside settings.py or .env file before moving to staging.)*
