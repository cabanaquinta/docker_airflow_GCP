## Start the folder using the below command. Why?

When running docker compose it will look up the environmnet variables in our .env
Without creating these directories, the Airflow container will not be able to find or store DAGs, logs, or plugins

```bash
mkdir -p ./dags ./logs ./plugins
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

## Start Airflow

```bash
cd airflow
```

```bash
docker build . --tag extending_airflow:latest
```

```bash
docker-compose up airflow-init
```

```bash
docker-compose up -d
```

## Enter the Airflow Container and Manually Backfill the Runs

We can pick the id of any of the airflow containers: scheduler, worker, server

```bash
docker exec -it <mycontainer> bash
```

```bash
airflow dags backfill -s 2021-04-01 -e 2022-01-01 data_ingestion_gcs_dag_v3.0
```

## Create bigquery table

```sql
CREATE OR REPLACE EXTERNAL TABLE dtc-de-378314.my_rides_alex.yellow_tripdata
PARTITION BY
    DATE(tpep_pickup_datetime)
CLUSTER BY
    tags
SELECT
 *
FROM
    dtc-de-378314.my_rides_alex.yellow_tripdata
OPTIONS (
  format = 'parquet',
  uris = [
    'gs://dtc_data_lake_dtc-de-378314/raw/yellow_tripdata/2021/*'
  ]
)
```
