"""News Plugin - Quick news headlines."""

from plugins.plugin_loader import PluginBase


class NewsPlugin(PluginBase):
    name = "news"
    description = "Get latest news headlines"
    triggers = ["news", "headlines", "what's happening", "latest news",
                 "current events", "today's news"]

    async def execute(self, command: str, context: dict = None) -> str:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://newsdata.io/api/1/news?apikey=pub_0&language=en&category=top",
                    follow_redirects=True,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    articles = data.get("results", [])[:5]
                    if articles:
                        result = "Latest Headlines:\n\n"
                        for i, a in enumerate(articles, 1):
                            result += f"  {i}. {a.get('title', 'No title')}\n"
                            if a.get('description'):
                                result += f"     {a['description'][:100]}...\n"
                        return result
        except Exception:
            pass

        return ("For latest news, I can search the web for you.\n"
                "Say 'search [topic] news' or ask me about any current event!")
