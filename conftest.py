import pytest
import os
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import requests
from datetime import datetime
import tempfile
import io
from dotenv import load_dotenv

load_dotenv()

TESTRAIL_URL = os.environ.get("TESTRAIL_URL")
USERNAME = os.environ.get("TESTRAIL_USERNAME")
API_KEY = os.environ.get("TESTRAIL_API_KEY")
PROJECT_ID = int(os.environ.get("TESTRAIL_PROJECT_ID", 1))
SUITE_ID = int(os.environ.get("TESTRAIL_SUITE_ID", 1))
DB_ACCESS_TOKEN = os.environ.get("DB_ACCESS_TOKEN")

# 브라우저별 TestRail 런 ID 저장
testrail_run_ids = {}

# TestRail API 클래스
class TestRailAPI:
    def __init__(self):
        self.url = TESTRAIL_URL
        self.auth = (USERNAME, API_KEY)

    def create_test_run(self, browser_name):
        """브라우저별 테스트 런 생성"""
        url = f"{self.url}/index.php?/api/v2/add_run/{PROJECT_ID}"
        today = datetime.now().strftime("%Y-%m-%d")
        payload = {
            "suite_id": SUITE_ID,
            "name": f"E2E Test Run - {browser_name.capitalize()} - {today}",
            "include_all": True,
        }
        response = requests.post(url, json=payload, auth=self.auth)
        if response.ok:
            return response.json()["id"]
        else:
            print(f"❌ TestRail 런 생성 실패: {response.status_code} {response.text}")
            return None

    def add_result(self, run_id, case_id, status, comment="", attachments=None):
        """테스트 결과 추가"""
        url = f"{self.url}/index.php?/api/v2/add_result_for_case/{run_id}/{case_id}"
        status_map = {"passed": 1, "failed": 5, "skipped": 2}

        payload = {
            "status_id": status_map.get(status, 4),
            "comment": comment
        }

        response = requests.post(url, json=payload, auth=self.auth)
        if response.ok:
            result_id = response.json().get("id")

            # 첨부파일이 있으면 추가
            if attachments and result_id:
                for attachment in attachments:
                    self.attach_file(result_id, attachment)

            return result_id
        else:
            print(f"❌ TestRail 결과 전송 실패: {response.status_code} {response.text}")
            return None

    def attach_file(self, result_id, file_data):
        """파일을 TestRail에 첨부"""
        url = f"{self.url}/index.php?/api/v2/add_attachment_to_result/{result_id}"

        if isinstance(file_data, tuple):  # (filename, bytes, content_type)
            filename, content, content_type = file_data
            files = {'attachment': (filename, content, content_type)}
        else:  # bytes
            files = {'attachment': ('screenshot.png', file_data, 'image/png')}

        response = requests.post(url, files=files, auth=self.auth)
        if response.ok:
            print(f"✅ TestRail 첨부 완료: {filename if isinstance(file_data, tuple) else 'screenshot.png'}")
        else:
            print(f"❌ TestRail 첨부 실패: {response.text}")


# 실패 시 아티팩트 캡처 및 TestRail 업로드
@pytest.fixture(autouse=True)
async def capture_failure_artifacts(request, page: Page):
    yield

    # 테스트 결과 확인
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        # TestRail case ID 확인
        case_id = None
        for marker in request.node.iter_markers():
            if marker.name in ['testrail_id', 'testrail_case_id']:
                case_id = marker.args[0]
                break

        if case_id:
            # 브라우저 정보 추출
            browser_name = "unknown"
            if hasattr(request.node, 'callspec'):
                browser_name = request.node.callspec.id

            # 스크린샷 캡처 (메모리에 저장)
            screenshot_bytes = await page.screenshot(full_page=True)

            # 로그 생성 (메모리에 저장)
            log_content = f"""
테스트 실패 정보:
- 테스트: {request.node.name}
- 브라우저: {browser_name}
- 실패 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 실패 원인: {request.node.rep_call.longrepr}
            """.encode('utf-8')

            # TestRail에 결과 및 첨부파일 전송
            api = TestRailAPI()
            run_id = testrail_run_ids.get(browser_name)
            if run_id:
                result_id = api.add_result(
                    run_id=run_id,
                    case_id=case_id,
                    status="failed",
                    comment=f"테스트 실패 - 브라우저: {browser_name}",
                    attachments=[
                        ("screenshot.png", screenshot_bytes, "image/png"),
                        ("error_log.txt", log_content, "text/plain")
                    ]
                )
                if result_id:
                    print(f"✅ TestRail에 실패 결과 업로드 완료: {case_id}")


