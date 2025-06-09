FROM python:3.11-slim

WORKDIR /app

# Copy only the main_project and shared directories
COPY main_project/ ./main_project/
COPY shared/ ./shared/

RUN pip install --no-cache-dir -r main_project/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "main_project.app.main:app", "--host", "0.0.0.0", "--port", "8001"] 