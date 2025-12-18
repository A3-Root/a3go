"""
Multi-provider LLM clients

All clients expose:
- generate_tactical_orders(world_state, mission_intent, objectives, system_prompt) -> dict|None
- test_connection() -> (ok: bool, message: str)
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("batcom.ai.providers")


def _format_prompt(system_prompt: str, world_state: Dict[str, Any], mission_intent: str, objectives: List[Dict[str, Any]]) -> str:
    return "\n\n".join([
        system_prompt,
        "MISSION INTENT:",
        mission_intent or "N/A",
        "OBJECTIVES:",
        json.dumps(objectives, indent=2),
        "WORLD STATE:",
        json.dumps(world_state, indent=2)
    ])


class BaseLLMClient:
    def generate_tactical_orders(self, world_state: Dict[str, Any], mission_intent: str, objectives: List[Dict[str, Any]], system_prompt: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def test_connection(self) -> (bool, str): # type: ignore
        raise NotImplementedError


class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, timeout: int = 30, endpoint: Optional[str] = None, max_output_tokens: int = 65536, thinking_config: Optional[Dict[str, Any]] = None):
        from google import genai
        from google.genai import types
        import datetime

        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.types = types
        self.datetime = datetime

        # Native Gemini context caching for system prompt
        self._cached_content = None  # Gemini CachedContent object
        self._cached_system_prompt_text = None  # Track what we cached
        self._cache_expiry = None  # When the cache expires

        # Thinking/reasoning configuration
        self.thinking_config = thinking_config or {}
        self.thinking_enabled = self.thinking_config.get('thinking_enabled', False)
        self.thinking_mode = self.thinking_config.get('thinking_mode', 'native_sdk')

        # Only pass base_url if a custom endpoint is explicitly provided
        # The native Google GenAI SDK works best without base_url for default endpoint
        if endpoint and endpoint.strip():
            # Custom endpoint provided - use it
            try:
                self.client = genai.Client(api_key=api_key, base_url=endpoint)
                logger.info("Gemini client initialized with custom endpoint: %s", endpoint)
            except TypeError:
                logger.warning("Gemini client does not support base_url param, using default endpoint")
                self.client = genai.Client(api_key=api_key)
        else:
            # No endpoint or empty string - use default Google endpoint
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized with default Google endpoint (max_output_tokens: %d, NATIVE caching enabled, thinking: %s)",
                        max_output_tokens, "enabled" if self.thinking_enabled else "disabled")

        # Validate thinking support
        if self.thinking_enabled:
            self._validate_thinking_support()

    def __del__(self):
        """Cleanup: delete Gemini cache when client is destroyed"""
        if self._cached_content:
            try:
                self.client.caches.delete(name=self._cached_content.name)
                logger.info("Cleaned up Gemini cache: %s", self._cached_content.name)
            except Exception as e:
                logger.debug("Failed to cleanup Gemini cache (may already be deleted): %s", e)

    def list_caches(self):
        """List all Gemini caches for debugging"""
        try:
            caches = list(self.client.caches.list())
            logger.info("=" * 80)
            logger.info("GEMINI CACHE LIST (%d total)", len(caches))
            logger.info("=" * 80)
            for cache in caches:
                logger.info("Cache: %s", cache.name)
                logger.info("  Display name: %s", getattr(cache, 'display_name', 'N/A'))
                logger.info("  Model: %s", getattr(cache, 'model', 'N/A'))
                logger.info("  Created: %s", getattr(cache, 'create_time', 'N/A'))
                logger.info("  Expires: %s", getattr(cache, 'expire_time', 'N/A'))
                if hasattr(cache, 'usage_metadata'):
                    logger.info("  Usage: %s", cache.usage_metadata)
                logger.info("-" * 40)
            logger.info("=" * 80)
            return caches
        except Exception as e:
            logger.error("Failed to list caches: %s", e)
            return []

    def delete_all_caches(self):
        """Delete all Gemini caches (useful for cleanup/debugging)"""
        try:
            caches = list(self.client.caches.list())
            logger.info("Deleting %d Gemini caches...", len(caches))
            for cache in caches:
                try:
                    self.client.caches.delete(name=cache.name)
                    logger.info("Deleted cache: %s", cache.name)
                except Exception as e:
                    logger.warning("Failed to delete cache %s: %s", cache.name, e)
            logger.info("Cache cleanup complete")
        except Exception as e:
            logger.error("Failed to list/delete caches: %s", e)

    def _validate_thinking_support(self):
        """Validate that the model supports thinking/reasoning"""
        thinking_models = ['2.5', '2.0', 'gemini-2', 'gemini-3']
        supports_thinking = any(v in self.model for v in thinking_models)

        if not supports_thinking:
            logger.warning("Model '%s' may not support thinking - verify model name includes version (e.g., gemini-2.5-flash)", self.model)
            logger.warning("Thinking-capable models: gemini-2.0-*, gemini-2.5-*, gemini-3-*")
        else:
            logger.info("Thinking enabled for model: %s (mode: %s)", self.model, self.thinking_mode)

    def _build_thinking_config(self):
        """Build ThinkingConfig for native SDK mode"""
        if not self.thinking_enabled or self.thinking_mode != "native_sdk":
            return None

        # Determine Gemini version and use appropriate parameter
        if "gemini-3" in self.model.lower():
            # Gemini 3: use thinking_level
            level = self.thinking_config.get('thinking_level', 'high')
            logger.info("Native SDK (Gemini 3): thinking_level='%s'", level)
            return self.types.ThinkingConfig(
                thinking_level=level,
                include_thoughts=self.thinking_config.get('include_thoughts', True)
            )
        else:
            # Gemini 2.5/2.0: use thinking_budget
            budget = self.thinking_config.get('thinking_budget', -1)
            budget_str = "dynamic" if budget == -1 else ("disabled" if budget == 0 else f"{budget} tokens")
            logger.info("Native SDK (Gemini 2.5): thinking_budget=%s", budget_str)
            return self.types.ThinkingConfig(
                thinking_budget=budget,
                include_thoughts=self.thinking_config.get('include_thoughts', True)
            )

    def _extract_thoughts(self, response):
        """
        Extract thought summaries from response.candidates[0].content.parts

        Returns:
            tuple: (thought_summary: str, final_answer: str)
        """
        thoughts = []
        answers = []

        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if not hasattr(part, 'text') or not part.text:
                            continue

                        # part.thought == True indicates this is a thinking summary
                        if hasattr(part, 'thought') and part.thought:
                            thoughts.append(part.text)
                        else:
                            answers.append(part.text)

        return "\n".join(thoughts), "\n".join(answers)

    def generate_tactical_orders(self, world_state, mission_intent, objectives, cached_context):
        """
        Generate tactical orders using Gemini with context caching.

        Args:
            world_state: Current world state (DYNAMIC - sent every call)
            mission_intent: Mission description (DYNAMIC)
            objectives: Mission objectives (for backward compatibility, not used directly)
            cached_context: System prompt + objectives + order history (CACHED)

        The cached_context includes:
        - Static system prompt with tactical guidelines
        - Current mission objectives (slow-changing)
        - Order history (what the LLM has done so far)

        This context gets cached by Gemini and reused until it changes.
        """
        import hashlib
        from datetime import datetime, timezone, timedelta

        # Format user prompt - ONLY dynamic content (world state)
        # The cached_context (system prompt + objectives + history) is cached separately
        user_prompt = f"**CURRENT SITUATION (T+{world_state.get('mission_time', 0)}s)**\n\nMISSION INTENT: {mission_intent or 'N/A'}\n\nWORLD STATE:\n{json.dumps(world_state, indent=2)}"

        # Check if we need to create/update the cache
        # Cache invalidation happens when:
        # 1. cached_context changes (objectives/history changed)
        # 2. Cache expires (1 hour TTL)
        cache_needs_update = False
        cache_expired = False

        if self._cached_system_prompt_text != cached_context:
            cache_needs_update = True
            logger.info("=" * 80)
            logger.info("GEMINI CACHED CONTEXT CHANGED - Creating new cache")
            logger.info("Cached context: %d chars (system prompt + objectives + history)", len(cached_context))
            logger.info("This context will be reused until objectives change or cache expires")
            logger.info("=" * 80)
        elif self._cache_expiry and datetime.now(timezone.utc) >= self._cache_expiry:
            cache_expired = True
            cache_needs_update = True
            logger.info("=" * 80)
            logger.info("GEMINI CACHE EXPIRED - Refreshing cache with current context")
            logger.info("=" * 80)

        # Create or update Gemini native cache
        if cache_needs_update:
            try:
                # Delete old cache if it exists
                if self._cached_content:
                    try:
                        self.client.caches.delete(name=self._cached_content.name)
                        logger.info("Deleted old Gemini cache: %s", self._cached_content.name)
                    except Exception as e:
                        logger.warning("Failed to delete old cache (may not exist): %s", e)

                # Create new cache with 1 hour TTL
                # Note: Gemini caching reduces costs by 90% for cached tokens
                # cached_context includes: system prompt + objectives + order history
                # According to Google's docs, cached content goes in system_instruction
                # and must be accessed via cached_content parameter in generate_content
                cache_config = self.types.CreateCachedContentConfig(
                    display_name=f'batcom_tactical_{int(datetime.now(timezone.utc).timestamp())}',
                    system_instruction=cached_context,  # System instruction IS cacheable
                    ttl="3600s"  # Cache for 1 hour (3600 seconds)
                )

                # Model is passed as separate argument to create(), not in config
                self._cached_content = self.client.caches.create(
                    model=self.model,
                    config=cache_config
                )
                self._cached_system_prompt_text = cached_context
                self._cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

                logger.info("=" * 80)
                logger.info("GEMINI NATIVE CACHE CREATED")
                logger.info("Cache name: %s", self._cached_content.name)
                logger.info("Cache expires: %s", self._cache_expiry.isoformat())
                logger.info("Cached content: ~%d chars", len(cached_context))
                logger.info("  - System prompt (tactical guidelines)")
                logger.info("  - Current mission objectives")
                logger.info("  - Order history (last 5 cycles)")
                logger.info("Estimated cached tokens: ~%d", len(cached_context) // 4)
                logger.info("This cache will be reused until objectives change or 1 hour expires")
                logger.info("=" * 80)

            except Exception as e:
                logger.error("=" * 80)
                logger.error("FAILED TO CREATE GEMINI CACHE")
                logger.error("Error: %s", str(e))
                logger.error("Model: %s", self.model)
                logger.error("IMPORTANT: Ensure model name is valid and supports context caching (e.g., 'gemini-2.5-flash-lite')")
                logger.error("Falling back to non-cached mode (full tokens charged each request)")
                logger.error("=" * 80)
                self._cached_content = None
        else:
            logger.info("GEMINI REQUEST (using NATIVE cached system prompt from: %s)",
                       self._cached_content.name if self._cached_content else "N/A")
            logger.info("Cache remains valid until: %s",
                       self._cache_expiry.isoformat() if self._cache_expiry else "N/A")

        # LOG REQUEST (only user prompt)
        logger.info("-" * 80)
        logger.info("USER PROMPT:\n%s", user_prompt)
        logger.info("=" * 80)

        # Build config params (shared for both cached and non-cached)
        config_params = {
            'temperature': 0.4,
            'max_output_tokens': self.max_output_tokens
        }

        # Add thinking config if enabled
        if self.thinking_enabled:
            thinking_cfg = self._build_thinking_config()
            if thinking_cfg:
                config_params['thinking_config'] = thinking_cfg

        # Generate content using cache if available
        try:
            if self._cached_content:
                # Use cached content by passing the cache name
                # The cached system instruction is automatically applied
                config_params['cached_content'] = self._cached_content.name
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=self.types.GenerateContentConfig(**config_params)
                )
                logger.info("Used Gemini NATIVE cache: %s", self._cached_content.name)
            else:
                # Fallback: no cache, use system_instruction directly
                config_params['system_instruction'] = cached_context
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=self.types.GenerateContentConfig(**config_params)
                )
                logger.info("Used Gemini WITHOUT cache (fallback mode)")
        except Exception as e:
            logger.error("=" * 80)
            logger.error("GEMINI API CALL FAILED")
            logger.error("Error: %s", str(e))
            logger.error("Error type: %s", type(e).__name__)

            # If cache-based call failed, try without cache
            if self._cached_content:
                logger.warning("Cache reference may be invalid. Retrying without cache...")
                logger.warning("Deleting invalid cache...")
                try:
                    self.client.caches.delete(name=self._cached_content.name)
                except Exception as del_err:
                    logger.debug("Failed to delete invalid cache: %s", del_err)

                self._cached_content = None
                self._cached_system_prompt_text = None
                self._cache_expiry = None

                logger.warning("Retrying API call in non-cached mode...")
                try:
                    # Build retry config with thinking (if enabled)
                    retry_config_params = {
                        'temperature': 0.4,
                        'max_output_tokens': self.max_output_tokens,
                        'system_instruction': cached_context
                    }
                    if self.thinking_enabled:
                        thinking_cfg = self._build_thinking_config()
                        if thinking_cfg:
                            retry_config_params['thinking_config'] = thinking_cfg

                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=user_prompt,
                        config=self.types.GenerateContentConfig(**retry_config_params)
                    )
                    logger.info("Retry succeeded without cache")
                except Exception as retry_err:
                    logger.error("Retry also failed: %s", retry_err)
                    logger.error("=" * 80)
                    raise
            else:
                logger.error("No cache was used, cannot retry")
                logger.error("=" * 80)
                raise

        # Extract thoughts if thinking is enabled
        thought_summary = ""
        if self.thinking_enabled and self.thinking_config.get('include_thoughts', True):
            thought_summary, answer_text = self._extract_thoughts(response)

            if thought_summary:
                logger.info("=" * 80)
                logger.info("GEMINI THOUGHT SUMMARY (%d chars):", len(thought_summary))
                logger.info("-" * 80)
                logger.info(thought_summary)
                logger.info("=" * 80)

            # Use extracted answer if available, otherwise fall back to response.text
            text = answer_text or response.text or ""
        else:
            # No thinking or thoughts not requested - use standard response.text
            text = response.text or ""

        # LOG RAW RESPONSE FIRST for debugging
        logger.info("=" * 80)
        logger.info("GEMINI RAW RESPONSE (full, %d chars):", len(text))
        logger.info("-" * 80)
        logger.info(text)
        logger.info("=" * 80)

        # Extract token usage if available (including cache metrics and thinking tokens)
        token_usage = {}
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            token_usage = {
                'input_tokens': getattr(usage, 'prompt_token_count', 0) or 0,
                'output_tokens': getattr(usage, 'candidates_token_count', 0) or 0,
                'total_tokens': getattr(usage, 'total_token_count', 0) or 0,
                'cached_tokens': getattr(usage, 'cached_content_token_count', 0) or 0,
                'thinking_tokens': getattr(usage, 'thoughts_token_count', 0) or 0
            }

            if token_usage['cached_tokens'] > 0 or token_usage['thinking_tokens'] > 0:
                logger.info("=" * 80)
                logger.info("GEMINI TOKEN USAGE (CACHE + THINKING):")
                logger.info("  Input tokens: %d", token_usage['input_tokens'])
                logger.info("  Cached tokens: %d (90%% cost reduction!)", token_usage['cached_tokens'])
                if token_usage['thinking_tokens'] > 0:
                    logger.info("  Thinking tokens: %d (charged as output)", token_usage['thinking_tokens'])
                logger.info("  Output tokens: %d", token_usage['output_tokens'])
                logger.info("  Total tokens: %d", token_usage['total_tokens'])
                if token_usage['thinking_tokens'] > 0:
                    effective_output = token_usage['thinking_tokens'] + token_usage['output_tokens']
                    logger.info("  Effective output cost: %d tokens (thinking + output)", effective_output)
                logger.info("  Cache savings: ~%d tokens not charged at full rate", token_usage['cached_tokens'])
                logger.info("=" * 80)
            else:
                logger.info("Gemini token usage: %d input, %d output, %d total (no cache/thinking used)",
                           token_usage['input_tokens'], token_usage['output_tokens'], token_usage['total_tokens'])

        # Try to parse JSON from response
        try:
            # Method 1: Try to extract JSON from markdown code blocks (```json ... ```)
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                logger.debug("Extracted JSON from markdown code block")
            else:
                # Method 2: Look for JSON object boundaries
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    json_str = text[start:end + 1]
                    logger.debug("Extracted JSON from character positions %d to %d", start, end)
                else:
                    logger.error("No JSON object found in response (no { } brackets)")
                    logger.error("Response text: %s", text[:200])
                    return None

            # Parse the extracted JSON
            parsed = json.loads(json_str)
            logger.info("Successfully parsed JSON response")

            # Validate required fields
            if 'orders' not in parsed:
                logger.error("Parsed JSON missing 'orders' field. Keys: %s", list(parsed.keys()))
                return None

            if not isinstance(parsed['orders'], list):
                logger.error("'orders' field is not a list, got: %s", type(parsed['orders']))
                return None

            # Add metadata
            parsed["__raw_text"] = text
            parsed["__token_usage"] = token_usage
            parsed["__thought_summary"] = thought_summary

            logger.info("Parsed %d orders from Gemini response", len(parsed.get('orders', [])))
            return parsed

        except json.JSONDecodeError as e:
            logger.error("JSON parsing failed: %s", e)
            logger.error("Attempted to parse: %s...", json_str[:200] if 'json_str' in locals() else "N/A")
            return None
        except Exception as e:
            logger.error("Unexpected error parsing Gemini response: %s", e, exc_info=True)
            return None

    def test_connection(self):
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents="Briefly confirm connectivity."
            )
            greeting = (resp.text or "").strip()
            return True, greeting or "Gemini responded"
        except Exception as e:
            return False, str(e)


class GeminiOpenAICompatClient(object):  # Will inherit from OpenAILLMClient defined below
    """
    Gemini via OpenAI compatibility endpoint
    Supports reasoning_effort for thinking
    """

    def __init__(self, api_key: str, model: str, timeout: int = 30, max_output_tokens: int = 65536, thinking_config: Optional[Dict[str, Any]] = None):
        # Import OpenAI client
        from openai import OpenAI

        # Use Gemini's OpenAI-compatible endpoint
        endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/"
        self.client = OpenAI(api_key=api_key, base_url=endpoint, timeout=timeout)
        self.model = model
        self.max_output_tokens = max_output_tokens

        # Thinking configuration
        self.thinking_config = thinking_config or {}
        self.thinking_enabled = self.thinking_config.get('thinking_enabled', False)

        logger.info("Gemini OpenAI-compat initialized (thinking: %s, endpoint: %s)",
                    "enabled" if self.thinking_enabled else "disabled", endpoint)

    def generate_tactical_orders(self, world_state, mission_intent, objectives, cached_context):
        """Generate tactical orders using OpenAI compatibility mode with reasoning_effort"""
        import json
        import hashlib

        # Simple caching for system prompt (client-side hashing, not Gemini cache)
        current_hash = hashlib.md5(cached_context.encode()).hexdigest()
        if not hasattr(self, '_cached_system_prompt_hash'):
            self._cached_system_prompt_hash = None

        context_changed = (self._cached_system_prompt_hash != current_hash)
        if context_changed:
            self._cached_system_prompt_hash = current_hash
            logger.info("OpenAI-compat: System prompt updated (hash: %s...)", current_hash[:8])

        # Format user prompt
        user_prompt = f"**CURRENT SITUATION (T+{world_state.get('mission_time', 0)}s)**\n\nMISSION INTENT: {mission_intent or 'N/A'}\n\nWORLD STATE:\n{json.dumps(world_state, indent=2)}"

        # Build messages
        messages = [
            {"role": "system", "content": cached_context},
            {"role": "user", "content": user_prompt}
        ]

        # Build request params
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": self.max_output_tokens
        }

        # Add reasoning_effort if thinking enabled
        if self.thinking_enabled:
            effort = self.thinking_config.get('reasoning_effort', 'medium')
            params['reasoning_effort'] = effort
            logger.info("OpenAI-compat: reasoning_effort='%s'", effort)

        # Make API call
        try:
            resp = self.client.chat.completions.create(**params)
            content = resp.choices[0].message.content or ""

            # Extract tokens including thinking
            token_usage = {}
            if hasattr(resp, 'usage') and resp.usage:
                token_usage = {
                    'input_tokens': getattr(resp.usage, 'prompt_tokens', 0),
                    'output_tokens': getattr(resp.usage, 'completion_tokens', 0),
                    'total_tokens': getattr(resp.usage, 'total_tokens', 0),
                    'thinking_tokens': getattr(resp.usage, 'thoughts_token_count', 0)
                }

                if token_usage['thinking_tokens'] > 0:
                    logger.info("OpenAI-compat thinking tokens: %d", token_usage['thinking_tokens'])

            # Parse JSON
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    json_str = content[start:end + 1]
                else:
                    logger.error("No JSON found in OpenAI-compat response")
                    return None

            parsed = json.loads(json_str)
            parsed["__raw_text"] = content
            parsed["__token_usage"] = token_usage
            return parsed

        except Exception as e:
            logger.error("OpenAI-compat API call failed: %s", e)
            return None

    def test_connection(self):
        """Test the OpenAI-compat connection"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            return True, "Gemini OpenAI-compat responded"
        except Exception as e:
            return False, str(e)


