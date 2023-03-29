import logging
import os
from datetime import datetime

import pyarrow.csv as pv
import pyarrow.parquet as pq
from airflow.operators.bash_operator import BashOperator
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
YELLOW_TAXI_CSV_FILE_TEMPLATE = AIRFLOW_HOME + \
    '/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.csv'
YELLOW_TAXI_PARQUET_FILE_TEMPLATE = AIRFLOW_HOME + \
    '/yellow_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.parquet'
YELLOW_TAXI_GCP_PATH_TEMPLATE = 'raw/yellow_tripdata/{{ execution_date.strftime(\'%Y\') }}/yellow_tripdata'


def format_to_parquet(src_file, destination_file):
    if not src_file.endswith('.csv'):
        logging.error(
            'Can only accept source files in CSV format, for the moment')
        return
    parse_options = pv.ParseOptions(delimiter=';')
    table = pv.read_csv(src_file, parse_options=parse_options)
    pq.write_table(table, destination_file)


def upload_to_gcs(bucket, object_name, local_file):
    client = storage.Client()
    bucket = client.bucket(bucket)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_file)
    print(
        f'File {local_file} uploaded to {bucket}.'
    )


default_args = {
    'owner': 'airflow',
    'start_date': datetime(2021, 1, 1),
    'depends_on_past': False,
    'retries': 1,
}


with DAG(
    dag_id='data_ingestion_gcs_dag_v2.0',
    start_date=datetime(2021, 1, 1),
    schedule_interval='0 6 2 * *',
    default_args=default_args,
    catchup=True,
    max_active_runs=3,
    tags=['dtc-de'],
) as dag:

    download_dataset_task = BashOperator(
        task_id='download_dataset_task',
        bash_command=f'curl -sSLf {YELLOW_TAXI_URL_TEMPLATE} > {YELLOW_TAXI_CSV_FILE_TEMPLATE}'
    )

    format_to_parquet_task = PythonOperator(
        task_id='format_to_parquet_task',
        python_callable=format_to_parquet,
        op_kwargs={
            'src_file': YELLOW_TAXI_CSV_FILE_TEMPLATE,
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
    download_dataset_task >> format_to_parquet_task >> local_to_gcs_task
