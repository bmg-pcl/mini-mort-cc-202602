FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose both API and Streamlit ports
EXPOSE 8000 8501

# Run API and Streamlit together via a small shell script
CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port 8000 & streamlit run web/app.py --server.port 8501 --server.headless true"]