class OpenAILLMClient(BaseLLMClient):
    """
    OpenAI client using the Responses API with native prompt caching.
    - Without caching: 25k input tokens charged at full rate
    - With caching: ~90% of static content (system prompt + history) cached at 50% discount
    """

    # Models with restricted parameters (require max_output_tokens instead of max_tokens)
    # These are reasoning models that also need longer timeouts
    RESTRICTED_PARAM_MODELS = ('gpt-5', 'o1', 'o3', 'o4')
    # Timeout for reasoning models (they can take much longer due to internal reasoning)
    REASONING_MODEL_TIMEOUT = 300  # 5 minutes

    def __init__(self, api_key: str, model: str, endpoint: Optional[str] = None, timeout: int = 30, max_output_tokens: int = 4096, use_responses_api: bool = True):
        """
        Initialize OpenAI client with Responses API support.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., 'gpt-5', 'gpt-5.1', 'gpt-5-mini', 'gpt-5-nano')
            endpoint: Custom endpoint URL (optional)
            timeout: Request timeout in seconds
            max_output_tokens: Maximum output tokens
            use_responses_api: If True, use Responses API with native caching (default: True)
        """
        from openai import OpenAI
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.use_responses_api = use_responses_api

        # Cache management for system prompt
        self._cached_system_prompt = None
        self._cached_system_prompt_hash = None
        self._prompt_cache_key = None  # Used for OpenAI's native prompt caching
        self._skip_cache_retention = False  # Flag to skip prompt_cache_retention if not supported

        # Determine if model has restricted parameters (gpt-5, o1, o3, o4)
        # These are reasoning models: require max_output_tokens instead of max_tokens, no custom temperature, longer timeout
        self._is_restricted_model = any(m in model.lower() for m in self.RESTRICTED_PARAM_MODELS)

        # Use longer timeout for reasoning models (they can take minutes to respond)
        effective_timeout = self.REASONING_MODEL_TIMEOUT if self._is_restricted_model else timeout
        kwargs = {"api_key": api_key, "timeout": effective_timeout}
        if endpoint:
            kwargs["base_url"] = endpoint
        self.client = OpenAI(**kwargs)

        logger.info("OpenAI client initialized (API: %s, restricted_params: %s, timeout: %ds)",
                   "Responses" if use_responses_api else "Chat Completions",
                   self._is_restricted_model, effective_timeout)

    def generate_tactical_orders(self, world_state, mission_intent, objectives, cached_context):
        """
        Generate tactical orders using OpenAI with native prompt caching.

        Uses Responses API for automatic caching of system prompt + objectives.
        The cached_context (system prompt + objectives) is cached by OpenAI,
        while world_state and order_summaries are sent fresh each time.

        NOTE: Order history/summaries should NOT be in cached_context because they change
        every call and would invalidate the cache. They should be in world_state instead.
        """
        import hashlib

        # Check if cached context changed (objectives changed)
        # NOTE: Only objectives should change here, NOT order history
        current_hash = hashlib.md5(cached_context.encode()).hexdigest()
        context_changed = (self._cached_system_prompt_hash != current_hash)

        if context_changed:
            self._cached_system_prompt = cached_context
            self._cached_system_prompt_hash = current_hash
            # Update prompt_cache_key for OpenAI's native caching
            self._prompt_cache_key = f"batcom_tactical_{current_hash[:16]}"

            logger.info("=" * 80)
            logger.info("OPENAI CACHED CONTEXT CHANGED (objectives updated)")
            logger.info("Cached context: %d chars", len(cached_context))
            logger.info("Cache key: %s", self._prompt_cache_key)
            logger.info("Stateless mode: context accumulation prevented")
            logger.info("=" * 80)
        else:
            logger.info("=" * 80)
            logger.info("OPENAI CACHE REUSED (objectives unchanged)")
            logger.info("Cache key: %s", self._prompt_cache_key)
            logger.info("Cached content: %d chars (system prompt + objectives)", len(cached_context))
            logger.info("=" * 80)

        # Format user prompt - dynamic world state + order history
        # Order summaries are embedded in world_state dict by commander.py
        user_prompt = f"**CURRENT SITUATION (T+{world_state.get('mission_time', 0)}s)**\n\nMISSION INTENT: {mission_intent or 'N/A'}\n\nWORLD STATE:\n{json.dumps(world_state, indent=2)}"

        logger.info("OPENAI REQUEST (cached context: %d chars, fresh prompt: %d chars)",
                   len(cached_context), len(user_prompt))
        logger.info("-" * 80)
        logger.info("USER PROMPT (DYNAMIC):\n%s", user_prompt)
        logger.info("=" * 80)

        # Use Responses API if enabled, otherwise fall back to Chat Completions
        if self.use_responses_api:
            try:
                return self._generate_with_responses_api(cached_context, user_prompt)
            except Exception as e:
                error_str = str(e)
                logger.error("Responses API failed: %s", e)

                # Check if it's a prompt_cache_retention error
                if "prompt_cache_retention" in error_str and "not supported" in error_str:
                    logger.warning("Model %s does not support prompt_cache_retention parameter", self.model)
                    logger.warning("Retrying without prompt_cache_retention...")
                    # Mark to skip cache retention parameter in future calls
                    self._skip_cache_retention = True
                    try:
                        return self._generate_with_responses_api(cached_context, user_prompt)
                    except Exception as retry_e:
                        logger.error("Retry without prompt_cache_retention also failed: %s", retry_e)
                        logger.warning("Falling back to Chat Completions API...")
                else:
                    logger.warning("Falling back to Chat Completions API...")
                # Fall through to Chat Completions fallback

        # Fallback: Use Chat Completions API (no native caching)
        return self._generate_with_chat_completions(cached_context, user_prompt)

    def _generate_with_responses_api(self, cached_context, user_prompt):
        """
        Generate using Responses API with native prompt caching.

        The Responses API provides:
        - Automatic caching of instructions via prompt_cache_key
        - 24h cache retention with prompt_cache_retention="24h" (if supported)

        IMPORTANT: We do NOT use previous_response_id to avoid context accumulation.
        Instead, we pass order summaries explicitly in the world_state dict for context continuity.
        This ensures the context window only contains:
        - System prompt (~2k tokens) - CACHED
        - Current objectives (~500 tokens) - CACHED
        - Current world state (~15k tokens) - FRESH
        - Last 5 order summaries (~500 tokens) - FRESH
        Total: ~18k tokens per call (not 400k from accumulated conversation history)
        """
        # Build request params for Responses API
        request_params = {
            "model": self.model,
            "instructions": cached_context,  # System prompt (will be cached)
            "input": user_prompt,  # Dynamic user input (not cached)
            "prompt_cache_key": self._prompt_cache_key,  # Enable native caching
            "store": False,  # DO NOT store conversation history (prevents context accumulation)
        }

        # Add prompt_cache_retention if supported by model
        # Some models (like gpt-5-mini) may not support this parameter
        # If it fails, we'll retry without it in the except block
        if not hasattr(self, '_skip_cache_retention'):
            request_params["prompt_cache_retention"] = "24h"  # Extended caching (up to 24 hours)

        # DO NOT add previous_response_id - we want stateless calls to prevent context accumulation
        # Context continuity is maintained via order_summaries in world_state instead
        logger.info("Stateless API call (no previous_response_id to prevent context accumulation)")

        # Handle max_output_tokens vs max_tokens based on model type
        if self._is_restricted_model:
            # gpt-5, gpt-5-mini, o1, o3, o4: use max_output_tokens
            request_params["max_output_tokens"] = self.max_output_tokens
        else:
            # Standard models: use max_output_tokens (Responses API naming)
            request_params["max_output_tokens"] = self.max_output_tokens
            request_params["temperature"] = 0.4

        # Make API call to Responses endpoint
        logger.info("Calling Responses API (cache_key: %s, stateless mode)",
                   self._prompt_cache_key)

        resp = self.client.responses.create(**request_params)

        # DO NOT store response ID - we want stateless calls
        # (response ID would accumulate conversation history and bloat context window)

        # Extract content from response
        content = ""
        if hasattr(resp, 'output') and resp.output:
            for item in resp.output:
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                content += content_item.text or ""

        # LOG RAW RESPONSE FIRST for debugging
        logger.info("=" * 80)
        logger.info("OPENAI RESPONSES API RAW RESPONSE (full, %d chars):", len(content))
        logger.info("-" * 80)
        logger.info(content)
        logger.info("=" * 80)

        # Extract token usage (including cached tokens!)
        token_usage = {}
        if hasattr(resp, 'usage') and resp.usage:
            input_tokens = getattr(resp.usage, 'input_tokens', 0)
            cached_tokens = 0
            if hasattr(resp.usage, 'input_tokens_details'):
                cached_tokens = getattr(resp.usage.input_tokens_details, 'cached_tokens', 0)

            token_usage = {
                'input_tokens': input_tokens,
                'cached_tokens': cached_tokens,
                'output_tokens': getattr(resp.usage, 'output_tokens', 0),
                'total_tokens': getattr(resp.usage, 'total_tokens', 0)
            }

            # Log cache hit metrics
            if cached_tokens > 0:
                cache_hit_rate = (cached_tokens / input_tokens * 100) if input_tokens > 0 else 0
                logger.info("=" * 80)
                logger.info("OPENAI PROMPT CACHE HIT!")
                logger.info("  Input tokens: %d", input_tokens)
                logger.info("  Cached tokens: %d (%.1f%% cache hit rate)", cached_tokens, cache_hit_rate)
                logger.info("  Output tokens: %d", token_usage['output_tokens'])
                logger.info("  Total tokens: %d", token_usage['total_tokens'])
                logger.info("  Estimated savings: ~%.1f%% on cached tokens", 50.0)  # OpenAI caches at 50% discount
                logger.info("=" * 80)
            else:
                logger.info("OpenAI token usage: %d input, %d output, %d total (no cache hit)",
                           input_tokens, token_usage['output_tokens'], token_usage['total_tokens'])

        return self._parse_response(content, token_usage)

    def _generate_with_chat_completions(self, cached_context, user_prompt):
        """
        Fallback: Generate using Chat Completions API (no native caching).
        """
        # Build request params - restricted models (gpt-5, o1, o3, o4) need different params
        request_params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": cached_context},
                {"role": "user", "content": user_prompt}
            ]
        }
        if self._is_restricted_model:
            # Restricted models: use max_completion_tokens, no custom temperature
            request_params["max_completion_tokens"] = self.max_output_tokens
        else:
            # Standard models: use max_tokens and temperature
            request_params["max_tokens"] = self.max_output_tokens
            request_params["temperature"] = 0.4

        resp = self.client.chat.completions.create(**request_params)
        content = resp.choices[0].message.content or ""

        # LOG RAW RESPONSE FIRST for debugging
        logger.info("=" * 80)
        logger.info("OPENAI CHAT COMPLETIONS RAW RESPONSE (full, %d chars):", len(content))
        logger.info("-" * 80)
        logger.info(content)
        logger.info("=" * 80)

        # Extract token usage
        token_usage = {}
        if hasattr(resp, 'usage') and resp.usage:
            token_usage = {
                'input_tokens': getattr(resp.usage, 'prompt_tokens', 0),
                'output_tokens': getattr(resp.usage, 'completion_tokens', 0),
                'total_tokens': getattr(resp.usage, 'total_tokens', 0),
                'cached_tokens': 0  # Chat Completions doesn't support native caching
            }
            logger.info("OpenAI token usage: %d input, %d output, %d total",
                       token_usage['input_tokens'], token_usage['output_tokens'], token_usage['total_tokens'])

        return self._parse_response(content, token_usage)

    def _parse_response(self, content, token_usage):
        """Parse JSON response and add metadata."""
        try:
            parsed = json.loads(content)
            parsed["__raw_text"] = content
            parsed["__token_usage"] = token_usage
            logger.info("Successfully parsed OpenAI JSON response with %d orders", len(parsed.get('orders', [])))
            return parsed
        except json.JSONDecodeError as e:
            logger.error("OpenAI JSON parsing failed: %s", e)
            logger.error("Response content: %s...", content[:200])
            return None
        except Exception as e:
            logger.error("OpenAI unexpected parsing error: %s", e, exc_info=True)
            return None

    def test_connection(self):
        try:
            if self.use_responses_api:
                # Test Responses API
                resp = self.client.responses.create(
                    model=self.model,
                    input="Hello, confirm connectivity.",
                    max_output_tokens=20
                )
                # Extract text from response
                text = ""
                if hasattr(resp, 'output') and resp.output:
                    for item in resp.output:
                        if hasattr(item, 'type') and item.type == 'message':
                            if hasattr(item, 'content') and item.content:
                                for content_item in item.content:
                                    if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                        text += content_item.text or ""
                return True, text.strip() or "Responses API connected"
            else:
                # Test Chat Completions API
                request_params = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Hello, confirm connectivity."}]
                }
                if self._is_restricted_model:
                    request_params["max_completion_tokens"] = 20
                else:
                    request_params["max_tokens"] = 20

                resp = self.client.chat.completions.create(**request_params)
                text = resp.choices[0].message.content or ""
                return True, text.strip()
        except Exception as e:
            return False, str(e)


class AnthropicLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, endpoint: Optional[str] = None, timeout: int = 30, max_output_tokens: int = 4096):
        import anthropic
        kwargs = {"api_key": api_key, "timeout": timeout}
        if endpoint:
            kwargs["base_url"] = endpoint
        self.client = anthropic.Anthropic(**kwargs)
        self.model = model
        self.max_output_tokens = max_output_tokens
        # Cache management for system prompt
        self._cached_system_prompt = None
        self._cached_system_prompt_hash = None
        logger.info("Anthropic client initialized with caching enabled")

    def generate_tactical_orders(self, world_state, mission_intent, objectives, cached_context):
        import hashlib

        # Check if cached context changed (objectives or history changed)
        current_hash = hashlib.md5(cached_context.encode()).hexdigest()
        context_changed = (self._cached_system_prompt_hash != current_hash)

        if context_changed:
            self._cached_system_prompt = cached_context
            self._cached_system_prompt_hash = current_hash
            logger.info("=" * 80)
            logger.info("ANTHROPIC CACHED CONTEXT CHANGED (objectives/history updated)")
            logger.info("Cached context: %d chars", len(cached_context))
            logger.info("=" * 80)

        # Format user prompt - only dynamic world state
        user_prompt = f"**CURRENT SITUATION (T+{world_state.get('mission_time', 0)}s)**\n\nMISSION INTENT: {mission_intent or 'N/A'}\n\nWORLD STATE:\n{json.dumps(world_state, indent=2)}"

        logger.info("ANTHROPIC REQUEST (cached context: %d chars, fresh prompt: %d chars)",
                   len(cached_context), len(user_prompt))
        logger.info("-" * 80)
        logger.info("USER PROMPT (DYNAMIC):\n%s", user_prompt)
        logger.info("=" * 80)

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_output_tokens,
            temperature=0.4,
            system=cached_context,
            messages=[{"role": "user", "content": user_prompt}]
        )
        content = "".join([p.text for p in resp.content if hasattr(p, "text")]) if resp.content else ""

        # LOG RAW RESPONSE FIRST for debugging
        logger.info("=" * 80)
        logger.info("ANTHROPIC RAW RESPONSE (full, %d chars):", len(content))
        logger.info("-" * 80)
        logger.info(content)
        logger.info("=" * 80)

        # Extract token usage
        token_usage = {}
        if hasattr(resp, 'usage') and resp.usage:
            token_usage = {
                'input_tokens': getattr(resp.usage, 'input_tokens', 0),
                'output_tokens': getattr(resp.usage, 'output_tokens', 0),
                'total_tokens': getattr(resp.usage, 'input_tokens', 0) + getattr(resp.usage, 'output_tokens', 0)
            }
            logger.info("Anthropic token usage: %d input, %d output, %d total",
                       token_usage['input_tokens'], token_usage['output_tokens'], token_usage['total_tokens'])

        try:
            parsed = json.loads(content)
            parsed["__raw_text"] = content
            parsed["__token_usage"] = token_usage
            logger.info("Successfully parsed Anthropic JSON response with %d orders", len(parsed.get('orders', [])))
            return parsed
        except json.JSONDecodeError as e:
            logger.error("Anthropic JSON parsing failed: %s", e)
            logger.error("Response content: %s...", content[:200])
            return None
        except Exception as e:
            logger.error("Anthropic unexpected parsing error: %s", e, exc_info=True)
            return None

    def test_connection(self):
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=20,
                messages=[{"role": "user", "content": "Hello, confirm connectivity."}]
            )
            text = "".join([p.text for p in resp.content if hasattr(p, "text")]) if resp.content else ""
            return True, text.strip()
        except Exception as e:
            return False, str(e)


