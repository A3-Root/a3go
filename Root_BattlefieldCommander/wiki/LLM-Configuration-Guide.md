# LLM Configuration Guide

Complete guide to configuring Large Language Model providers for BATCOM, including setup, optimization, and cost management.

## Table of Contents

- [Overview](#overview)
- [Supported Providers](#supported-providers)
- [Quick Setup](#quick-setup)
- [Provider-Specific Configuration](#provider-specific-configuration)
  - [Google Gemini](#google-gemini)
  - [OpenAI GPT](#openai-gpt)
  - [Anthropic Claude](#anthropic-claude)
  - [DeepSeek](#deepseek)
  - [Azure OpenAI](#azure-openai)
  - [Local/Custom Endpoints](#localcustom-endpoints)
- [Configuration Methods](#configuration-methods)
- [Cost Optimization](#cost-optimization)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)

---

## Overview

BATCOM uses Large Language Models to make intelligent tactical decisions. The system supports multiple LLM providers with automatic fallback and rate limiting.

### Key Features

- **Multi-Provider Support** - Switch between providers seamlessly
- **Native Context Caching** - Gemini's caching reduces costs by 90%
- **Rate Limiting** - Prevent API quota exhaustion
- **Circuit Breaker** - Automatic disable after consecutive errors
- **Token Tracking** - Monitor usage and costs
- **Async Operations** - Non-blocking LLM calls

### Architecture

```
SQF Layer → Python Backend → LLM Provider
    ↓           ↓                 ↓
 Config    Rate Limiter      API Response
            Caching
            Retry Logic
```

---

## Supported Providers

| Provider | Default Model | Cost | Speed | Quality | Caching |
|----------|--------------|------|-------|---------|---------|
| **Gemini** | `gemini-2.5-flash-lite` | Very Low | Very Fast | Good | Native |
| **OpenAI** | `gpt-4o-mini` | Low | Fast | Very Good | Prompt Caching |
| **Claude** | `claude-3-5-sonnet` | Medium | Medium | Excellent | Prompt Caching |
| **DeepSeek** | `deepseek-chat` | Very Low | Medium | Good | No |
| **Azure** | Custom | Varies | Varies | Varies | No |
| **Local** | Custom | Free | Varies | Varies | Varies |

### Recommendations

**For Production Use**:
- **Best Overall**: Gemini 2.5 Flash Lite (fast, cheap, reliable)
- **Best Quality**: Claude 3.5 Sonnet (best reasoning, higher cost)
- **Budget Option**: Gemini 2.5 Flash Lite (fast, FREE)

**For Development/Testing**:
- **Gemini Flash** - Fast iterations with caching
- **Local Models** - No API costs, requires setup

---

## Quick Setup

### Method 1: In-Game Configuration

```sqf
// Set LLM provider and API key
["setLLMConfig", createHashMapFromArray [
  ["provider","Provider Name"],
  ["api_key","API Key"],
  ["model","LLM Model"],
  ["endpoint","API Endpoint"],
  ["rate_limit",Rate Limit (Minimum seconds between LLM calls)]
], true] call Root_fnc_batcomInit;
```

### Method 2: Configuration File (Recommended)

Edit `@BATCOM/batcom/config/guardrails.json`. You can use the existing template available in the file or create a new one. Only the `current` template is read in-game.

```json
{
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "api_key": "YOUR_API_KEY",
    "timeout": 30,
    "min_interval": 10
}
```

### Method 3: Environment Variable

Set environment variable before starting Arma 3 server:

**Windows**:
```batch
set GEMINI_API_KEY=YOUR_API_KEY
```

**Linux**:
```bash
export GEMINI_API_KEY=YOUR_API_KEY
```

### Testing Configuration

```sqf
// Test LLM connectivity
private _result = call Root_fnc_testGeminiConnection;
systemChat _result;
```

---

## Provider-Specific Configuration

### Google Gemini

**Recommended for most users** - Fast, cheap, and includes native context caching.

#### Getting an API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create new API key
3. Copy the key

#### Configuration

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_GEMINI_API_KEY"],
    ["model", "gemini-2.5-flash-lite"],    // Optional: override model
    ["timeout", 30],                       // Optional: timeout in seconds
    ["min_interval", 10]                   // Optional: min seconds between calls
], true] call Root_fnc_batcomInit;
```

#### Available Models

| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| `gemini-2.5-flash-lite` | 1M tokens | Very Fast | Very Low | Production (default) |
| `gemini-2.0-flash-exp` | 1M tokens | Fast | Low | Experimental features |
| `gemini-1.5-flash` | 1M tokens | Fast | Low | Stable production |
| `gemini-1.5-pro` | 2M tokens | Medium | Medium | Complex reasoning |

#### Context Caching

Gemini includes **native context caching** that reduces costs by 90%:

**How it works**:
1. System prompt, objectives, and order history are cached
2. Cache valid for 1 hour
3. Only new information (current world state) incurs full cost
4. Automatic cache refresh before expiry

**Cost Comparison**:
- **Without caching**: ~4,300 tokens/call
- **With caching**: ~440 effective tokens/call
- **Savings**: 90% cost reduction

**Configuration**:
```python
# Caching is automatic for Gemini
# No additional configuration needed
# Monitor in: @BATCOM/token_usage.json
```

#### Rate Limits

- **Free tier**: 15 requests/minute, 1,500 requests/day
- **Paid tier**: 1,000 requests/minute, 4M requests/day

**Recommended settings**:
```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"],
    ["min_interval", 10]  // 6 requests/minute (safe for free tier)
], true] call Root_fnc_batcomInit;
```

---

### OpenAI GPT

High-quality responses with good reasoning capabilities.

#### Getting an API Key

1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create new API key
3. Add credits to account

#### Configuration

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "openai"],
    ["api_key", "sk-..."],
    ["model", "gpt-4o-mini"],              // Optional
    ["timeout", 30],                       // Optional
    ["min_interval", 10]                   // Optional
], true] call Root_fnc_batcomInit;
```

#### Available Models

| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| `gpt-4o-mini` | 128K | Fast | Low | Production (default) |
| `gpt-4o` | 128K | Medium | Medium | Best quality |
| `gpt-4-turbo` | 128K | Medium | High | Complex tasks |
| `gpt-3.5-turbo` | 16K | Very Fast | Very Low | Simple tasks |

#### Costs

**GPT-4o-mini** (recommended):
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens
- Typical call: ~4,300 tokens = $0.0006-$0.001

**No native caching** - Consider Claude or Gemini for cost optimization.

#### Rate Limits

Depends on tier:
- **Free tier**: 3 requests/minute
- **Tier 1**: 60 requests/minute
- **Tier 5**: 10,000 requests/minute

---

### Anthropic Claude

Best reasoning capabilities, excellent for complex tactical scenarios.

#### Getting an API Key

1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create new API key
3. Add credits to account

#### Configuration

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "anthropic"],
    ["api_key", "sk-ant-..."],
    ["model", "claude-3-5-sonnet-20241022"],  // Optional
    ["timeout", 30],                          // Optional
    ["min_interval", 10]                      // Optional
], true] call Root_fnc_batcomInit;
```

#### Available Models

| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| `claude-3-5-sonnet-20241022` | 200K | Medium | Medium | Production (default) |
| `claude-3-5-haiku-20241022` | 200K | Fast | Low | Fast decisions |
| `claude-3-opus-20240229` | 200K | Slow | High | Most complex tasks |

#### Prompt Caching

Claude supports **prompt caching** (different from Gemini):
- Caches conversation history
- Reduces costs for repetitive prompts
- 90% cost reduction on cached tokens
- Automatic in BATCOM

#### Costs

**Claude 3.5 Sonnet**:
- Input: $3.00 per 1M tokens
- Output: $15.00 per 1M tokens
- Cached input: $0.30 per 1M tokens (90% off)
- Typical call with cache: ~$0.002-$0.003

#### Rate Limits

- **Free tier**: 5 requests/minute
- **Build tier**: 50 requests/minute
- **Scale tier**: 1,000 requests/minute

---

### DeepSeek

Budget-friendly option with decent quality.

#### Getting an API Key

1. Visit [DeepSeek Platform](https://platform.deepseek.com/)
2. Create account and API key
3. Add credits (very cheap)

#### Configuration

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "deepseek"],
    ["api_key", "YOUR_DEEPSEEK_KEY"],
    ["model", "deepseek-chat"],            // Optional
    ["timeout", 30],                       // Optional
    ["min_interval", 10]                   // Optional
], true] call Root_fnc_batcomInit;
```

#### Costs

**Extremely cheap**:
- Input: $0.14 per 1M tokens
- Output: $0.28 per 1M tokens
- Typical call: ~4,300 tokens = $0.0006

#### Trade-offs

**Pros**:
- Very low cost
- Decent quality for tactical decisions
- Fast response times

**Cons**:
- Less sophisticated reasoning than GPT-4 or Claude
- May require more specific prompts
- Limited context compared to newer models

---

### Azure OpenAI

Enterprise deployment with your own infrastructure.

#### Prerequisites

1. Azure account with OpenAI service
2. Deployed model endpoint
3. API key and endpoint URL

#### Configuration

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "azure"],
    ["api_key", "YOUR_AZURE_KEY"],
    ["endpoint", "https://your-resource.openai.azure.com/"],
    ["model", "gpt-4o-mini"],              // Your deployed model
    ["timeout", 30],
    ["min_interval", 10]
], true] call Root_fnc_batcomInit;
```

#### Configuration File

Edit `guardrails.json`:

```json
{
    "provider": "azure",
    "endpoint": "https://your-resource.openai.azure.com/",
    "api_key": "your-azure-key",
    "model": "your-deployment-name",
    "timeout": 30,
    "min_interval": 10
}
```

---

### Local/Custom Endpoints

Use self-hosted models or custom API endpoints.

#### Supported Formats

Any OpenAI-compatible API:
- **LM Studio**
- **Ollama**
- **vLLM**
- **Text Generation WebUI**
- **Custom backends**

#### Configuration

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "local"],
    ["endpoint", "http://localhost:1234/v1/chat/completions"],
    ["api_key", "not-needed"],             // Some servers require dummy key
    ["model", "your-model-name"],
    ["timeout", 60],                       // Local may be slower
    ["min_interval", 0]                    // No rate limit needed
], true] call Root_fnc_batcomInit;
```

#### Configuration File

Edit `guardrails.json`:

```json
{
    "provider": "local",
    "endpoint": "http://localhost:1234/v1/chat/completions",
    "api_key": "not-needed",
    "model": "your-model-name",
    "timeout": 60,
    "min_interval": 0,
    "max_input_tokens": 4096,
    "max_output_tokens": 2048
}
```

#### Recommended Models

For local deployment:
- **Llama 3.1 8B** - Good quality, runs on consumer GPU
- **Mistral 7B** - Fast, decent quality
- **Qwen 2.5 14B** - Excellent quality, requires more VRAM

#### Performance Considerations

- **Response time**: Local models are slower (5-30s)
- **Hardware**: Requires GPU with 8GB+ VRAM for 7B models
- **Quality**: Smaller models may make suboptimal decisions
- **Testing**: Thoroughly test before production use

---

## Configuration Methods

### Priority Order

BATCOM checks configuration in this order:
1. In-game `setLLMConfig` command (highest priority)
2. `guardrails.json` file
3. Environment variables
4. Default values from `config.cpp`

### In-Game Configuration

**Advantages**:
- No file editing required
- Immediate effect
- Can be scripted in mission init
- Per-mission customization

**Example**:
```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"],
    ["model", "gemini-2.5-flash-lite"],
    ["timeout", 30],
    ["min_interval", 10]
], true] call Root_fnc_batcomInit;
```

### Configuration File

**Advantages**:
- Persistent across missions
- Version control friendly
- Easy to backup/restore
- Supports all options

**Location**: `@BATCOM/batcom/config/guardrails.json`

**Full Example**:
```json
{
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "endpoint": null,
    "api_key": "YOUR_API_KEY",
    "timeout": 30,
    "min_interval": 10,
    "rate_limit": 60,
    "max_input_tokens": 1000000,
    "max_output_tokens": 8192,
    "use_caching": true,
    "cache_ttl": 3600
}
```

### Environment Variables

**Advantages**:
- Secure (no keys in files)
- Easy for automated deployments
- Per-server configuration

**Supported Variables**:
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DEEPSEEK_API_KEY`
- `AZURE_OPENAI_KEY`

**Example** (Windows):
```batch
set GEMINI_API_KEY=your-key-here
arma3server.exe -serverMod=@BATCOM ...
```

### CfgBATCOM Defaults

**Location**: `addons/main/config.cpp`

**Default Values**:
```cpp
class ai {
    enabled = 1;
    provider = "gemini";
    model = "gemini-2.5-flash-lite";
    timeout = 30;
    min_interval = 30.0;
};
```

These are fallback values if no other configuration is found.

---

## Cost Optimization

### Strategy 1: Use Gemini with Caching

**Best cost-per-decision**:
- 90% cost reduction vs. no caching
- ~$0.0001 per decision with caching
- Automatic cache management

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"],
    ["model", "gemini-2.5-flash-lite"]  // Caching enabled by default
], true] call Root_fnc_batcomInit;
```

### Strategy 2: Increase Decision Interval

Reduce LLM call frequency:

```sqf
// In mission init or config.cpp
BATCOM_DECISION_INTERVAL = 60;  // 60 seconds between decisions (default: 45)
```

**Trade-off**: Less responsive AI, but 25-50% cost reduction.

### Strategy 3: Limit AO Scope

Smaller AO = less world data = smaller prompts:

```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_center", getPos someMarker],
    ["ao_radius", 1000]  // Smaller radius = less data
], nil] call Root_fnc_batcomInit;
```

### Strategy 4: Use Faster Models

Faster models are usually cheaper:

| Provider | Model | Cost/Decision | Quality |
|----------|-------|---------------|---------|
| Gemini | `gemini-2.5-flash-lite` (cached) | $0.0001 | Good |
| DeepSeek | `deepseek-chat` | $0.0006 | Good |
| OpenAI | `gpt-3.5-turbo` | $0.0008 | Good |
| OpenAI | `gpt-4o-mini` | $0.0012 | Very Good |
| Claude | `claude-3-5-haiku` | $0.002 | Very Good |

### Strategy 5: Monitor Usage

Track token usage to identify optimization opportunities:

```sqf
// Get current usage stats
private _stats = call Root_fnc_getTokenStats;
systemChat format ["Total tokens: %1", _stats get "total_tokens"];
systemChat format ["Total cost: $%1", _stats get "total_cost"];
```

**Log Location**: `@BATCOM/token_usage.json`

### Cost Estimation

**Example Mission** (2 hours, 45s decision interval):
- **Decisions**: 160 (2 hours / 45s)
- **Tokens per decision**: 440 (with Gemini caching)
- **Total tokens**: 70,400
- **Cost**: ~$0.016 (with Gemini Flash Lite)

**Without caching**: ~$0.160 (10x more expensive)

---

## Performance Tuning

### Response Time Optimization

#### Reduce Latency

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["model", "gemini-2.5-flash-lite"],  // Fastest model
    ["timeout", 15],                      // Lower timeout
    ["min_interval", 5]                   // More frequent updates
], true] call Root_fnc_batcomInit;
```

#### Async Processing

BATCOM uses async LLM calls by default:
- World scanning continues during LLM processing
- Commands execute immediately when ready
- No blocking operations

### Rate Limit Configuration

Match your API tier:

**Free Tier**:
```sqf
["setLLMConfig", createHashMapFromArray [
    ["min_interval", 10]  // 6 requests/minute
], true] call Root_fnc_batcomInit;
```

**Paid Tier**:
```sqf
["setLLMConfig", createHashMapFromArray [
    ["min_interval", 2]  // 30 requests/minute
], true] call Root_fnc_batcomInit;
```

### Circuit Breaker

Automatic disable after consecutive errors:

**Configuration** (in `batcom/runtime/commander.py`):
```python
max_consecutive_errors = 3  # Disable LLM after 3 errors
```

**Re-enable**:
```sqf
["deployCommander", false] call Root_fnc_batcomInit;
["deployCommander", true] call Root_fnc_batcomInit;
```

### Timeout Configuration

Adjust based on provider and model:

```sqf
["setLLMConfig", createHashMapFromArray [
    ["timeout", 30],  // Default: 30s
    // Gemini Flash: 15s
    // GPT-4o: 30s
    // Local models: 60s
], true] call Root_fnc_batcomInit;
```

---

## Troubleshooting

### Connection Issues

#### Test Connectivity

```sqf
private _result = call Root_fnc_testGeminiConnection;
systemChat _result;
```

#### Common Errors

**"API key not set"**:
```sqf
// Set API key
["setLLMApiKey", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
], nil] call Root_fnc_batcomInit;
```

**"Connection timeout"**:
- Check internet connectivity
- Increase timeout: `["timeout", 60]`
- Try different provider

**"Rate limit exceeded"**:
- Increase `min_interval`
- Upgrade API tier
- Switch to provider with higher limits

**"Invalid API key"**:
- Verify key is correct
- Check key hasn't expired
- Ensure key has necessary permissions

### Performance Issues

#### Slow Responses

**Diagnosis**:
```sqf
// Check last decision time
diag_log format ["Last decision: %1s ago",
    diag_tickTime - (BATCOM get "last_decision_time")];
