"""Citation Plugin - Generate citations in APA, MLA, Chicago formats."""

from plugins.plugin_loader import PluginBase
import re
from datetime import datetime


class CitationPlugin(PluginBase):
    name = "citation"
    description = "Generate academic citations in APA, MLA, Chicago format"
    triggers = ["cite", "citation", "reference", "bibliography", "apa", "mla"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        year = datetime.now().year

        # Website citation
        url_match = re.search(r'(https?://\S+)', command)
        if url_match:
            url = url_match.group(1)
            domain = url.split("//")[-1].split("/")[0]
            return (f"APA: {domain}. ({year}). Retrieved from {url}\n"
                    f"MLA: \"{domain}.\" Web. {datetime.now().strftime('%d %b. %Y')}. <{url}>.\n"
                    f"\n(For accurate citations, provide: author, title, date, publisher)")

        # Book citation template
        if "book" in lower:
            return ("Book Citation Template:\n"
                    f"  APA: Author, A. A. ({year}). Title of book (edition). Publisher.\n"
                    f"  MLA: Author. Title of Book. Publisher, {year}.\n"
                    f"  Chicago: Author. Title of Book. Place: Publisher, {year}.\n"
                    f"\nTell me: 'cite book by [author] titled [title] published by [publisher]'")

        # Journal article template
        if "journal" in lower or "article" in lower or "paper" in lower:
            return ("Journal Article Template:\n"
                    f"  APA: Author, A. ({year}). Title of article. Journal Name, volume(issue), pages.\n"
                    f"  MLA: Author. \"Title.\" Journal Name, vol. X, no. X, {year}, pp. X-X.\n"
                    f"\nTell me the details and I'll format it for you!")

        return ("Citation Generator:\n"
                "  'cite https://example.com' - cite a website\n"
                "  'cite book' - book citation template\n"
                "  'cite journal' - article template\n"
                "  Supported formats: APA, MLA, Chicago")
