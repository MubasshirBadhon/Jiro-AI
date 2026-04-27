"""PDF Analyzer - Local PDF + image processing → API output.

Extracts text and images from PDFs locally using PyMuPDF,
then sends to AI for analysis and summarization.
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.ui.pdf")


class PDFAnalyzer:
    """Analyzes PDFs: extract text + images locally, analyze via AI."""

    def __init__(self, config: dict, ai_engine=None):
        self._config = config
        self._ai_engine = ai_engine

    async def analyze(self, file_path: str, query: Optional[str] = None) -> str:
        """Analyze a PDF file."""
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        if path.suffix.lower() != ".pdf":
            return "Not a PDF file."

        text, image_count = self._extract(path)

        if not text:
            return "Could not extract text from this PDF."

        parts = [f"Extracted {len(text)} characters, {image_count} images."]

        if self._ai_engine:
            prompt = query or "Summarize this document."
            ai_prompt = f"{prompt}\n\nDocument content:\n{text[:8000]}"
            analysis = await self._ai_engine.process(ai_prompt)
            parts.append(f"\n{analysis}")
        else:
            parts.append(f"\nFirst 1000 characters:\n{text[:1000]}")

        return "\n".join(parts)

    def _extract(self, path: Path) -> tuple[str, int]:
        """Extract text and count images from PDF."""
        try:
            import fitz
            doc = fitz.open(str(path))
            texts = []
            images = 0
            for page in doc:
                t = page.get_text()
                if t.strip():
                    texts.append(t)
                images += len(page.get_images())
            doc.close()
            return "\n".join(texts), images
        except ImportError:
            logger.warning("PyMuPDF not installed, trying pdftotext")
            return self._fallback_extract(path), 0

    def _fallback_extract(self, path: Path) -> str:
        import subprocess
        try:
            r = subprocess.run(["pdftotext", str(path), "-"],
                               capture_output=True, text=True, timeout=30)
            return r.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def extract_path(self, text: str) -> Optional[str]:
        """Extract file path from user command."""
        patterns = [r'["\']([^"\']+\.pdf)["\']', r'(\S+\.pdf)']
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1)

        # Try to find recently opened PDFs on the system
        recent = self._find_recent_pdfs()
        if recent:
            return str(recent[0])

        return None

    def _find_recent_pdfs(self) -> list[Path]:
        """Find recently modified PDF files in common locations."""
        import platform
        search_dirs = []
        home = Path.home()

        if platform.system() == "Windows":
            search_dirs = [
                home / "Desktop", home / "Downloads",
                home / "Documents", home / "OneDrive" / "Desktop",
            ]
        else:
            search_dirs = [home / "Desktop", home / "Downloads", home / "Documents"]

        pdfs = []
        for d in search_dirs:
            if d.exists():
                try:
                    pdfs.extend(d.glob("*.pdf"))
                except PermissionError:
                    continue

        # Sort by modification time (newest first)
        pdfs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return pdfs[:5]

    async def analyze_recent(self, query: Optional[str] = None) -> str:
        """Analyze the most recently opened/downloaded PDF."""
        pdfs = self._find_recent_pdfs()
        if not pdfs:
            return "No PDF files found on your Desktop or Downloads. Provide a path: 'analyze pdf C:\\path\\to\\file.pdf'"

        latest = pdfs[0]
        return await self.analyze(str(latest), query or f"Summarize this PDF: {latest.name}")
