import requests
import time
import pandas as pd

class DatabricksSPClient:
    def __init__(self, workspace_url, tenant_id, client_id, client_secret, warehouse_id):
        self.workspace_url = workspace_url.rstrip("/")
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.warehouse_id = warehouse_id
        self.access_token = self.get_access_token()

    def get_access_token(self):
        """Service Principal로 OAuth2 토큰 발급"""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://databricks.azure.net/.default"
        }
        res = requests.post(token_url, data=payload)
        res.raise_for_status()
        return res.json()["access_token"]

    def query_to_dataframe(self, sql: str, wait_timeout="30s"):
        """Databricks SQL Warehouse에서 쿼리 실행 후 DataFrame으로 반환"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # 1. 쿼리 실행 요청
        submit_url = f"{self.workspace_url}/api/2.0/sql/statements"
        payload = {
            "statement": sql,
            "warehouse_id": self.warehouse_id,
            "wait_timeout": wait_timeout,
            "on_wait_timeout": "CONTINUE"
        }
        res = requests.post(submit_url, headers=headers, json=payload)
        res.raise_for_status()
        statement_id = res.json()["statement_id"]

        # 2. 쿼리 실행 상태 확인 (polling)
        status_url = f"{self.workspace_url}/api/2.0/sql/statements/{statement_id}"
        while True:
            res = requests.get(status_url, headers=headers)
            res.raise_for_status()
            state_data = res.json()
            state = state_data.get("status", {}).get("state")
            if state in ("SUCCEEDED", "FAILED", "CANCELED"):
                break
            time.sleep(2)

        if state != "SUCCEEDED":
            raise Exception(f"Query failed with state: {state}")

        # 3. 결과를 DataFrame으로 변환
        result = state_data.get("result", {})
        columns = [col["name"] for col in result.get("columns", [])]
        rows = result.get("data_array", [])
        df = pd.DataFrame(rows, columns=columns)
        return df