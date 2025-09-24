import requests
import time
import pandas as pd

def query_databricks(workspace_url: str, access_token: str, warehouse_id: str, sql: str):
    """
    Databricks SQL Warehouse API를 통해 SQL 실행 후 결과를 반환하는 함수

    Args:
        workspace_url (str): Databricks 워크스페이스 URL (예: https://<workspace>.databricks.com)
        access_token (str): Personal Access Token
        warehouse_id (str): 사용할 SQL Warehouse ID
        sql (str): 실행할 SQL 쿼리

    Returns:
        dict: 쿼리 결과 JSON
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 1. 쿼리 실행 요청
    submit_url = f"{workspace_url}/api/2.0/sql/statements"
    payload = {
        "statement": sql,
        "warehouse_id": warehouse_id,
        "wait_timeout": "30s",  # 결과 기다리는 시간
        "on_wait_timeout": "CONTINUE"  # 바로 안 끝나면 나중에 polling
    }

    response = requests.post(submit_url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    statement_id = data["statement_id"]

    # 2. 실행 상태 확인 (polling)
    status_url = f"{workspace_url}/api/2.0/sql/statements/{statement_id}"
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

    return state_data.get("result", {})

    # result = state_data.get("result", {})
    #
    # # 컬럼명 추출, 없으면 기본 이름 생성
    # rows = result.get("data_array", [])
    # columns_info = result.get("columns", [])
    # if columns_info:
    #     columns = [col.get("name", f"col{i}") for i, col in enumerate(columns_info)]
    # else:
    #     # 컬럼 정보가 없으면 0,1,2,...로 기본 생성
    #     columns = [f"col{i}" for i in range(len(rows[0]))] if rows else []
    #
    # # 컬럼 전체 표시
    # pd.set_option("display.max_columns", None)
    #
    # # 행 전체 표시 (많으면 주의)
    # pd.set_option("display.max_rows", None)
    #
    # # 열 값 전체 길이 표시
    # pd.set_option("display.max_colwidth", None)
    # df = pd.DataFrame(rows, columns=columns)
    # return df


workspace_url = "https://adb-5971940266401983.3.azuredatabricks.net"
access_token = "  "
warehouse_id = "8a389507a5bf8eb6"

sql = "select * from baikald1xs.kafka_silver.ub_ad_cpc_click_gmkt where dt ='20250822' and item_no = '8000052576' and cguid = '11750814611572002332000000'"

result = query_databricks(workspace_url, access_token, warehouse_id, sql)

print(result)
