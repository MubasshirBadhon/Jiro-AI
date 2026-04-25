"""Web Search Plugin - Search the web for information."""

from plugins.plugin_loader import PluginBase
import re


class WebSearchPlugin(PluginBase):
    name = "web_search"
    description = "Search the web for information"
    triggers = ["search", "google", "look up", "find", "search for", "search about"]

    async def execute(self, command: str, context: dict = None) -> str:
        query = re.sub(r'(?:search|google|look up|find|search for|search about)\s*', '', command, flags=re.IGNORECASE).strip()
        if not query:
            return "What should I search for?"

        try:
            import httpx
            url = f"https://lite.duckduckgo.com/lite/?q={query}&kl=wt-wt"
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    abstract = data.get("AbstractText", "")
                    if abstract:
                        source = data.get("AbstractSource", "")
                        return f"{abstract}\n\n(Source: {source})"

                    related = data.get("RelatedTopics", [])
                    if related:
                        results = []
                        for r in related[:5]:
                            if isinstance(r, dict) and "Text" in r:
                                results.append(f"  - {r['Text'][:150]}")
                        if results:
                            return f"Search results for '{query}':\n" + "\n".join(results)
        except Exception:
            pass

        import webbrowser
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        try:
            webbrowser.open(search_url)
            return f"I've opened a Google search for '{query}' in your browser."
        except Exception:
            return f"Search for: {search_url}"
