# Google Gemini Native Context Caching

## Overview

The BATCOM system implements **intelligent context caching** with Google Gemini's native caching API. The cache includes:
- **System prompt**: Tactical guidelines and command format (static)
- **Current objectives**: Active mission objectives and their states (slow-changing)
- **Order history**: Last 5 decision cycles showing what the LLM has done (contextual memory)

This provides massive cost savings and gives the LLM **continuity** - it remembers what it has done and can avoid redundant orders.

## How It Works

### Native Caching Benefits

1. **90% Cost Reduction**: Cached tokens are charged at 1/10th the normal rate
2. **Automatic Management**: Cache is created on first call and reused for 1 hour
3. **Transparent Fallback**: If caching fails, automatically falls back to standard mode
4. **Smart Refresh**: Cache is refreshed when system prompt changes or expires

### Cache Lifecycle

```
First Call:
- System prompt is sent to Gemini Caching API
- CachedContent object is created with 1-hour TTL
- Cache name is stored for subsequent calls

Subsequent Calls (within 1 hour):
- Only the user prompt (world state + objectives) is sent
- Cache name is referenced in the API call
- Gemini automatically applies the cached system prompt
- Token usage shows cached_content_token_count

After 1 Hour or Prompt Change:
- Old cache is deleted
- New cache is created
- Process repeats
```

## Token Usage Reporting

When caching is active, you'll see enhanced logging:

```
GEMINI TOKEN USAGE (WITH NATIVE CACHE):
  Input tokens: 450
  Cached tokens: 2150 (90% cost reduction!)
  Output tokens: 320
  Total tokens: 2920
  Cache savings: ~2150 tokens not charged at full rate
```

**Cost Calculation**:
- Without cache: 2600 input tokens × $1.00 = ~$2.60 per 1M tokens
- With cache: 450 input tokens × $1.00 + 2150 cached tokens × $0.10 = ~$0.66 per 1M tokens
- **Savings: 75% cost reduction per call**

## Implementation Details

### Cache Creation

The cache is created automatically on first call:

```python
cache_config = types.CreateCachedContentConfig(
    model=self.model,
    system_instruction=system_prompt,  # ~2000 tokens
    ttl=timedelta(hours=1)  # 1 hour lifetime
)

cached_content = client.caches.create(config=cache_config)
```

### Using the Cache

Subsequent calls reference the cache:

```python
response = client.models.generate_content(
    model=self.model,
    contents=user_prompt,  # Only dynamic content
    config=types.GenerateContentConfig(
        cached_content=cached_content.name  # Reference cache
    )
)
```

## What Gets Cached

**Cached (90% discount)** - Updates when objectives change or every 1 hour:
- **System prompt** (~2000 tokens): Tactical guidelines, command format, constraints
- **Current objectives** (~500 tokens): Active mission objectives with descriptions, positions, priorities
- **Order history** (~300 tokens): Last 5 decision cycles showing what the LLM has commanded

**Not Cached (full price)** - Sent fresh every decision cycle:
- **World state** (~1500 tokens): Current group positions, unit counts, combat status
- **Mission intent**: Dynamic mission description
- **Force summary**: Real-time threat assessment and force ratios

## Cache Invalidation

The cache is automatically updated when:
1. **Objectives change** (new objective, objective completed, priority changed)
2. **Cache expires** (1 hour TTL - refreshes automatically)
3. **System prompt changes** (very rare, only during development)

When cache is valid (most of the time):
- Only ~1500 tokens sent per call (world state)
- ~2800 tokens cached (90% discount)
- **Total effective cost: ~440 tokens per call** (vs 4300 without caching)

## Fallback Behavior

If caching fails (e.g., unsupported model, API error), the system automatically falls back to standard mode:

1. Logs warning about cache failure
2. Uses `system_instruction` parameter instead
3. Continues operation without interruption
4. No impact on functionality, only cost optimization is lost

## Monitoring

### Log Messages

**Cache Created**:
```
GEMINI NATIVE CACHE CREATED
Cache name: cachedContents/abc123xyz
Cache expires: 2025-12-05T10:30:00+00:00
Cached tokens: ~2000 (estimated)
```

**Cache Reused**:
```
GEMINI REQUEST (using NATIVE cached system prompt from: cachedContents/abc123xyz)
Cache remains valid until: 2025-12-05T10:30:00+00:00
```

**Cache Expired**:
```
GEMINI CACHE EXPIRED - Refreshing native cache
```

## Requirements

- Google Gemini API key
- `google-genai` Python SDK (latest version)
- Models that support caching (most Gemini models do)

## Contextual Memory (Order History)

One of the most powerful features is that the LLM **remembers its previous decisions**. The cached context includes:

```
ORDER HISTORY (Your Previous Decisions)
================================================================================
This shows what orders you've issued in recent decision cycles:

[Cycle 5 @ T+150s]
  Commands: 8
  Types: defend_area: 3, seek_and_destroy: 2, deploy_asset: 3

[Cycle 6 @ T+180s]
  Commands: 2
  Types: move_to: 2

[Cycle 7 @ T+210s]
  Commands: 0
  (Situation stable, no new orders needed)

Use this history to understand what you've already ordered.
Don't repeat identical orders unless the situation has changed.
```

This enables:
- **Avoid redundant orders**: LLM sees it already ordered units to defend a position
- **Better decisions**: Can see if previous strategy worked or needs adjustment
- **Continuity**: Understands the tactical evolution, not just snapshots
- **Empty orders**: Can confidently return no orders when situation is stable

## Cost Savings Example

### Scenario: 100 API calls over 1 hour (objectives don't change)

**Without Caching**:
- 100 calls × 2600 input tokens = 260,000 tokens
- At $0.075 per 1M tokens = $0.0195

**With Caching**:
- 1st call: 2600 tokens (full price)
- 99 calls: 450 input + 2150 cached = 99 × (450 + 215) = 65,835 tokens
- Total effective cost: ~$0.0049

**Savings**: ~75% reduction in API costs

## Troubleshooting

### Cache Not Being Used

Check logs for:
- "Failed to create Gemini native cache" → Model may not support caching
- "GEMINI CACHE EXPIRED" → Cache refreshing normally
- "Retrying without cache" → API issue, fallback engaged

### High Token Usage

If cached_tokens = 0 in logs:
- Cache may not have been created
- Model might not support caching
- System prompt may be changing between calls

### Verify Caching

Look for these log patterns:
1. First call: "GEMINI NATIVE CACHE CREATED"
2. Subsequent calls: "Used Gemini NATIVE cache: cachedContents/..."
3. Token usage: "Cached tokens: XXXX (90% cost reduction!)"
