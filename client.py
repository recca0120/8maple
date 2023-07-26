import aiohttp


class Http:
    timeouts = (5, 10)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    }

    async def get(self, url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()

                return await response.read()

    async def head(self, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.head(url, headers=self.headers) as response:
                response.raise_for_status()

                return response.headers
