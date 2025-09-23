class Vip():
    def __init__(self, page):
        self.page = page

    async def select_first_product(self):
        await self.page.click("css=ul.search-list > li:first-child a")

    async def click_buy_now(self):
        await self.page.click("text=바로구매")