# 성공 시 TestRail 기록
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()
    setattr(item, "rep_" + call.when, result)

    if call.when == "call" and result.passed:
        # TestRail case ID 확인
        case_id = None
        for marker in item.iter_markers():
            if marker.name in ['testrail_id', 'testrail_case_id']:
                case_id = marker.args[0]
                break

        if case_id:
            # 브라우저 정보 추출
            browser_name = "unknown"
            if hasattr(item, 'callspec'):
                browser_name = item.callspec.id

            # TestRail에 성공 결과 전송
            api = TestRailAPI()
            run_id = testrail_run_ids.get(browser_name)
            if run_id:
                api.add_result(
                    run_id=run_id,
                    case_id=case_id,
                    status="passed",
                    comment=f"테스트 성공 - 브라우저: {browser_name}"
                )


# 마커를 통한 TestRail ID 설정
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    for marker in item.iter_markers():
        if marker.name in ['testrail_id', 'testrail_case_id']:
            item.testrail_case_id = marker.args[0]
            break


# pytest 옵션 설정
def pytest_addoption(parser):
    parser.addoption("--browsers", action="store", default="chromium,firefox",
                     help="Comma-separated list of browsers to test")
    parser.addoption("--testrail", action="store_true", default=True,
                     help="Enable TestRail integration")


def pytest_configure(config):
    config.browsers = config.getoption("--browsers").split(",")
    config.testrail_enabled = config.getoption("--testrail")


# 브라우저별 TestRail 런 생성
@pytest.fixture(scope="session", autouse=True)
def setup_testrail_runs(pytestconfig):
    if pytestconfig.testrail_enabled:
        api = TestRailAPI()
        for browser in pytestconfig.browsers:
            run_id = api.create_test_run(browser)
            testrail_run_ids[browser] = run_id
            print(f"✅ TestRail 런 생성: {browser} -> {run_id}")


# 브라우저 타입 fixture (동시 실행 지원)
@pytest.fixture(scope="function", params=["chromium", "firefox"])
async def browser_type(request):
    async with async_playwright() as p:
        browser_launcher = getattr(p, request.param)
        browser = await browser_launcher.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        yield browser
        await browser.close()

# 브라우저별 기본 디바이스 설정
BROWSER_DEVICE_CONFIG = {
    "chromium": {
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) "
            "Chrome/114.0.5735.196 Mobile Safari/537.36"
        ),
        "viewport": {"width": 412, "height": 915},
        "is_mobile": True,
        "device_scale_factor": 2.5,
        "has_touch": True,
        "locale": "ko-KR"
    },
    "firefox": {
        "user_agent": (
            "Mozilla/5.0 (Android 11; Mobile; rv:109.0) "
            "Gecko/109.0 Firefox/109.0"
        ),
        "viewport": {"width": 412, "height": 915},
        "is_mobile": True,
        "device_scale_factor": 2.5,
        "has_touch": True,
        "locale": "ko-KR"
    }
}

# 컨텍스트 fixture (브라우저별 디바이스 1:1)
@pytest.fixture(scope="function")
async def context(browser_type: Browser, request) -> BrowserContext:
    browser_name = request.param if hasattr(request, 'param') else browser_type.name
    device = BROWSER_DEVICE_CONFIG.get(browser_name, BROWSER_DEVICE_CONFIG["chromium"])
    context = await browser_type.new_context(**device)

    # Stealth 우회용 init script
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    yield context
    await context.close()


# 페이지 fixture
@pytest.fixture(scope="function")
async def page(context: BrowserContext) -> Page:
    page = await context.new_page()
    page.set_default_timeout(10000)
    yield page
    await page.close()