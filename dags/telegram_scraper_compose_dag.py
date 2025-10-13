from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule

PROJECT_DIR = "/opt/projects/scraper3"       # docker-compose'daki isim
COMPOSE_FILE = "docker-compose.yaml"
PROJECT_NAME = "telegram_scraper_airflow"

default_args = {
    "owner": "airflow",
    "retries": 0,
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="telegram_scraper_compose_dag",
    description="Run the scraping project via docker compose",
    start_date=datetime(2025, 9, 1),
    schedule_interval=None,
    catchup=False,
    default_args=default_args,
    dagrun_timeout=timedelta(hours=6),
    tags=["scraper", "docker", "compose"],
) as dag:
    compose_up_cmd = f"""
    set -euo pipefail
    cd "{PROJECT_DIR}"

    docker compose -p "{PROJECT_NAME}" -f "{COMPOSE_FILE}" up --build --abort-on-container-exit
    """.strip()


    compose_up = BashOperator(
        task_id="docker_compose_up",
        bash_command=compose_up_cmd,
        env={},
    )

    # cleanup
    compose_down_cmd = f"""
        set -euo pipefail
        cd "{PROJECT_DIR}"
        docker compose -p "{PROJECT_NAME}" -f "{COMPOSE_FILE}" down -v --remove-orphans
    """.strip()

    compose_down = BashOperator(
        task_id="docker_compose_down",
        bash_command=compose_down_cmd,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    compose_up >> compose_down
