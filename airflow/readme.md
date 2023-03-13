## Start the folder using the below command. Why?

When running docker compose it will look up the environmnet variables in our .env
Without creating these directories, the Airflow container will not be able to find or store DAGs, logs, or plugins

```bash
mkdir -p ./dags ./logs ./plugins
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

## Init docker compose

```bash
docker compose build
```

```bash
docker-compose up airflow-init
```

```bash
docker-compose up -d
```
