import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import requests


SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "ai_settings.json"


@dataclass
class AISettings:
    provider: Optional[str] = None  # "chatgpt" or "gemini"
    api_key: Optional[str] = None


class AIManager:
    """Persist AI configuration and proxy report generation to external APIs."""

    def __init__(self) -> None:
        self.settings = AISettings()
        self._load()

    def _load(self) -> None:
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            self.settings = AISettings(
                provider=data.get("provider"),
                api_key=data.get("api_key"),
            )

    def configure(self, provider: str, api_key: str) -> None:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.settings = AISettings(provider=provider, api_key=api_key)
        SETTINGS_PATH.write_text(
            json.dumps({"provider": provider, "api_key": api_key}, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        self.settings = AISettings()
        if SETTINGS_PATH.exists():
            SETTINGS_PATH.unlink()

    def is_enabled(self) -> bool:
        """Check if AI is enabled. Reloads settings from disk if not already loaded."""
        # If settings are empty, try reloading from disk
        if not self.settings.provider and not self.settings.api_key:
            self._load()
        return bool(self.settings.provider and self.settings.api_key)

    def provider_name(self) -> str:
        mapping = {"chatgpt": "ChatGPT", "gemini": "Gemini"}
        return mapping.get(self.settings.provider or "", "None")

    def validate_api_key(self, provider: str, api_key: str) -> Tuple[bool, str]:
        """Test if the provided API key is valid by making a minimal API call."""
        if not api_key or not api_key.strip():
            return False, "API key cannot be empty."

        if provider == "chatgpt":
            return self._validate_chatgpt_key(api_key)
        if provider == "gemini":
            return self._validate_gemini_key(api_key)
        return False, f"Unknown provider: {provider}"

    def _validate_chatgpt_key(self, api_key: str) -> Tuple[bool, str]:
        """Validate OpenAI API key by listing available models."""
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return True, "ChatGPT API key is valid."
            if response.status_code == 401:
                return False, "Invalid API key. Please check your OpenAI API key."
            return False, f"API validation failed: HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Connection timeout. Please check your internet connection."
        except requests.exceptions.RequestException as exc:
            return False, f"Network error: {exc}"

    def _validate_gemini_key(self, api_key: str) -> Tuple[bool, str]:
        """Validate Gemini API key by making a minimal generateContent call."""
        # First, try to list available models to find one that works
        available_models = self._list_available_models(api_key)
        
        # Build list of endpoints to try
        endpoints = []
        if available_models:
            # Use models that are actually available
            for model in available_models[:2]:  # Try first 2 available models
                endpoints.append(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent")
                endpoints.append(f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent")
        else:
            # Fallback: try common model names
            model_names = ["gemini-pro", "gemini-1.5-flash"]
            api_versions = ["v1beta", "v1"]
            for version in api_versions:
                for model in model_names:
                    endpoints.append(f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent")
        
        params = {"key": api_key}
        payload = {
            "contents": [{"parts": [{"text": "test"}]}],
        }
        
        last_error = None
        for url in endpoints:
            try:
                response = requests.post(url, params=params, json=payload, timeout=10)
                if response.status_code == 200:
                    return True, "Gemini API key is valid."
                # 401/403 means definitely invalid key
                if response.status_code == 401 or response.status_code == 403:
                    error_data = {}
                    try:
                        error_data = response.json() if response.content else {}
                    except:
                        pass
                    error_msg = error_data.get("error", {}).get("message", "Unauthorized")
                    return False, f"Invalid API key: {error_msg}"
                # 400/404 might be model/endpoint issue, but key could still be valid
                # Try next endpoint
                if response.status_code == 400 or response.status_code == 404:
                    error_data = {}
                    try:
                        error_data = response.json() if response.content else {}
                    except:
                        pass
                    error_msg = error_data.get("error", {}).get("message", "Bad request" if response.status_code == 400 else "Not found")
                    error_str = str(error_msg).upper()
                    # Only reject if explicitly says API key is invalid
                    if "API_KEY" in error_str or "INVALID_API_KEY" in error_str:
                        return False, f"Invalid API key: {error_msg}"
                    # Otherwise, might be valid key with model/endpoint issue - try next endpoint
                    last_error = f"Model/endpoint issue (trying alternatives): {error_msg}"
                    continue
                # For other status codes, try next endpoint
                last_error = f"HTTP {response.status_code}"
                continue
            except requests.exceptions.Timeout:
                last_error = "Connection timeout"
                continue
            except requests.exceptions.RequestException as exc:
                last_error = f"Network error: {exc}"
                continue
        
        # If we got here, all endpoints had issues but none were 401/403
        # This likely means the key format is correct but there might be endpoint/model issues
        # Accept it as potentially valid (user can test during actual use)
        if last_error:
            if "timeout" not in str(last_error).lower() and "network" not in str(last_error).lower():
                return True, "Gemini API key format appears valid (endpoint-specific issues may exist, will be tested during actual use)."
            return False, f"Gemini API validation failed: {last_error}. Please verify your API key is correct and has proper permissions."
        return False, "Gemini API validation failed: Unable to connect to any endpoint."

    def generate_analysis(self, tool_name: str, raw_output: str) -> Tuple[bool, str]:
        if not self.is_enabled():
            return False, "AI integration is not configured."

        provider = self.settings.provider
        api_key = self.settings.api_key or ""

        if provider == "chatgpt":
            return self._call_chatgpt(api_key, tool_name, raw_output)
        if provider == "gemini":
            return self._call_gemini(api_key, tool_name, raw_output)
        return False, f"Unsupported AI provider: {provider}"

    def _call_chatgpt(self, api_key: str, tool_name: str, raw_output: str) -> Tuple[bool, str]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        prompt = self._build_prompt(tool_name, raw_output)
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a penetration testing assistant generating detailed reports.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return True, data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as exc:
            return False, f"ChatGPT API error: {exc}"
        except (KeyError, IndexError) as exc:
            return False, f"Unexpected ChatGPT response structure: {exc}"

    def _list_available_models(self, api_key: str) -> List[str]:
        """List available Gemini models for this API key."""
        list_urls = [
            "https://generativelanguage.googleapis.com/v1beta/models",
            "https://generativelanguage.googleapis.com/v1/models",
        ]
        
        for list_url in list_urls:
            try:
                response = requests.get(list_url, params={"key": api_key}, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model in data.get("models", []):
                        name = model.get("name", "")
                        # Extract model name (e.g., "models/gemini-pro" -> "gemini-pro")
                        if "/" in name:
                            model_name = name.split("/")[-1]
                            # Check if it supports generateContent
                            methods = model.get("supportedGenerationMethods", [])
                            if "generateContent" in methods:
                                models.append(model_name)
                    if models:
                        return models
            except:
                continue
        return []

    def _call_gemini(self, api_key: str, tool_name: str, raw_output: str) -> Tuple[bool, str]:
        # First, try to list available models to find one that works
        available_models = self._list_available_models(api_key)
        
        # Build list of endpoints to try
        # Priority: available models from API, then fallback to common names
        endpoints = []
        
        if available_models:
            # Use models that are actually available
            for model in available_models:
                # Try v1beta first, then v1
                endpoints.append(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent")
                endpoints.append(f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent")
        else:
            # Fallback: try common model names with different API versions
            model_names = ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
            api_versions = ["v1beta", "v1"]
            for version in api_versions:
                for model in model_names:
                    endpoints.append(f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent")
        
        params = {"key": api_key}
        prompt = self._build_prompt(tool_name, raw_output)
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                    ]
                }
            ],
        }
        
        last_error = None
        last_response_text = None
        for url in endpoints:
            try:
                response = requests.post(url, params=params, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return True, text
                
                # Get error details for debugging
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    last_response_text = error_msg
                except:
                    last_response_text = response.text[:200] if response.text else f"HTTP {response.status_code}"
                
                # If 400/404, might be model/endpoint issue, try next endpoint
                if response.status_code == 400 or response.status_code == 404:
                    last_error = f"Endpoint '{url.split('/')[-1]}' returned {response.status_code}: {last_response_text}"
                    continue
                # Handle rate limiting (429) - common with free tier
                if response.status_code == 429:
                    error_msg = "Rate limit exceeded. Free tier has usage limits. Please wait a moment and try again."
                    return False, error_msg
                # For other errors, raise to get more details
                response.raise_for_status()
            except requests.RequestException as exc:
                last_error = f"Network/API error for '{url.split('/')[-1]}': {exc}"
                continue
            except (KeyError, IndexError) as exc:
                last_error = f"Unexpected response structure from '{url.split('/')[-1]}': {exc}"
                continue
        
        # Provide detailed error message
        error_msg = f"All Gemini endpoints failed. Last error: {last_error or 'Unknown error'}"
        if last_response_text:
            error_msg += f" | Response: {last_response_text}"
        return False, error_msg

    @staticmethod
    def _build_prompt(tool_name: str, raw_output: str) -> str:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Special handling for report analysis (when analyzing existing reports)
        if tool_name == "Report Analysis":
            return (
                f"Analyze the following security reconnaissance report and provide a comprehensive summary with key insights.\n\n"
                f"Structure your analysis with the following sections:\n"
                f"1. Executive Summary - Brief overview of the report, main findings, and overall risk assessment\n"
                f"2. Key Findings - Most critical discoveries (open ports, services, vulnerabilities, hosts discovered)\n"
                f"3. Technical Insights - Important technical details, service versions, OS information, and network topology\n"
                f"4. Risk Assessment - Prioritized security risks and potential attack vectors identified\n"
                f"5. Actionable Recommendations - Specific next steps for further reconnaissance, exploitation, or remediation\n"
                f"6. Summary Statistics - Quick reference of hosts, ports, services, and vulnerabilities found\n\n"
                f"Format the analysis using Markdown with clear headings, bullet points, tables, and code blocks where appropriate.\n"
                f"Be specific, technical, and actionable. Highlight the most important findings first.\n"
                f"Timestamp: {timestamp}\n\n"
                f"--- REPORT CONTENT START ---\n{raw_output}\n--- REPORT CONTENT END ---"
            )
        
        # Default prompt for scan output analysis
        return (
            f"Analyze the following {tool_name} scan output and create a comprehensive, well-organized red-team reconnaissance report.\n\n"
            f"Structure the report with the following sections in order:\n"
            f"1. Executive Summary - Brief overview of findings and risk level\n"
            f"2. Scan Overview - Target information, scan type, and methodology\n"
            f"3. Key Findings - Most critical discoveries (open ports, services, vulnerabilities)\n"
            f"4. Detailed Technical Analysis - Port-by-port analysis, service versions, OS detection results\n"
            f"5. Risk Assessment - Prioritized risks and potential attack vectors\n"
            f"6. Recommendations - Suggested next steps for further reconnaissance or exploitation\n"
            f"7. Appendix - Raw scan data reference\n\n"
            f"Format the report using Markdown with clear headings, bullet points, and code blocks where appropriate.\n"
            f"Be specific, technical, and actionable. Organize findings by priority (Critical, High, Medium, Low).\n"
            f"Timestamp: {timestamp}\n\n"
            f"--- RAW {tool_name.upper()} OUTPUT START ---\n{raw_output}\n--- RAW {tool_name.upper()} OUTPUT END ---"
        )


