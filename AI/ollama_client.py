"""Client for Ollama local LLM API (free, no API key needed)."""

import requests


class OllamaClient:
    BASE_URL = "http://localhost:11434"

    def __init__(self, base_url=BASE_URL, timeout=120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_server_running(self):
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self):
        r = requests.get(f"{self.base_url}/api/tags", timeout=10)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    def model_exists(self, model_name):
        return model_name in self.list_models()

    def pull_model(self, model_name, progress_callback=None):
        """Stream the model pull, reporting progress if a callback is provided."""
        try:
            r = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": True},
                stream=True,
                timeout=None,
            )
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                import json

                data = json.loads(line)
                if progress_callback:
                    progress_callback(data)
                if data.get("error"):
                    raise RuntimeError(data["error"])
                if data.get("status") == "success":
                    return True
            return True
        except requests.RequestException as e:
            raise RuntimeError(f"Erreur de connexion Ollama: {e}")

    def delete_model(self, model_name):
        r = requests.delete(
            f"{self.base_url}/api/delete", json={"name": model_name}, timeout=30
        )
        r.raise_for_status()

    def chat(self, model, messages, temperature=0.3, max_tokens=2048, stream=False):
        """Send a chat request, return the assistant reply text."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        r = requests.post(
            f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
        )
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]

    def generate(self, model, prompt, temperature=0.3, max_tokens=2048):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        r = requests.post(
            f"{self.base_url}/api/generate", json=payload, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()["response"]
