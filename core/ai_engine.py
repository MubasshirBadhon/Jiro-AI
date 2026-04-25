"""Multi-provider AI Engine for Jiro AI.

Routes requests intelligently:
- NVIDIA (build.nvidia.com): Understands user prompt, separates tasks
- Groq + Gemini: Combined generation for quality responses
- HuggingFace: Heavy tasks (image generation, etc.)
- OpenRouter: Fallback provider
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger("jiro.ai_engine")

JIRO_SYSTEM_PROMPT = """You are Jiro AI, a personal AI assistant. You always introduce yourself as Jiro AI.
You are helpful, witty, and proactive. You act as a daily life partner - helping with scheduling,
studying, productivity, and general tasks. You understand both English and Bengali (Bangla).
You never mention or brand other AI providers - you are Jiro AI.
Keep responses natural and conversational. Be concise but thorough.
When the user speaks in Bengali/Bangla, respond in Bengali/Bangla.
You have access to the user's schedule, memory, and can set reminders and alarms."""


class AIEngine:
    """Multi-provider AI processing engine with smart routing."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.conversation_history: list[dict] = []
        self.max_history = config_manager.get("memory.max_conversation_history", 100)

    async def _call_nvidia(self, prompt: str) -> dict:
        """Use NVIDIA API to understand prompt and classify the task."""
        api_key = self.config.get_api_key("nvidia")
        if not api_key:
            return {"task_type": "general", "sub_tasks": [prompt], "original": prompt}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.get_model("nvidia_understanding"),
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Analyze the user's prompt and classify it. "
                                    "Return JSON with: task_type (general/heavy/scheduling/study/reminder), "
                                    "sub_tasks (list of subtasks), requires_heavy_compute (bool), "
                                    "original (original prompt). Only return valid JSON."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 500,
                        "temperature": 0.3,
                    },
                )

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"task_type": "general", "sub_tasks": [prompt], "original": prompt}
                else:
                    logger.warning("NVIDIA API error: %s", response.status_code)
                    return {"task_type": "general", "sub_tasks": [prompt], "original": prompt}
        except Exception as e:
            logger.error("NVIDIA call failed: %s", e)
            return {"task_type": "general", "sub_tasks": [prompt], "original": prompt}

    async def _call_groq(self, prompt: str, system_prompt: str = JIRO_SYSTEM_PROMPT) -> str:
        """Generate response using Groq API."""
        api_key = self.config.get_api_key("groq")
        if not api_key:
            return ""

        try:
            import httpx
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history[-20:])
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.get_model("groq_generation"),
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                    },
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    logger.warning("Groq API error: %s", response.status_code)
                    return ""
        except Exception as e:
            logger.error("Groq call failed: %s", e)
            return ""

    async def _call_gemini(self, prompt: str, system_prompt: str = JIRO_SYSTEM_PROMPT) -> str:
        """Generate response using Gemini API."""
        api_key = self.config.get_api_key("gemini")
        if not api_key:
            return ""

        try:
            import httpx
            history_text = "\n".join(
                f"{m['role']}: {m['content']}" for m in self.conversation_history[-20:]
            )
            full_prompt = f"{system_prompt}\n\nConversation history:\n{history_text}\n\nUser: {prompt}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{self.config.get_model('gemini_generation')}:generateContent",
                    params={"key": api_key},
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 2048,
                        },
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return ""
                else:
                    logger.warning("Gemini API error: %s", response.status_code)
                    return ""
        except Exception as e:
            logger.error("Gemini call failed: %s", e)
            return ""

    async def _call_huggingface(self, prompt: str, model: Optional[str] = None) -> str:
        """Use HuggingFace for heavy compute tasks."""
        api_key = self.config.get_api_key("huggingface")
        if not api_key:
            return ""

        model = model or self.config.get_model("huggingface_heavy")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"inputs": prompt},
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and data:
                        return data[0].get("generated_text", str(data))
                    return str(data)
                else:
                    logger.warning("HuggingFace API error: %s", response.status_code)
                    return ""
        except Exception as e:
            logger.error("HuggingFace call failed: %s", e)
            return ""

    async def _call_openrouter(self, prompt: str, system_prompt: str = JIRO_SYSTEM_PROMPT) -> str:
        """Fallback generation using OpenRouter."""
        api_key = self.config.get_api_key("openrouter")
        if not api_key:
            return ""

        try:
            import httpx
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history[-20:])
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.get_model("openrouter_fallback"),
                        "messages": messages,
                        "max_tokens": 2048,
                    },
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    logger.warning("OpenRouter API error: %s", response.status_code)
                    return ""
        except Exception as e:
            logger.error("OpenRouter call failed: %s", e)
            return ""

    async def _combine_responses(self, groq_response: str, gemini_response: str) -> str:
        """Combine Groq and Gemini responses for best quality."""
        if groq_response and gemini_response:
            combine_prompt = (
                f"Combine these two AI responses into one natural, coherent response. "
                f"Take the best parts from each. Keep it conversational.\n\n"
                f"Response A:\n{groq_response}\n\n"
                f"Response B:\n{gemini_response}\n\n"
                f"Combined response:"
            )
            combined = await self._call_groq(combine_prompt, system_prompt=JIRO_SYSTEM_PROMPT)
            return combined if combined else groq_response
        return groq_response or gemini_response or ""

    async def process(self, user_input: str, context: Optional[dict] = None) -> str:
        """Process user input through the multi-provider pipeline."""
        self.conversation_history.append({"role": "user", "content": user_input})

        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        task_analysis = await self._call_nvidia(user_input)
        task_type = task_analysis.get("task_type", "general")
        requires_heavy = task_analysis.get("requires_heavy_compute", False)

        logger.info("Task type: %s, Heavy: %s", task_type, requires_heavy)

        if requires_heavy:
            response = await self._call_huggingface(user_input)
            if not response:
                response = await self._call_groq(user_input)
        else:
            groq_task = self._call_groq(user_input)
            gemini_task = self._call_gemini(user_input)
            groq_response, gemini_response = await asyncio.gather(
                groq_task, gemini_task, return_exceptions=True
            )

            groq_response = groq_response if isinstance(groq_response, str) else ""
            gemini_response = gemini_response if isinstance(gemini_response, str) else ""

            response = await self._combine_responses(groq_response, gemini_response)

        if not response:
            response = await self._call_openrouter(user_input)

        if not response:
            response = "I'm sorry, I couldn't process that right now. Please check your API keys."

        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    async def stream_process(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream the AI response for real-time TTS."""
        self.conversation_history.append({"role": "user", "content": user_input})

        api_key = self.config.get_api_key("groq")
        if not api_key:
            yield "API keys not configured. Please set up your API keys."
            return

        try:
            import httpx
            messages = [{"role": "system", "content": JIRO_SYSTEM_PROMPT}]
            messages.extend(self.conversation_history[-20:])
            messages.append({"role": "user", "content": user_input})

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.get_model("groq_generation"),
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "stream": True,
                    },
                ) as response:
                    full_response = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

                    self.conversation_history.append(
                        {"role": "assistant", "content": full_response}
                    )
        except Exception as e:
            logger.error("Streaming failed: %s", e)
            yield f"I encountered an error: {e}"

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
