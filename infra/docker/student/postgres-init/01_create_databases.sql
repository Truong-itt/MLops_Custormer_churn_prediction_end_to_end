CREATE USER airflow WITH PASSWORD 'airflow';
CREATE USER mlflow WITH PASSWORD 'mlflow';

CREATE DATABASE airflow OWNER airflow;
CREATE DATABASE mlflow OWNER mlflow;
