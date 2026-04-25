"""PDF Analyzer Plugin for Jiro AI.

Processes PDFs including text extraction and image analysis.
Text extraction is done locally; content analysis uses AI APIs.
"""

import logging
from pathlib import Path
from typing import Optional

from core.plugin_loader import PluginBase

logger = logging.getLogger("jiro.plugins.pdf")


class PDFAnalyzerPlugin(PluginBase):
    name = "pdf_analyzer"
    description = "Analyze PDF files - extract text, analyze images, summarize content"
    triggers = [
        "pdf", "analyze pdf", "read pdf", "summarize pdf",
        "document", "extract text", "open pdf",
    ]
    version = "1.0.0"
    requires_api_keys = ["groq"]

    async def execute(self, command: str, context: Optional[dict] = None) -> str:
        file_path = self._extract_file_path(command)
        if not file_path:
            if context and "file_path" in context:
                file_path = context["file_path"]
            else:
                return "Please provide a PDF file path. Example: 'analyze pdf C:\\Users\\docs\\report.pdf'"

        if not Path(file_path).exists():
            return f"File not found: {file_path}"

        if not file_path.lower().endswith(".pdf"):
            return "Please provide a PDF file."

        try:
            text, images = await self._extract_content(file_path)

            if not text and not images:
                return "Could not extract any content from the PDF."

            summary_parts = []

            if text:
                summary_parts.append(f"Extracted {len(text)} characters of text.")

                if self.ai_engine:
                    truncated_text = text[:8000]
                    analysis = await self.ai_engine.process(
                        f"Analyze and summarize this PDF content:\n\n{truncated_text}"
                    )
                    summary_parts.append(f"\nAnalysis:\n{analysis}")
                else:
                    summary_parts.append(f"\nFirst 500 characters:\n{text[:500]}")

            if images:
                summary_parts.append(f"\nFound {len(images)} images in the PDF.")

            return "\n".join(summary_parts)

        except Exception as e:
            logger.error("PDF analysis failed: %s", e)
            return f"Error analyzing PDF: {e}"

    async def _extract_content(self, file_path: str) -> tuple[str, list]:
        """Extract text and images from PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return await self._extract_text_fallback(file_path), []

        text_parts = []
        images = []

        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]

            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            for img_index, img in enumerate(page.get_images()):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    if base_image:
                        images.append({
                            "page": page_num + 1,
                            "index": img_index,
                            "data": base_image["image"],
                            "ext": base_image["ext"],
                        })
                except Exception as e:
                    logger.warning("Failed to extract image: %s", e)

        doc.close()
        return "\n".join(text_parts), images

    async def _extract_text_fallback(self, file_path: str) -> str:
        """Fallback text extraction without PyMuPDF."""
        try:
            import subprocess
            result = subprocess.run(
                ["pdftotext", file_path, "-"],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def _extract_file_path(self, command: str) -> Optional[str]:
        """Extract file path from command text."""
        import re

        patterns = [
            r'["\']([^"\']+\.pdf)["\']',
            r'(\S+\.pdf)',
            r'([A-Za-z]:\\[^\s]+)',
            r'(/[^\s]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                path = match.group(1)
                if Path(path).suffix.lower() == ".pdf" or Path(path).exists():
                    return path
        return None
