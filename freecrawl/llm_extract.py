"""
LLM-powered structured extraction.
Takes a URL + JSON schema, scrapes page, sends to LLM, returns structured JSON.
"""
import json, time
from typing import Dict, Any, Optional, List
from .config import Config
from .scraper import Scraper


class LLMExtractor:
    """Extract structured data from web pages using an LLM."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.scraper = Scraper(self.config)

    def extract(self, url: str, schema: Dict[str, Any] = None,
                instruction: str = None, model: str = None,
                format_type: str = "json") -> Dict[str, Any]:
        """Extract structured data from a URL using LLM.

        Args:
            url: Web page URL to extract from
            schema: JSON schema defining expected output structure
            instruction: Custom instruction for the LLM
            model: Override LLM model
            format_type: "json" for structured data, "summary" for summary

        Returns:
            Dict with extracted data
        """
        start = time.time()

        # Scrape the page
        page = self.scraper.scrape(url, formats=["markdown"])
        content = page.get("markdown") or page.get("text") or ""

        if not content:
            return {
                "error": "No content extracted from page",
                "metadata": page.get("metadata", {}),
                "elapsed": round(time.time() - start, 2),
            }

        # Truncate very long content
        max_chars = 15000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[Content truncated...]"

        # Build the prompt
        if format_type == "summary":
            prompt = self._build_summary_prompt(content, instruction)
        elif schema:
            prompt = self._build_extract_prompt(content, schema, instruction)
        else:
            prompt = self._build_extract_prompt(content, {"description": "Extract all key information"}, instruction)

        # Call the LLM
        llm_result = self._call_llm(prompt, model=model or self.config.llm_model,
                                    format_type=format_type)

        elapsed = round(time.time() - start, 2)

        return {
            "data": llm_result.get("data"),
            "raw_response": llm_result.get("raw"),
            "model_used": model or self.config.llm_model,
            "metadata": {
                "url": url,
                "content_length": len(content),
                "elapsed": elapsed,
                "format": format_type,
            },
        }

    def _build_extract_prompt(self, content: str, schema: Dict[str, Any],
                              instruction: str = None) -> str:
        schema_str = json.dumps(schema, indent=2)
        instr = instruction or f"Extract structured data matching this JSON schema."
        return f"""{instr}

Return ONLY valid JSON. Do NOT include markdown code blocks or any text outside the JSON.

SCHEMA:
{schema_str}

PAGE CONTENT:
{content}

JSON OUTPUT:"""

    def _build_summary_prompt(self, content: str, instruction: str = None) -> str:
        instr = instruction or "Summarize the following web page content concisely."
        return f"""{instr}

Return a concise summary of the key information. Format as plain text.

PAGE CONTENT:
{content}

SUMMARY:"""

    def _call_llm(self, prompt: str, model: str = "deepseek-chat",
                  format_type: str = "json") -> Dict[str, Any]:
        """Call an OpenAI-compatible LLM API."""
        api_key = self.config.llm_api_key
        if not api_key:
            return {"data": None, "raw": "No LLM API key configured"}

        import httpx

        try:
            messages = [
                {"role": "system", "content": "You are a precise data extraction assistant. Extract structured data as JSON." if format_type == "json" else "You are a helpful summarization assistant."},
                {"role": "user", "content": prompt},
            ]

            resp = httpx.post(
                f"{self.config.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 2000,
                    "temperature": 0.1,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"]

            if format_type == "json":
                # Try to parse JSON from response
                parsed = self._parse_json(raw)
                return {"data": parsed, "raw": raw}
            else:
                return {"data": raw, "raw": raw}

        except Exception as e:
            return {"data": None, "raw": f"LLM error: {str(e)}"}

    def _parse_json(self, text: str) -> Any:
        """Try to parse JSON from LLM response, handling code blocks."""
        # Strip markdown code blocks
        text = text.strip()
        if text.startswith("```"):
            # Find JSON content
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object/array within text
            import re
            for pattern in [r'\{.*\}', r'\[.*\]']:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except:
                        pass
            return {"raw_text": text, "parse_error": "Could not parse JSON from LLM response"}

    def close(self):
        self.scraper.close()
