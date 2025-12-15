# AAU Startups Portal Backend

Backend API for the AAU Startups Portal, built with Django and Django Rest Framework.

## Features
- **Authentication**: User registration, login, and profile management (Student, Mentor, Admin).
- **Startups**: Manage startups, ideas, phases, and milestones.
- **Matching**: Co-founder matching API.
- **Documentation**: Swagger UI available at `/swagger/`.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd startup
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory with the following content:
    ```env
    DEBUG=True
    SECRET_KEY=your_secret_key
    DB_NAME=startup_portal
    DB_USER=postgres
    DB_PASSWORD=your_password
    DB_HOST=localhost
    DB_PORT=5432
    ```

5.  **Run Migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Run the Server:**
    ```bash
    python manage.py runserver
    ```

## API Documentation
Access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`