class DeepSeekLLMClient(OpenAILLMClient):
    """DeepSeek is OpenAI-compatible; use OpenAI client with custom base_url."""


class AzureOpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, endpoint: str, api_version: str = "2024-02-15-preview", timeout: int = 30, max_output_tokens: int = 4096):
        from azure.ai.openai import AzureOpenAI # type: ignore
        if not endpoint:
            raise ValueError("Azure endpoint is required")
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        # Cache management for system prompt
        self._cached_system_prompt = None
        self._cached_system_prompt_hash = None
        logger.info("Azure OpenAI client initialized with caching enabled")

    def generate_tactical_orders(self, world_state, mission_intent, objectives, cached_context):
        import hashlib

        # Check if cached context changed (objectives or history changed)
        current_hash = hashlib.md5(cached_context.encode()).hexdigest()
        context_changed = (self._cached_system_prompt_hash != current_hash)

        if context_changed:
            self._cached_system_prompt = cached_context
            self._cached_system_prompt_hash = current_hash
            logger.info("=" * 80)
            logger.info("AZURE OPENAI CACHED CONTEXT CHANGED (objectives/history updated)")
            logger.info("Cached context: %d chars", len(cached_context))
            logger.info("=" * 80)

        # Format user prompt - only dynamic world state
        user_prompt = f"**CURRENT SITUATION (T+{world_state.get('mission_time', 0)}s)**\n\nMISSION INTENT: {mission_intent or 'N/A'}\n\nWORLD STATE:\n{json.dumps(world_state, indent=2)}"

        logger.info("AZURE OPENAI REQUEST (cached context: %d chars, fresh prompt: %d chars)",
                   len(cached_context), len(user_prompt))
        logger.info("-" * 80)
        logger.info("USER PROMPT (DYNAMIC):\n%s", user_prompt)
        logger.info("=" * 80)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": cached_context},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4,
            max_tokens=self.max_output_tokens
        )
        content = resp.choices[0].message.content or ""

        # LOG RAW RESPONSE FIRST for debugging
        logger.info("=" * 80)
        logger.info("AZURE OPENAI RAW RESPONSE (full, %d chars):", len(content))
        logger.info("-" * 80)
        logger.info(content)
        logger.info("=" * 80)

        # Extract token usage
        token_usage = {}
        if hasattr(resp, 'usage') and resp.usage:
            token_usage = {
                'input_tokens': getattr(resp.usage, 'prompt_tokens', 0),
                'output_tokens': getattr(resp.usage, 'completion_tokens', 0),
                'total_tokens': getattr(resp.usage, 'total_tokens', 0)
            }
            logger.info("Azure OpenAI token usage: %d input, %d output, %d total",
                       token_usage['input_tokens'], token_usage['output_tokens'], token_usage['total_tokens'])

        try:
            parsed = json.loads(content)
            parsed["__raw_text"] = content
            parsed["__token_usage"] = token_usage
            logger.info("Successfully parsed Azure OpenAI JSON response with %d orders", len(parsed.get('orders', [])))
            return parsed
        except json.JSONDecodeError as e:
            logger.error("Azure OpenAI JSON parsing failed: %s", e)
            logger.error("Response content: %s...", content[:200])
            return None
        except Exception as e:
            logger.error("Azure OpenAI unexpected parsing error: %s", e, exc_info=True)
            return None

    def test_connection(self):
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello, confirm connectivity."}],
                max_tokens=20
            )
            text = resp.choices[0].message.content or ""
            return True, text.strip()
        except Exception as e:
            return False, str(e)


class LocalLLMClient(BaseLLMClient):
    """Placeholder for local/assistant-less mode."""

    def __init__(self):
        self.model = "local"

    def generate_tactical_orders(self, world_state, mission_intent, objectives, system_prompt):
        return None

    def test_connection(self):
        return True, "Local mode (no external LLM)"