```

**Solutions**:
1. Use faster model (`gemini-2.5-flash-lite`)
2. Reduce AO size
3. Lower timeout
4. Check network latency

#### High Costs

**Check Usage**:
```sqf
private _stats = call Root_fnc_getTokenStats;
diag_log format ["Tokens/hour: %1", _stats get "tokens_per_hour"];
```

**Solutions**:
1. Enable Gemini caching
2. Increase decision interval
3. Reduce AO scope
4. Switch to cheaper provider

### Debug Logging

Enable detailed logging:

**In config.cpp**:
```cpp
class logging {
    level = "DEBUG";  // DEBUG, INFO, WARN, ERROR
    arma_console = 1; // Print to Arma console
};
```

**Log Locations**:
- **Python logs**: `@BATCOM/logs/batcom_YYYYMMDD_HHMMSS.log`
- **API call logs**: `@BATCOM/apicall.<map>.<mission>.<ao>.<timestamp>.log`
- **Token usage**: `@BATCOM/token_usage.json`
- **Arma RPT**: Arma 3 logs directory

### Provider-Specific Issues

#### Gemini Issues

**"Caching not working"**:
- Verify using Gemini Flash or Flash Lite
- Check `use_caching = true` in config
- Monitor `token_usage.json` for cache metrics

**"Model not found"**:
- Use supported models: `gemini-2.5-flash-lite`, `gemini-1.5-flash`
- Check model availability in your region

#### OpenAI Issues

**"Insufficient quota"**:
- Add credits to account
- Upgrade to paid tier
- Switch to free provider (Gemini)

**"Model deprecated"**:
- Update to current model name
- Check [OpenAI docs](https://platform.openai.com/docs/models)

#### Claude Issues

**"Rate limit exceeded"**:
- Increase `min_interval` to 12+ seconds
- Upgrade to Build or Scale tier

**"Context too long"**:
- Reduce AO size
- Lower `max_controlled_groups`
- Use shorter mission descriptions

---

## Advanced Configuration

### Custom System Prompts

Modify `batcom/ai/providers.py` to customize behavior:

```python
system_prompt = """
You are a tactical AI commander specializing in [YOUR FOCUS].
Your objectives are:
1. [CUSTOM OBJECTIVE 1]
2. [CUSTOM OBJECTIVE 2]
...
"""
```

### Multi-Provider Fallback

Implement automatic fallback in mission init:

```sqf
// Try Gemini first
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", GEMINI_KEY]
], true] call Root_fnc_batcomInit;

