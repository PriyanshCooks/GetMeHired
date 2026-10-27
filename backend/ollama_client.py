import json
import re
import httpx
from typing import Dict, Any, List, Optional
from backend.config import load_settings

class OllamaClient:
    def __init__(self):
        settings = load_settings()
        self.base_url = settings.get("ollama_base_url", "http://localhost:11434").rstrip("/")
        self.model = settings.get("ollama_model", "qwen3.5:4b")
        self.temperature = settings.get("llm_temperature", 0.3)
        self.timeout = 600.0  # 10 min true safety net — LLM runs in background thread, time is not a constraint

    def is_available(self) -> Dict[str, Any]:
        """Check if Ollama server is running and get model list."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    return {
                        "online": True,
                        "current_model": self.model,
                        "available_models": models,
                        "is_current_model_installed": self.model in models or any(self.model in m for m in models)
                    }
        except Exception as e:
            return {
                "online": False,
                "error": str(e),
                "current_model": self.model,
                "available_models": []
            }
        return {"online": False, "available_models": []}

    def generate(self, prompt: str, system: Optional[str] = None, json_format: bool = False) -> str:
        """Call Ollama generate endpoint."""
        settings = load_settings()
        model = settings.get("ollama_model", self.model)
        base_url = settings.get("ollama_base_url", self.base_url).rstrip("/")
        
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": 2048,        # Reduced context: 2x faster per-token generation
                "num_predict": 400,     # Enough for structured JSON output from micro calls
            }
        }
        if system:
            payload["system"] = system
        if json_format:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{base_url}/api/generate", json=payload)
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
                else:
                    print(f"Ollama returned status {res.status_code}: {res.text}")
                    return ""
        except Exception as e:
            print(f"Ollama call failed ({e}). Attempting fallback heuristics if available.")
            return ""

    def generate_json(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        """Generate and parse structured JSON response."""
        raw = self.generate(prompt=prompt, system=system, json_format=True)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            # Fallback regex search for JSON block
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {}

ollama_client = OllamaClient()
