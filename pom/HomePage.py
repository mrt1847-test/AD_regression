class HomePage():
    def __init__(self, page):
        self.page = page

    async def search_product(self, keyword: str):
        await self.page.fill("input[name='keyword']", keyword)
        await self.page.press("input[name='keyword']", "Enter")