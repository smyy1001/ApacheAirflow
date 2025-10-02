from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
import os
import base64
from urllib.parse import urlparse
from typing import Tuple, Union, Dict
import requests
from airflow import DAG
from airflow.hooks.base import BaseHook
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from typing import Tuple, Optional
import logging

HEADERS = {"Content-Type": "application/json"}


ILM_BODY = r"""
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "set_priority": { "priority": 100 }
        }
      },
      "warm": {
        "min_age": "15d",
        "actions": {
          "set_priority": { "priority": 50 },
          "migrate": { "enabled": true }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "set_priority": { "priority": 25 },
          "migrate": { "enabled": true }
        }
      }
    }
  }
}
"""

INDEX_TEMPLATE_BODY = r"""
{
  "index_patterns": ["media-*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "30s",
      "index.lifecycle.name": "media_tiers_policy",
      "index.routing.allocation.include._tier_preference": "data_hot"
    },
    "mappings": {
      "properties": {
        "url":            { "type": "keyword" },
        "type":           { "type": "keyword" },
        "source":         { "type": "keyword" },
        "account_id":     { "type": "keyword" },
        "username":       { "type": "keyword" },
        "account_url":    { "type": "keyword" },
        "post_id":        { "type": "keyword" },
        "post_url":       { "type": "keyword" },
        "tags":           { "type": "keyword" },
        "created_at":     { "type": "date"    },
        "scraped_at":     { "type": "date"    },
        "matched_keyword":{ "type": "keyword" },
        "media_class":    { "type": "keyword" },
        "download_status":  { "type": "keyword" },
        "download_attempts":{ "type": "integer" },
        "last_error":       { "type": "text" },
        "bytes":            { "type": "long" },
        "width":            { "type": "integer" },
        "height":           { "type": "integer" },
        "duration_ms":      { "type": "long" },
        "stored_path":      { "type": "keyword" }
      }
    }
  },
  "priority": 100
}
"""


def _env(key: str, default=None):
    v = os.getenv(key)
    return v if (v is not None and v != "") else default

def _env_bool(key: str, default=False) -> bool:
    v = _env(key)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "t", "yes", "y", "on")

def _to_bool(val, default=False):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() not in {"false", "0", "no", "off", ""}
    return default

def _get_es_conn() -> Tuple[str, Dict[str, str], Union[bool, str]]:

    base_url = _env("ES_BASE_URL")
    if not base_url:
        schema = (_env("ES_SCHEMA", "https") or "https").lower()
        host = _env("ES_HOST", "192.168.1.66")
        port = _env("ES_PORT")
        base_url = f"{schema}://{host}{f':{port}' if port else ''}"

    api_key = _env("ES_API_KEY")
    api_key_id = _env("ES_API_KEY_ID")
    api_key_secret = _env("ES_API_KEY_SECRET")

    if api_key:
        encoded_key = (base64.b64encode(api_key.encode()).decode()
                       if ":" in api_key else api_key)
    elif api_key_id and api_key_secret:
        encoded_key = base64.b64encode(f"{api_key_id}:{api_key_secret}".encode()).decode()
    else:
        raise RuntimeError(
            "ES API key bulunamadı. 'ES_API_KEY' (encoded veya 'id:secret') "
            "ya da 'ES_API_KEY_ID' + 'ES_API_KEY_SECRET' verin."
        )

    headers: Dict[str, str] = {"Authorization": f"ApiKey {encoded_key}"}


    disable_cert = _env_bool("ES_DISABLE_SSL_CERT_VALIDATION", False)
    ca_path = _env("ES_CA_PATH")
    if ca_path:
        verify: Union[bool, str] = ca_path
    else:
        verify = (not disable_cert) and _env_bool("ES_VERIFY", True)


    return base_url, headers, verify




def wait_for_es_ready() -> bool:
    base_url, headers, verify = _get_es_conn()
    client_timeout = float(os.getenv("ES_TIMEOUT", "35")) 

    try:
        resp = requests.get(
            f"{base_url}/_cluster/health",
            params={"wait_for_status": "yellow", "timeout": "30s"},
            headers=headers,
            verify=verify,
            timeout=client_timeout,
        )
        if not resp.ok:
            logging.warning("ES health http=%s body=%s", resp.status_code, resp.text[:300])
            return False

        data = resp.json()
        status = str(data.get("status", "")).lower()
        ready = status in {"yellow", "green"}
        if not ready:
            logging.info("ES health status=%s timed_out=%s", status, data.get("timed_out"))
        return ready

    except Exception as e:
        logging.exception("ES health check exception: %r", e)
        return False


def put_ilm_policy(**_):
    base_url, headers, verify = _get_es_conn()
    timeout = float(os.getenv("ES_TIMEOUT", "60"))

    resp = requests.put(
        f"{base_url}/_ilm/policy/media_tiers_policy",
        headers=headers,
        json=json.loads(ILM_BODY),
        verify=verify,
        timeout=timeout,
    )
    if not resp.ok:
        raise RuntimeError(f"ILM PUT failed: {resp.status_code} {resp.text[:500]}")


def put_index_template(**_):
    base_url, headers, verify = _get_es_conn()
    timeout = float(os.getenv("ES_TIMEOUT", "60"))

    resp = requests.put(
        f"{base_url}/_index_template/media_template",
        headers=headers,
        json=json.loads(INDEX_TEMPLATE_BODY),
        verify=verify,
        timeout=timeout,
    )
    if not resp.ok:
        raise RuntimeError(f"Template PUT failed: {resp.status_code} {resp.text[:500]}")


default_args = {
    "owner": "data",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="bootstrap_es_for_media",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["media_api", "elasticsearch", "bootstrap"],
) as dag:

    es_up = PythonSensor(
        task_id="wait_for_es",
        poke_interval=10,
        timeout=300,
        mode="poke",
        python_callable=wait_for_es_ready,
    )

    put_ilm = PythonOperator(
        task_id="put_ilm_policy",
        python_callable=put_ilm_policy,
    )

    put_template = PythonOperator(
        task_id="put_index_template",
        python_callable=put_index_template,
    )

    es_up >> put_ilm >> put_template
