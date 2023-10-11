FROM python:3.11-slim-bookworm 

# Upgrade system packages
RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y sqlite3 libsqlite3-dev

# Switch to non-root user
RUN useradd --create-home appuser
USER appuser

# Install dependencies
WORKDIR /usr/app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# TODO remove this and revert to plain copy once migrated to postgresql
COPY --chown=appuser:appuser . .
#COPY . . 

# Run the app
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
