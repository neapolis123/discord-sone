FROM python:3.11-slim-buster

COPY . .

RUN pip install -r requirements.txt

CMD ["python3","-u","main.py"]
