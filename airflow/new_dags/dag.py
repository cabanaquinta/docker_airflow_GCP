import os
from datetime import datetime, timedelta

import pandas as pd
from airflow.operators.python import PythonOperator
from google.cloud import storage

from airflow import DAG

# VARIABLES
PROJECT_ID = os.environ.get('GCP_PROJECT_ID')
BUCKET = os.environ.get('GCP_GCS_BUCKET')

URL_PREFIX = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow'
AIRFLOW_HOME = '/opt/airflow'

YELLOW_TAXI_URL_TEMPLATE = URL_PREFIX + \
    '/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.csv.gz'
# YELLOW_TAXI_CSV_FILE_TEMPLATE = AIRFLOW_HOME + \
#     '/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.csv.gz'
YELLOW_TAXI_PARQUET_FILE_TEMPLATE = AIRFLOW_HOME + \
    '/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.parquet'
YELLOW_TAXI_GCP_PATH_TEMPLATE = 'raw/yellow_tripdata/{{ execution_date.strftime(\'%Y\') }}/{{ execution_date.strftime(\'%m\') }}'


def upload_to_gcs(bucket, object_name, local_file):
    """Upload to Bucket"""
    client = storage.Client()
    bucket = client.bucket(bucket)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_file)
    print(
        f'File {local_file} uploaded to {bucket}.'
    )


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Fix dtype issues"""
    df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
    df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'])
    return df


def write_local(df: pd.DataFrame, destination_file) -> None:
    """Write DataFrame out locally as parquet file"""
    df.to_parquet(destination_file, compression='gzip')


def read_and_transform_to_parquet(src_file: str, destination_file: str) -> pd.DataFrame:
    """Read Transform and Save"""
    df = pd.read_csv(src_file)
    df = clean(df)
    write_local(df, destination_file)


default_args = {
    'owner': 'airflow',
    'rety_delay': timedelta(minutes=5),
    'retries': 1,
}


with DAG(
    dag_id='data_ingestion_gcs_dag_v3.0',
    start_date=datetime(2021, 1, 1),
    end_date=datetime(2021, 8, 1),
    schedule_interval='0 6 2 * *',
    default_args=default_args,
    catchup=False,
    max_active_runs=3,
    tags=['dtc-de'],
) as dag:

    etl_web_local_task = PythonOperator(
        task_id='download_dataset_task',
        python_callable=read_and_transform_to_parquet,
        op_kwargs={
            'src_file': YELLOW_TAXI_URL_TEMPLATE,
            'destination_file': YELLOW_TAXI_PARQUET_FILE_TEMPLATE
        },
    )

    local_to_gcs_task = PythonOperator(
        task_id='local_to_gcs_task',
        python_callable=upload_to_gcs,
        op_kwargs={
            'bucket': BUCKET,
            'object_name': YELLOW_TAXI_GCP_PATH_TEMPLATE,
            'local_file': YELLOW_TAXI_PARQUET_FILE_TEMPLATE,
        },
    )

    # Workflow for task direction
    etl_web_local_task >> local_to_gcs_task
