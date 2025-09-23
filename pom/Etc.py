from playwright.async_api import Page

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