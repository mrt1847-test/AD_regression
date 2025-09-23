# tests/test_gmarket_purchase_flow.py
import pytest
import json
import os
import platform

from pom.SrpPage import Srp
from pom.VipPage import Vip
from pom.HomePage import HomePage
from pom.Etc import Etc


#pipenv run pytest --cache-clear test.py --asyncio-mode=auto -n 4
@pytest.mark.asyncio
@pytest.mark.testrail_id("C1234")
async def test(page,request):
    test_id = request.node.name
    etc = Etc(page)
    srp_page = Srp(page)
    vip_page = Vip(page)
    home_page = HomePage(page)
    try:
        await etc.goto()
        await etc.login("cease2504", "")

        await srp_page.search_product("무선 이어폰")
        await vip_page.select_first_product()
        await vip_page.click_buy_now()

        await order.complete_purchase()

    except Exception as e:
        await page.screenshot(path="error_screenshot.png")
        raise e  # 테스트를 실패로 처리