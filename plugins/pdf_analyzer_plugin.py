"""PDF Analyzer Plugin - Extract and analyze PDF documents."""

from plugins.plugin_loader import PluginBase


class PDFAnalyzerPlugin(PluginBase):
    name = "pdf_analyzer"
    description = "Analyze PDF documents - extract text and get AI summaries"
    triggers = ["pdf", "analyze pdf", "read pdf", "open pdf"]
    version = "1.0.0"
    requires_api_keys = ["groq"]

    async def execute(self, command, context=None):
        try:
            from ui.pdf_analyzer import PDFAnalyzer
            analyzer = PDFAnalyzer(self.config, self.ai_engine)
            path = analyzer.extract_path(command)
            if path:
                return await analyzer.analyze(path, command)
            return "Please provide a PDF file path. Example: 'analyze pdf C:\\docs\\paper.pdf'"
        except Exception as e:
            return f"PDF analysis error: {e}"
