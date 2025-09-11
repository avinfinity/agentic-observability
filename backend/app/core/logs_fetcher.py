
from elasticsearch import Elasticsearch
import threading
import time

class LogsFetcher:

  def fetch_logs(self, past_minutes=5):
    """
    Fetch logs from Elasticsearch from the last 5 minutes containing error, err, or warning.
    Returns:
      logs (str): Joined log messages from the last 5 minutes.
    """
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=past_minutes)
    # Elasticsearch expects ISO format
    start_iso = start_time.isoformat() + "Z"
    now_iso = now.isoformat() + "Z"
    try:
      resp = self.es_client.search(
        index=self.es_index,
        body={
          "query": {
            "bool": {
              "must": [
                {"range": {"@timestamp": {"gte": start_iso, "lte": now_iso}}},
                {"query_string": {
                  "query": "*error* OR *err* OR *warning*",
                  "fields": ["*"]
                }}
              ]
            }
          }
        },
        size=100,
        ignore_unavailable=True
      )
      logs = []
      import json
      for hit in resp['hits']['hits']:
        src = hit['_source']
        if 'message' in src and src['message']:
          logs.append(src['message'])
        else:
          logs.append(json.dumps(src))
      return "\n".join(logs)
    except Exception as e:
      return f"Error pulling logs: {e}"

  def __init__(self, es_host='http://localhost:9200', es_user='elastic', es_pass='changeme', es_index='logs-*-*,logs-*,filebeat-*', interval=300, periodic_pull=False):
    self.es_host = es_host
    self.es_user = es_user
    self.es_pass = es_pass
    self.es_index = es_index
    self.interval = interval
    self.es_client = Elasticsearch(
      [self.es_host],
      basic_auth=(self.es_user, self.es_pass)
    )
    self.latest_logs = ""
    if periodic_pull:
        self._start_periodic_pull()

  def _pull_logs(self):
    try:
      resp = self.es_client.search(index=self.es_index, body={"query": {"match_all": {}}}, size=100)
      logs = []
      for hit in resp['hits']['hits']:
        logs.append(hit['_source'].get('message', str(hit['_source'])))
      self.latest_logs = "\n".join(logs)
    except Exception as e:
      self.latest_logs = f"Error pulling logs: {e}"

  def _periodic_pull(self):
    while True:
      self._pull_logs()
      time.sleep(self.interval)

  def _start_periodic_pull(self):
    t = threading.Thread(target=self._periodic_pull, daemon=True)
    t.start()
