FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "pydantic>=2.9" pydantic-settings sqlalchemy "psycopg[binary]" "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt==4.0.1" cryptography httpx "langgraph>=0.2,<0.3" "langchain-core>=0.3" langsmith redis python-dotenv slowapi
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