// Test connection
private _result = call Root_fnc_testGeminiConnection;
if (_result find "success" == -1) then {
    // Fallback to OpenAI
    ["setLLMConfig", createHashMapFromArray [
        ["provider", "openai"],
        ["api_key", OPENAI_KEY]
    ], true] call Root_fnc_batcomInit;
};
```

### Custom Token Limits

Edit `guardrails.json`:

```json
{
    "max_input_tokens": 50000,   // Reduce context size
    "max_output_tokens": 2048    // Limit response length
}
```

---

## Best Practices

### 1. Use Gemini for Production
- Fastest responses
- Lowest cost with caching
- Reliable and well-tested

### 2. Set Appropriate Rate Limits
- Match your API tier
- Leave margin for error retries
- Monitor usage regularly

### 3. Test Before Production
```sqf
// Always test configuration
call Root_fnc_testGeminiConnection;
```

### 4. Monitor Costs
- Check `token_usage.json` regularly
- Set billing alerts on provider platforms
- Track cost per mission

### 5. Use Environment Variables for Keys
- Never commit keys to version control
- Use env vars or secure config management
- Rotate keys regularly

### 6. Enable Logging During Setup
- Use DEBUG level initially
- Switch to INFO for production
- Keep ERROR logs enabled

---

## Quick Reference

### Provider Comparison

| Feature | Gemini | OpenAI | Claude | DeepSeek | Local |
|---------|--------|--------|--------|----------|-------|
| Cost | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★★★★ | ★★★★★ |
| Speed | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ★★☆☆☆ |
| Quality | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★☆☆ | ★★★☆☆ |
| Setup | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | ★★☆☆☆ |
| Caching | Native | No | Prompt | No | No |

### Command Reference

```sqf
// Set provider
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini|openai|anthropic|deepseek|azure|local"],
    ["api_key", "YOUR_KEY"]
], true] call Root_fnc_batcomInit;

// Test connection
call Root_fnc_testGeminiConnection;

// Get stats
call Root_fnc_getTokenStats;
```

---

## See Also

- [API Reference](API-Reference.md) - Complete function documentation
- [Server Setup Guide](Server-Setup-Guide.md) - Initial installation
- [Troubleshooting Guide](Troubleshooting-Guide.md) - Detailed debugging
- [Architecture Overview](Architecture-Overview.md) - System internals

---

**Last Updated**: 2025-12-05
