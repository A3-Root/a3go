"""
LLM Provider Manager with fallback support

Manages multiple LLM providers with priority-based fallback.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple

from .providers import (
    GeminiLLMClient,
    OpenAILLMClient,
    AnthropicLLMClient,
    DeepSeekLLMClient,
    AzureOpenAILLMClient,
    LocalLLMClient,
)
from .gemini import RateLimiter

logger = logging.getLogger('batcom.ai.provider_manager')


class ProviderConfig:
    """Configuration for a single LLM provider"""

    def __init__(self, config_dict: Dict[str, Any]):
        self.name = config_dict.get('name', 'unnamed')
        self.priority = config_dict.get('priority', 999)
        self.enabled = config_dict.get('enabled', False)
        self.provider = config_dict.get('provider', '').lower()
        self.model = config_dict.get('model', '')
        self.endpoint = config_dict.get('endpoint', '')
        self.api_key = config_dict.get('api_key', '')
        self.timeout = config_dict.get('timeout', 30)
        self.min_interval = config_dict.get('min_interval', 10.0)
        self.rate_limit = config_dict.get('rate_limit', None)
        self.max_input_tokens = config_dict.get('max_input_tokens', 32000)
        self.max_output_tokens = config_dict.get('max_output_tokens', 128000)

        # OpenAI specific
        self.use_responses_api = config_dict.get('use_responses_api', True)

        # Gemini specific
        self.thinking_enabled = config_dict.get('thinking_enabled', False)
        self.thinking_mode = config_dict.get('thinking_mode', 'native_sdk')
        self.thinking_budget = config_dict.get('thinking_budget', -1)
        self.thinking_level = config_dict.get('thinking_level', 'high')
        self.reasoning_effort = config_dict.get('reasoning_effort', 'medium')
        self.include_thoughts = config_dict.get('include_thoughts', True)
        self.log_thoughts_to_file = config_dict.get('log_thoughts_to_file', True)

        # Azure specific
        self.api_version = config_dict.get('api_version', '2024-02-15-preview')

        # Calculate min_interval from rate_limit if not set
        if self.min_interval is None and self.rate_limit:
            try:
                rate_limit_val = float(self.rate_limit)
                if rate_limit_val > 0:
                    self.min_interval = 60.0 / rate_limit_val
            except Exception:
                pass
        if self.min_interval is None:
            self.min_interval = 10.0

    def __repr__(self):
        return f"ProviderConfig(name={self.name}, priority={self.priority}, provider={self.provider}, model={self.model})"


class LLMProviderManager:
    """
    Manages multiple LLM providers with automatic fallback

    Tries providers in priority order. If a provider fails, automatically
    falls back to the next enabled provider.
    """

    def __init__(self, providers_config: List[Dict[str, Any]], state_manager=None):
        """
        Initialize provider manager

        Args:
            providers_config: List of provider configuration dicts
            state_manager: Optional state manager for API key lookup
        """
        self.state_manager = state_manager
        self.providers: List[ProviderConfig] = []
        self.active_provider_index = 0
        self.provider_failure_counts: Dict[str, int] = {}
        self.max_failures_per_provider = 3  # After 3 failures, skip provider until reset

        # Parse and sort providers by priority
        for config_dict in providers_config:
            provider_config = ProviderConfig(config_dict)
            if provider_config.enabled:
                self.providers.append(provider_config)

        # Sort by priority (lower number = higher priority)
        self.providers.sort(key=lambda p: p.priority)

        if not self.providers:
            logger.warning("No enabled LLM providers configured!")
        else:
            logger.info("Configured %d enabled LLM providers:", len(self.providers))
            for i, p in enumerate(self.providers):
                logger.info("  Priority %d: %s (%s %s)", p.priority, p.name, p.provider, p.model)

    def create_client(self, provider_config: ProviderConfig) -> Tuple[Optional[Any], Optional[RateLimiter], str]:
        """
        Create LLM client and rate limiter for a provider

        Args:
            provider_config: Provider configuration

        Returns:
            Tuple of (client, rate_limiter, error_message)
            Returns (None, None, error) on failure
        """
        try:
            # Get API key from config, state manager, or environment
            api_key = provider_config.api_key
            if not api_key and self.state_manager:
                provider_keys = self.state_manager.api_keys.get(provider_config.provider, {})
                api_key = provider_keys.get('key', '')
            if not api_key:
                env_key_map = {
                    'openai': 'OPENAI_API_KEY',
                    'gpt': 'OPENAI_API_KEY',
                    'gemini': 'GEMINI_API_KEY',
                    'claude': 'ANTHROPIC_API_KEY',
                    'anthropic': 'ANTHROPIC_API_KEY',
                    'deepseek': 'DEEPSEEK_API_KEY',
                    'azure': 'AZURE_OPENAI_API_KEY',
                    'azureopenai': 'AZURE_OPENAI_API_KEY',
                }
                env_var = env_key_map.get(provider_config.provider)
                if env_var:
                    api_key = os.getenv(env_var, '')

            # Provider-specific initialization
            if provider_config.provider == "gemini":
                if not api_key:
                    return None, None, f"API key not set for {provider_config.name}"

                thinking_config = {
                    'thinking_enabled': provider_config.thinking_enabled,
                    'thinking_mode': provider_config.thinking_mode,
                    'thinking_budget': provider_config.thinking_budget,
                    'thinking_level': provider_config.thinking_level,
                    'reasoning_effort': provider_config.reasoning_effort,
                    'include_thoughts': provider_config.include_thoughts,
                    'log_thoughts_to_file': provider_config.log_thoughts_to_file
                }

                if provider_config.thinking_mode == "openai_compat":
                    from .providers import GeminiOpenAICompatClient
                    client = GeminiOpenAICompatClient(
                        api_key=api_key,
                        model=provider_config.model,
                        timeout=provider_config.timeout,
                        max_output_tokens=provider_config.max_output_tokens,
                        thinking_config=thinking_config
                    )
                else:
                    client = GeminiLLMClient(
                        api_key=api_key,
                        model=provider_config.model,
                        timeout=provider_config.timeout,
                        endpoint=provider_config.endpoint,
                        max_output_tokens=provider_config.max_output_tokens,
                        thinking_config=thinking_config
                    )

                rate_limiter = RateLimiter(min_interval=provider_config.min_interval)
                return client, rate_limiter, ""

            elif provider_config.provider in ["openai", "gpt"]:
                if not api_key:
                    return None, None, f"API key not set for {provider_config.name}"

                client = OpenAILLMClient(
                    api_key=api_key,
                    model=provider_config.model,
                    endpoint=provider_config.endpoint,
                    timeout=provider_config.timeout,
                    max_output_tokens=provider_config.max_output_tokens,
                    use_responses_api=provider_config.use_responses_api
                )
                rate_limiter = RateLimiter(min_interval=provider_config.min_interval)
                return client, rate_limiter, ""

            elif provider_config.provider in ["claude", "anthropic"]:
                if not api_key:
                    return None, None, f"API key not set for {provider_config.name}"

                client = AnthropicLLMClient(
                    api_key=api_key,
                    model=provider_config.model,
                    endpoint=provider_config.endpoint,
                    timeout=provider_config.timeout,
                    max_output_tokens=provider_config.max_output_tokens
                )
                rate_limiter = RateLimiter(min_interval=provider_config.min_interval)
                return client, rate_limiter, ""

            elif provider_config.provider == "deepseek":
                if not api_key:
                    return None, None, f"API key not set for {provider_config.name}"

                endpoint = provider_config.endpoint or "https://api.deepseek.com"
                client = DeepSeekLLMClient(
                    api_key=api_key,
                    model=provider_config.model,
                    endpoint=endpoint,
                    timeout=provider_config.timeout,
                    max_output_tokens=provider_config.max_output_tokens
                )
                rate_limiter = RateLimiter(min_interval=provider_config.min_interval)
                return client, rate_limiter, ""

            elif provider_config.provider in ["azure", "azureopenai"]:
                if not api_key:
                    return None, None, f"API key not set for {provider_config.name}"
                endpoint = provider_config.endpoint or os.getenv('AZURE_OPENAI_ENDPOINT', '')
                if not endpoint:
                    return None, None, f"Endpoint not set for {provider_config.name}"

                client = AzureOpenAILLMClient(
                    api_key=api_key,
                    model=provider_config.model,
                    endpoint=endpoint,
                    api_version=provider_config.api_version,
                    timeout=provider_config.timeout,
                    max_output_tokens=provider_config.max_output_tokens
                )
                rate_limiter = RateLimiter(min_interval=provider_config.min_interval)
                return client, rate_limiter, ""

            elif provider_config.provider == "local":
                client = LocalLLMClient()
                rate_limiter = RateLimiter(min_interval=provider_config.min_interval)
                return client, rate_limiter, ""

            else:
                return None, None, f"Unknown provider type: {provider_config.provider}"

        except Exception as e:
            return None, None, f"Failed to initialize {provider_config.name}: {str(e)}"

    def get_next_provider(self) -> Optional[Tuple[ProviderConfig, Any, RateLimiter]]:
        """
        Get the next available provider (skipping failed ones)

        Returns:
            Tuple of (provider_config, client, rate_limiter) or None if no providers available
        """
        if not self.providers:
            return None

        # Try providers in priority order
        for attempt in range(len(self.providers)):
            provider_config = self.providers[self.active_provider_index]

            # Check if this provider has too many failures
            failure_count = self.provider_failure_counts.get(provider_config.name, 0)
            if failure_count >= self.max_failures_per_provider:
                logger.warning("Skipping %s (too many failures: %d)", provider_config.name, failure_count)
                self.active_provider_index = (self.active_provider_index + 1) % len(self.providers)
                continue

            # Try to create client
            client, rate_limiter, error = self.create_client(provider_config)
            if client and rate_limiter:
                logger.info("Using LLM provider: %s (priority %d, %s %s)",
                           provider_config.name, provider_config.priority,
                           provider_config.provider, provider_config.model)
                return provider_config, client, rate_limiter
            else:
                logger.warning("Failed to initialize %s: %s", provider_config.name, error)
                self.record_failure(provider_config.name)
                self.active_provider_index = (self.active_provider_index + 1) % len(self.providers)

        # No providers available
        logger.error("All LLM providers failed or unavailable!")
        return None

    def record_failure(self, provider_name: str):
        """Record a failure for a provider"""
        self.provider_failure_counts[provider_name] = self.provider_failure_counts.get(provider_name, 0) + 1
        logger.warning("Provider %s failure count: %d/%d",
                      provider_name, self.provider_failure_counts[provider_name],
                      self.max_failures_per_provider)

    def record_success(self, provider_name: str):
        """Record a success for a provider (resets failure count)"""
        if provider_name in self.provider_failure_counts:
            del self.provider_failure_counts[provider_name]

    def fallback_to_next(self):
        """Move to next provider in priority order"""
        if not self.providers:
            return

        current_provider = self.providers[self.active_provider_index]
        logger.info("Falling back from %s to next provider...", current_provider.name)

        self.active_provider_index = (self.active_provider_index + 1) % len(self.providers)

    def reset_failures(self):
        """Reset all provider failure counts"""
        self.provider_failure_counts.clear()
        logger.info("Reset all provider failure counts")
