# AO Tracking and Post-Mission Analysis

## Overview

BATCOM now tracks complete AO (Area of Operations) history including:
- **All orders issued** by the LLM commander with timestamps
- **Tactical commentary** explaining the reasoning behind each decision
- **Active objectives** at the time of each decision
- **Complete API call logs** with request/response data for debugging

This data enables:
1. **Post-mission analysis** - LLM can review its own performance and learn
2. **Debugging** - Complete audit trail of all decisions and API calls
3. **Performance metrics** - Track effectiveness across multiple AOs

## File Structure

### Order History (In-Memory)
Stored in `StateManager.ao_orders` for the current AO:
```python
{
    'cycle': 5,
    'mission_time': 150.5,
    'timestamp': 1733456789.123,
    'order_count': 8,
    'orders': [
        {'type': 'defend_area', 'group_id': 'GRP_EAST_1', ...},
        {'type': 'seek_and_destroy', 'group_id': 'GRP_EAST_2', ...},
        ...
    ],
    'commentary': 'Deploying forces to defend HVT. Enemy approaching from north.',
    'objectives': [
        {'id': 'OBJ_RUNTIME_1', 'description': 'Defend HVT', ...}
    ]
}
```

### API Call Logs (Files)
Stored in `@BATCOM/` directory with format:
```
apicall.<mapname>.<missionname>.<ao_number>.<timestamp>.log
```

Example:
```
apicall.Altis.Defend_Base.1.20251205_143022.log
```

## Usage

### Starting an AO

When starting a new AO, initialize tracking:

```python
# In your mission init
state_manager.start_ao(
    ao_id="AO_RUNTIME_1",
    map_name="Altis",
    mission_name="Defend_Base",
    ao_number=1
)

# Also start commander tracking for API logs
commander.start_ao_tracking(
    ao_id="AO_RUNTIME_1",
    map_name="Altis",
    mission_name="Defend_Base",
    ao_number=1
)
```

### During AO

Orders are automatically tracked as the commander issues them:
- Each decision cycle records orders with commentary
- API calls are logged to the dedicated log file
- All data timestamped for timeline reconstruction

### Ending an AO

When AO completes, finalize tracking:

```python
# End commander tracking (closes API log file)
commander.end_ao_tracking()

# End state tracking (triggers analysis)
ao_data = state_manager.end_ao()

# ao_data now contains complete history for analysis
```

### Retrieving AO Data

Get complete AO data for post-mission analysis:

```python
analysis_data = state_manager.get_ao_analysis_data()

# Returns:
{
    'metadata': {
        'ao_id': 'AO_RUNTIME_1',
        'map_name': 'Altis',
        'mission_name': 'Defend_Base',
        'ao_number': 1,
        'start_time': 1733456789.0
    },
    'objectives_summary': [
        {
            'id': 'OBJ_RUNTIME_1',
            'description': 'Defend HVT at position [15931, 17067]',
            'state': 'COMPLETED',
            'priority': 100
        }
    ],
    'orders_history': [
        # All orders with commentary (see structure above)
    ],
    'total_cycles': 15,
    'total_orders_issued': 47
}
```

## API Call Log Format

Each API call log file contains:

### Header
```
================================================================================
API CALL LOG - AO: AO_RUNTIME_1
================================================================================
Map: Altis
Mission: Defend_Base
AO Number: 1
Started: 2025-12-05T14:30:22.123456
================================================================================
```

### Each API Call
```
================================================================================
API CALL #1 - REQUEST
================================================================================
Timestamp: 2025-12-05T14:30:25.456789
Cycle: 1
Mission Time: 30.5s
Provider: gemini
Model: gemini-2.5-flash-lite
--------------------------------------------------------------------------------
REQUEST DATA:
{
  "cached_context_length": 2850,
  "world_state": {
    "mission_time": 30.5,
    "controlled_groups": [...],
    "enemy_groups": [...]
  },
  "mission_intent": "Defend HVT at position [15931, 17067]",
  "objectives_count": 1
}
--------------------------------------------------------------------------------

RESPONSE:
Timestamp: 2025-12-05T14:30:27.123456
Success: true
Latency: 1667.2ms
Token Usage:
  input_tokens: 450
  output_tokens: 320
  cached_tokens: 2150
--------------------------------------------------------------------------------
RESPONSE DATA:
{
  "orders": [
    {"type": "defend_area", "group_id": "GRP_EAST_1", "position": [15931, 17067, 0], "radius": 200},
    {"type": "deploy_asset", "side": "EAST", "asset_type": "infantry_squad", ...}
  ],
  "commentary": "Deploying defensive forces around HVT position. Enemy detected north."
}
================================================================================
```

