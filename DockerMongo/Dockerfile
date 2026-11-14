FROM python:3.12-slim
LABEL maintainer="Antonio Robles <bryan77robles@gmail.com>"
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["flask_brevets.py"]
