FROM python:3.11-slim
WORKDIR /app
COPY sokrat.py
RUN mkdir -p /app/data
VOLUME ["/app/data"]
CMD ["python", "-u", "sokrat.py"]