### Footer
```
================================================================================
API CALL LOG COMPLETED
================================================================================
Total API Calls: 15
Ended: 2025-12-05T14:45:30.789012
================================================================================
```

## Post-Mission Analysis

After an AO completes, the data can be used for:

### 1. Performance Review
```python
ao_data = state_manager.end_ao()

# Review what the LLM decided at each cycle
for entry in ao_data['orders_history']:
    print(f"Cycle {entry['cycle']} @ T+{entry['mission_time']}s")
    print(f"Commentary: {entry['commentary']}")
    print(f"Orders: {entry['order_count']}")
```

### 2. LLM Self-Analysis

Send the complete AO data to the LLM for analysis:

```python
analysis_prompt = f"""
You were the tactical commander for this AO. Review your performance:

MISSION: {ao_data['metadata']['mission_name']}
MAP: {ao_data['metadata']['map_name']}

OBJECTIVES:
{json.dumps(ao_data['objectives_summary'], indent=2)}

YOUR DECISIONS:
{json.dumps(ao_data['orders_history'], indent=2)}

Analyze:
1. Did you achieve the objectives? Why or why not?
2. Were your tactical decisions sound?
3. What could you have done better?
4. What did you learn for future AOs?
"""

# Send to LLM for self-reflection
```

### 3. Debugging

Use the API call logs to debug:
- Why a specific decision was made
- What data the LLM saw at each cycle
- Token usage and caching effectiveness
- Response latencies and errors

### 4. Metrics

Track performance across multiple AOs:
- Average orders per cycle
- Decision cycle durations
- Token usage trends
- Success rates by mission type

## Benefits

### For the LLM
- **Memory across missions**: Learn from previous AOs
- **Self-improvement**: Analyze mistakes and successes
- **Context awareness**: See patterns in decision-making

### For Developers
- **Complete audit trail**: Know exactly what happened and why
- **Debugging**: Trace issues through complete API logs
- **Performance tuning**: Optimize prompts and caching

### For Mission Designers
- **Mission validation**: Ensure scenarios work as intended
- **Balance testing**: See if AI makes sensible decisions
- **Narrative review**: Check if tactics match mission intent

## Example: Complete AO Lifecycle

```python
# Mission starts
state_manager.start_ao("AO_1", "Altis", "Defend_Base", 1)
commander.start_ao_tracking("AO_1", "Altis", "Defend_Base", 1)

# Add objectives
state_manager.add_objective(defend_hvt_objective)

# Mission runs (commander makes decisions automatically)
# - Orders tracked with commentary
# - API calls logged to file

# Mission ends
commander.end_ao_tracking()  # Closes API log
ao_data = state_manager.end_ao()  # Gets complete data

# Analyze
print(f"AO completed: {ao_data['total_cycles']} cycles")
print(f"Orders issued: {ao_data['total_orders_issued']}")
print(f"API log: {commander.api_logger.get_log_file_path()}")

# Use for next AO
# LLM can review ao_data to improve future performance
```

## File Locations

- **API Call Logs**: `@BATCOM/apicall.*.log`
- **Token Usage Logs**: `@BATCOM/token_usage_*.json` (existing)
- **Main Logs**: Standard Python logging to `@BATCOM/batcom.log`

## SQF Integration

Example SQF code to start/end AO tracking:

```sqf
// Start AO
["startAO", ["AO_RUNTIME_1", "Altis", "Defend_Base", 1]] call Root_fnc_batcomAO;

// During mission - tracking happens automatically

// End AO
["endAO"] call Root_fnc_batcomAO;

// Get analysis data
private _aoData = ["getAnalysisData"] call Root_fnc_batcomAO;
```

## Notes

- API logs are **append-only** - never overwrite mid-mission
- Logs use **UTF-8 encoding** for international characters
- Timestamps are **ISO 8601 format** for easy parsing
- File names are **filesystem-safe** (no special characters)
- Logs are **human-readable JSON** for easy review
