from playwright.async_api import Page
import requests
import time

class Etc():
    def __init__(self, page: Page):
        self.page = page

    async def goto(self):
        await self.page.goto("https://m.gmarket.co.kr")

    async def login(self, username: str, password: str):
        await self.page.click("text=로그인")
        await self.page.fill("#typeMemberInputId", username)
        await self.page.fill("#typeMemberInputPassword", password)
        await self.page.click("#btn_memberLogin")

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