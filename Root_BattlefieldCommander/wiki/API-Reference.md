# API Reference

Complete reference documentation for all BATCOM APIs, including SQF functions, Python APIs, and Pythia extension calls. The order of APIs documented is random. Please read them carefully before executing them as some APIs functions have no use when executed outside of its context function, while others are used a lot.

## Table of Contents

- [SQF Functions](#sqf-functions)
  - [Initialization Functions](#initialization-functions)
  - [Commander Control Functions](#commander-control-functions)
  - [Command Application Functions](#command-application-functions)
  - [World Scanning Functions](#world-scanning-functions)
  - [Group Management Functions](#group-management-functions)
  - [Debug & Testing Functions](#debug--testing-functions)
- [Python API (via Pythia)](#python-api-via-pythia)
  - [Core Functions](#core-functions)
  - [Admin Commands](#admin-commands)
- [Configuration Reference](#configuration-reference)
- [Data Structures](#data-structures)

---

## SQF Functions

All BATCOM functions are either prefixed with `Root_fnc_` or `BATCOM_fnc_`. Please be very careful as to what prefix is being used as `Root_fnc_init` is NOT the same as `BATCOM_fnc_init`.

### Initialization Functions

#### `BATCOM_fnc_init`

Initialize BATCOM systems on server start.

**Location**: `addons/main/functions/fn_init.sqf`

**Syntax**:
```sqf
call BATCOM_fnc_init;
```

**Parameters**: None

**Returns**: Nothing

**Description**:
- Initializes BATCOM namespace (`missionNamespace setVariable ["BATCOM", createHashMap]`)
- Sets up configuration from CfgBATCOM
- Initializes Pythia extension
- Configures logging levels
- Sets up global variables
- Called automatically on server via XEH_postInit

**Example**:
```sqf
// Automatically called on server start
// Manual call:
call Root_fnc_init;
```

---

#### `Root_fnc_batcomInit`

Main admin command handler for BATCOM configuration and control.

**Location**: `addons/main/functions/fn_batcomInit.sqf`

**Syntax**:
```sqf
[command, params, flag] call Root_fnc_batcomInit;
```

**Parameters**:
1. `command` (STRING) - Command name
2. `params` (ANY) - Command parameters (varies by command)
3. `flag` (BOOL or nil) - Optional flag for certain commands

**Returns**: Varies by command

**Supported Commands**:

##### `commanderBrief`
Set mission intent/description for the AI.

```sqf
["commanderBrief", "Defend the airfield from CSAT assault", true] call Root_fnc_batcomInit;
```

##### `commanderAllies`
Set friendly/allied sides.

```sqf
["commanderAllies", ["EAST"], nil] call Root_fnc_batcomInit;
```

##### `commanderSides`
Set controllable sides for the commander.

```sqf
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;
```

##### `commanderTask`
Add mission objectives/tasks.

```sqf
// Simple format
["commanderTask", [
    "Defend control tower at all costs",  // Description
    ["O_Soldier_F", "O_medic_F"],          // Relevant unit classes
    10                                      // Priority (0-10)
], nil] call Root_fnc_batcomInit;

// Advanced format (recommended)
["commanderTask", createHashMapFromArray [
    ["description", "Defend control tower at all costs"],
    ["priority", 10],
    ["position", [5234, 5678, 0]],
    ["radius", 150],
    ["task_type", "defend_area"],
    ["metadata", createHashMapFromArray [
        ["importance", "critical"],
        ["notes", "Command center for the entire AO"]
    ]]
], nil] call Root_fnc_batcomInit;
```

##### `deployCommander`
Start or stop the AI commander.

```sqf
// Start commander
["deployCommander", true] call Root_fnc_batcomInit;

// Stop commander
["deployCommander", false] call Root_fnc_batcomInit;
```

##### `setLLMConfig`
Configure LLM provider and settings.

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],              // Provider name
    ["api_key", "YOUR_API_KEY"],         // API key
    ["model", "gemini-2.5-flash-lite"],  // Optional: model name
    ["timeout", 30],                     // Optional: timeout in seconds
    ["min_interval", 10]                 // Optional: min seconds between calls
], true] call Root_fnc_batcomInit;
```

Supported providers:
- `gemini` - Google Gemini (default: `gemini-2.5-flash-lite`)
- `openai` - OpenAI GPT (default: `gpt-4o-mini`)
- `anthropic` - Anthropic Claude (default: `claude-3-5-sonnet-20241022`)
- `deepseek` - DeepSeek (default: `deepseek-chat`)
- `azure` - Azure OpenAI
- `local` - Local/custom endpoint

##### `setLLMApiKey`
Set API key for specific provider.

```sqf
["setLLMApiKey", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_API_KEY"]
], nil] call Root_fnc_batcomInit;
```

##### `setGeminiApiKey`
Legacy function to set Gemini API key (use `setLLMApiKey` instead).

```sqf
["setGeminiApiKey", "YOUR_API_KEY", nil] call Root_fnc_batcomInit;
```

##### `commanderControlGroups`
Override automatic group control.

```sqf
// Add specific groups to control
["commanderControlGroups", [group1, group2], "add"] call Root_fnc_batcomInit;

// Remove groups from control
["commanderControlGroups", [group3], "remove"] call Root_fnc_batcomInit;

// Set exact list of controlled groups
["commanderControlGroups", [group1, group2], "set"] call Root_fnc_batcomInit;

// Clear all controlled groups
["commanderControlGroups", [], "clear"] call Root_fnc_batcomInit;
```

##### `commanderGuardrails`
Set AO bounds and resource pools.

```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_center", [5000, 5000, 0]],      // AO center position
    ["ao_radius", 1500],                 // Radius in meters
    ["ao_shape", "circle"],              // "circle" or "rectangle"
    // For rectangle, add:
    // ["ao_width", 2000],
    // ["ao_height", 1500],
    ["resource_pool", createHashMapFromArray [
        ["EAST", createHashMapFromArray [
            ["infantry_squad", createHashMapFromArray [
                ["classnames", ["O_Soldier_F", "O_Soldier_F", "O_medic_F", "O_Soldier_AR_F"]],
                ["max", 3]  // Max 3 squads can be deployed
            ]],
            ["armor_platoon", createHashMapFromArray [
                ["classnames", ["O_MBT_02_cannon_F", "O_APC_Tracked_02_cannon_F"]],
                ["max", 1]
            ]]
        ]]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

### Commander Control Functions

#### `Root_fnc_deployCommander`

Deploy or undeploy the AI commander (internal implementation).

**Location**: `addons/main/functions/fn_deployCommander.sqf`

**Syntax**:
```sqf
deploy call Root_fnc_deployCommander;
```

**Parameters**:
1. `deploy` (BOOL) - true to start, false to stop

**Returns**: Nothing

**Description**:
- Starts/stops world scan loop
- Starts/stops command processing loop
- Notifies Python backend

**Example**:
```sqf
// Start commander
true call Root_fnc_deployCommander;

// Stop commander
false call Root_fnc_deployCommander;
```

---

### Command Application Functions

These functions apply tactical commands to groups.

#### `Root_fnc_applyMoveCommand`

Apply a move command to a group.

**Location**: `addons/main/functions/fn_applyMoveCommand.sqf`

**Syntax**:
```sqf
[group, position, waypoint_type] call Root_fnc_applyMoveCommand;
```

**Parameters**:
1. `group` (GROUP) - Target group
2. `position` (ARRAY) - Destination [x, y, z]
3. `waypoint_type` (STRING) - Waypoint type (default: "MOVE")

**Returns**: BOOL - Success

**Example**:
```sqf
[group player, [5000, 5000, 0], "MOVE"] call Root_fnc_applyMoveCommand;
```

---

#### `Root_fnc_applyDefendCommand`

Apply a defend command to a group.

**Location**: `addons/main/functions/fn_applyDefendCommand.sqf`

**Syntax**:
```sqf
[group, position, radius] call Root_fnc_applyDefendCommand;
```

**Parameters**:
1. `group` (GROUP) - Target group
2. `position` (ARRAY) - Defense position [x, y, z]
3. `radius` (NUMBER) - Defense radius in meters

**Returns**: BOOL - Success

**Example**:
```sqf
[group player, [5000, 5000, 0], 150] call Root_fnc_applyDefendCommand;
```

---

#### `Root_fnc_applyPatrolCommand`

Apply a patrol command to a group.

**Location**: `addons/main/functions/fn_applyPatrolCommand.sqf`

**Syntax**:
```sqf
[group, positions] call Root_fnc_applyPatrolCommand;
```

**Parameters**:
1. `group` (GROUP) - Target group
2. `positions` (ARRAY) - Array of patrol waypoints [[x,y,z], [x,y,z], ...]

**Returns**: BOOL - Success

**Example**:
```sqf
[group player, [
    [5000, 5000, 0],
    [5100, 5000, 0],
    [5100, 5100, 0],
    [5000, 5100, 0]
]] call Root_fnc_applyPatrolCommand;
```

---

#### `Root_fnc_applySeekCommand`

Apply a seek and destroy command to a group.

**Location**: `addons/main/functions/fn_applySeekCommand.sqf`

**Syntax**:
```sqf
[group, position, radius] call Root_fnc_applySeekCommand;
```

**Parameters**:
1. `group` (GROUP) - Target group
2. `position` (ARRAY) - Search area center [x, y, z]
3. `radius` (NUMBER) - Search radius in meters

**Returns**: BOOL - Success

**Example**:
```sqf
[group player, [5000, 5000, 0], 500] call Root_fnc_applySeekCommand;
```

---

#### `Root_fnc_applyDeployAssetCommand`

Deploy units from resource pool.

**Location**: `addons/main/functions/fn_applyDeployAssetCommand.sqf`

**Syntax**:
```sqf
[asset_type, side, position, classnames] call Root_fnc_applyDeployAssetCommand;
```

**Parameters**:
1. `asset_type` (STRING) - Asset identifier
2. `side` (SIDE) - Side to spawn for
3. `position` (ARRAY) - Spawn position [x, y, z]
4. `classnames` (ARRAY) - Array of unit classnames

**Returns**: GROUP or nil - Created group

**Example**:
```sqf
["infantry_squad", EAST, [5000, 5000, 0], ["O_Soldier_F", "O_Soldier_F", "O_medic_F"]] call Root_fnc_applyDeployAssetCommand;
```

---

#### `Root_fnc_applyTransportCommand`

Transport a group using vehicles.

**Location**: `addons/main/functions/fn_applyTransportCommand.sqf`

**Syntax**:
```sqf
[cargo_group, transport_group, destination] call Root_fnc_applyTransportCommand;
```

**Parameters**:
1. `cargo_group` (GROUP) - Group to be transported
2. `transport_group` (GROUP) - Vehicle group
3. `destination` (ARRAY) - Destination [x, y, z]

**Returns**: BOOL - Success

**Example**:
```sqf
[infGroup, heliGroup, [5000, 5000, 0]] call Root_fnc_applyTransportCommand;
```

---

#### `Root_fnc_applyEscortCommand`

Escort a high-value group.

**Location**: `addons/main/functions/fn_applyEscortCommand.sqf`

**Syntax**:
```sqf
[escort_group, protected_group] call Root_fnc_applyEscortCommand;
```

**Parameters**:
1. `escort_group` (GROUP) - Escorting group
2. `protected_group` (GROUP) - Group to protect

**Returns**: BOOL - Success

**Example**:
```sqf
[tankGroup, commanderGroup] call Root_fnc_applyEscortCommand;
```

---

#### `Root_fnc_applyFireSupportCommand`

Provide fire support to a position.

**Location**: `addons/main/functions/fn_applyFireSupportCommand.sqf`

**Syntax**:
```sqf
[fire_support_group, target_position] call Root_fnc_applyFireSupportCommand;
```

**Parameters**:
1. `fire_support_group` (GROUP) - Artillery/air group
2. `target_position` (ARRAY) - Target [x, y, z]

**Returns**: BOOL - Success

**Example**:
```sqf
[artilleryGroup, [5000, 5000, 0]] call Root_fnc_applyFireSupportCommand;
```

---

### World Scanning Functions

#### `BATCOM_fnc_worldScan`

Perform a complete world state scan.

**Location**: `addons/main/functions/fn_worldScan.sqf`

**Syntax**:
```sqf
call BATCOM_fnc_worldScan;
```

**Parameters**: None

**Returns**: Nothing

**Description**:
- Scans all units, groups, vehicles
- Collects player information
- Evaluates objective states
- Sends snapshot to Python backend
- Retrieves pending commands

**Example**:
```sqf
// Manual scan (normally called by loop)
call BATCOM_fnc_worldScan;
```

---

### Group Management Functions

#### `BATCOM_fnc_getGroupId`

Get unique identifier for a group.

**Location**: `addons/main/functions/fn_getGroupId.sqf`

**Syntax**:
```sqf
group call BATCOM_fnc_getGroupId;
```

**Parameters**:
1. `group` (GROUP) - Target group

**Returns**: STRING - Unique group ID (e.g., "B_Alpha_1_5")

**Example**:
```sqf
private _groupId = group player call BATCOM_fnc_getGroupId;
// Returns: "B_Alpha_1_5"
```

---

#### `BATCOM_fnc_getGroupType`

Classify group type based on units.

**Location**: `addons/main/functions/fn_getGroupType.sqf`

**Syntax**:
```sqf
group call BATCOM_fnc_getGroupType;
```

**Parameters**:
1. `group` (GROUP) - Target group

**Returns**: STRING - Group type

**Possible Return Values**:
- `"infantry"` - Infantry squad
- `"motorized"` - Infantry with light vehicles
- `"mechanized"` - IFVs/APCs
- `"armor"` - Tanks
- `"air"` - Helicopters/planes
- `"artillery"` - Artillery units
- `"support"` - Support/logistics units
- `"unknown"` - Cannot classify

**Example**:
```sqf
private _type = group player call BATCOM_fnc_getGroupType;
// Returns: "infantry"
```

---

### Debug & Testing Functions

#### `Root_fnc_testPythia`

Test Pythia extension connectivity.

**Location**: `addons/main/functions/fn_testPythia.sqf`

**Syntax**:
```sqf
call Root_fnc_testPythia;
```

**Parameters**: None

**Returns**: BOOL - true if working

**Example**:
```sqf
if (call Root_fnc_testPythia) then {
    systemChat "Pythia is working!";
};
```

---

#### `Root_fnc_testGeminiConnection`

Test LLM provider connectivity.

**Location**: `addons/main/functions/fn_testGeminiConnection.sqf`

**Syntax**:
```sqf
call Root_fnc_testGeminiConnection;
```

**Parameters**: None

**Returns**: STRING - Status message

**Example**:
```sqf
private _result = call Root_fnc_testGeminiConnection;
systemChat _result;
```

---

#### `BATCOM_fnc_debugInit`

Debug initialization status.

**Location**: `addons/main/functions/fn_debugInit.sqf`

**Syntax**:
```sqf
call BATCOM_fnc_debugInit;
```

**Parameters**: None

**Returns**: Nothing (prints to chat/log)

**Example**:
```sqf
call BATCOM_fnc_debugInit;
```

---

#### `BATCOM_fnc_isEnabled`

Check if commander is running.

**Syntax**:
```sqf
call BATCOM_fnc_isEnabled;
```

**Returns**: BOOL - true if running

**Example**:
```sqf
if (call BATCOM_fnc_isEnabled) then {
    systemChat "Commander is active";
};
```

---

#### `Root_fnc_getTokenStats`

Get token usage statistics.

**Syntax**:
```sqf
call Root_fnc_getTokenStats;
```

**Returns**: HASHMAP - Token usage data

**Example**:
```sqf
private _stats = call Root_fnc_getTokenStats;
systemChat format ["Tokens used: %1", _stats get "total_tokens"];
```

---

## Python API (via Pythia)

All Python functions are accessible from SQF via the Pythia extension:

```sqf
["batcom.function_name", [args]] call py3_fnc_callExtension;
```

### Core Functions

#### `init`

Initialize BATCOM Python backend.

**Python Location**: `batcom/api.py:init()`

**Syntax**:
```sqf
["batcom.init", [configArray]] call py3_fnc_callExtension;
```

**Parameters**:
1. `configArray` (ARRAY) - Configuration parameters

**Returns**: STRING - Status message

**Example**:
```sqf
private _config = [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
];
["batcom.init", [_config]] call py3_fnc_callExtension;
```

---

#### `shutdown`

Shutdown BATCOM Python backend.

**Python Location**: `batcom/api.py:shutdown()`

**Syntax**:
```sqf
["batcom.shutdown", []] call py3_fnc_callExtension;
```

**Parameters**: None

**Returns**: STRING - Status message

---

#### `is_initialized`

Check initialization status.

**Python Location**: `batcom/api.py:is_initialized()`

**Syntax**:
```sqf
["batcom.is_initialized", []] call py3_fnc_callExtension;
```

**Returns**: BOOL - Initialization status

---

#### `get_version`

Get BATCOM version.

**Python Location**: `batcom/api.py:get_version()`

**Syntax**:
```sqf
["batcom.get_version", []] call py3_fnc_callExtension;
```

**Returns**: STRING - Version string

---

#### `world_snapshot`

Process world state snapshot.

**Python Location**: `batcom/api.py:world_snapshot()`

**Syntax**:
```sqf
["batcom.world_snapshot", [snapshotData]] call py3_fnc_callExtension;
```

**Parameters**:
1. `snapshotData` (HASHMAP) - Complete world state

**Returns**: STRING - Processing status

**Description**: Sends current world state to Python backend for analysis and decision-making.

---

#### `get_pending_commands`

Retrieve commands from queue.

**Python Location**: `batcom/api.py:get_pending_commands()`

**Syntax**:
```sqf
["batcom.get_pending_commands", []] call py3_fnc_callExtension;
```

**Returns**: ARRAY - Array of command hashmaps

**Example**:
```sqf
private _commands = ["batcom.get_pending_commands", []] call py3_fnc_callExtension;
{
    private _cmd = _x;
    // Process command
} forEach _commands;
```

---

#### `batcom_init`

Handle admin commands.

**Python Location**: `batcom/api.py:batcom_init()`

**Syntax**:
```sqf
["batcom.batcom_init", [command, params, flag]] call py3_fnc_callExtension;
```

**Parameters**:
1. `command` (STRING) - Command name
2. `params` (ANY) - Command parameters
3. `flag` (BOOL) - Optional flag

**Returns**: Varies by command

---

#### `test_gemini_connection`

Test LLM connectivity.

**Python Location**: `batcom/api.py:test_gemini_connection()`

**Syntax**:
```sqf
["batcom.test_gemini_connection", []] call py3_fnc_callExtension;
```

**Returns**: STRING - Connection test result

---

## Configuration Reference

### CfgBATCOM Classes

Located in: `addons/main/config.cpp`

#### `CfgBATCOM >> logging`

```cpp
class logging {
    level = "INFO";           // DEBUG, INFO, WARN, ERROR
    arma_console = 0;         // 0 = disabled, 1 = enabled
};
```

#### `CfgBATCOM >> scan`

```cpp
class scan {
    tick = 2.0;               // World scan interval (seconds)
    ai_groups = 5.0;          // AI group scan interval
    players = 3.0;            // Player scan interval
    objectives = 5.0;         // Objective evaluation interval
};
```

#### `CfgBATCOM >> runtime`

```cpp
class runtime {
    max_messages_per_tick = 50;      // Max messages processed per tick
    max_commands_per_tick = 30;      // Max commands executed per tick
    max_controlled_groups = 500;     // Max groups under AI control
};
```

#### `CfgBATCOM >> ai`

```cpp
class ai {
    enabled = 1;                     // 0 = disabled, 1 = enabled
    provider = "gemini";             // Provider: gemini, openai, anthropic, deepseek, azure, local
    model = "gemini-2.5-flash-lite"; // Model identifier
    timeout = 30;                    // API timeout (seconds)
    min_interval = 30.0;             // Minimum seconds between LLM calls
};
```

#### `CfgBATCOM >> safety`

```cpp
class safety {
    sandbox_enabled = 1;                     // Enable command validation
    max_groups_per_objective = 500;          // Max groups per objective
    max_units_per_side = 500;                // Max spawned units per side
    allowed_commands[] = {                   // Command whitelist
        "move_to",
        "defend_area",
        "patrol_route",
        "seek_and_destroy",
        "transport_group",
        "escort_group",
        "fire_support",
        "deploy_asset"
    };
    blocked_commands[] = {};                 // Command blacklist
    audit_log = 1;                           // Enable audit logging
};
```

---

## Data Structures

### Command Structure

Commands returned from `get_pending_commands`:

```sqf
createHashMapFromArray [
    ["command_type", "move_to"],              // Command type
    ["group_id", "B_Alpha_1_5"],              // Target group ID
    ["parameters", createHashMapFromArray [   // Command-specific parameters
        ["position", [5000, 5000, 0]],
        ["waypoint_type", "MOVE"]
    ]],
    ["priority", 5],                          // Priority (0-10)
    ["timestamp", "2024-01-15T10:30:00"]     // ISO timestamp
]
```

### World Snapshot Structure

```sqf
createHashMapFromArray [
    ["timestamp", diag_tickTime],
    ["groups", [/* array of group data */]],
    ["players", [/* array of player data */]],
    ["objectives", [/* array of objectives */]],
    ["commander_state", createHashMapFromArray [
        ["is_deployed", true],
        ["controlled_sides", ["EAST"]],
        ["allied_sides", ["EAST"]]
    ]]
]
```

### Group Data Structure

```sqf
createHashMapFromArray [
    ["id", "B_Alpha_1_5"],
    ["side", "EAST"],
    ["position", [5000, 5000, 0]],
    ["heading", 180],
    ["speed", 10],
    ["unit_count", 8],
    ["group_type", "infantry"],
    ["is_in_combat", false],
    ["current_waypoint", [5100, 5100, 0]],
    ["units", [/* array of unit objects */]]
]
```

### Objective/Task Structure

```sqf
createHashMapFromArray [
    ["id", "obj_1"],
    ["description", "Defend the airfield"],
    ["priority", 10],
    ["position", [5000, 5000, 0]],
    ["radius", 200],
    ["task_type", "defend_area"],
    ["state", "active"],  // "active", "completed", "failed"
    ["metadata", createHashMapFromArray [/* optional metadata */]]
]
```

---

## Advanced Topics

### Custom LLM Providers

To add a custom provider, modify `batcom/config/guardrails.json`:

```json
{
    "provider": "custom",
    "model": "your-model-name",
    "endpoint": "https://your-endpoint.com/v1/chat/completions",
    "api_key": "your-key",
    "timeout": 30,
    "min_interval": 10,
    "rate_limit": 60,
    "max_input_tokens": 4096,
    "max_output_tokens": 2048
}
```

### Rate Limiting

Rate limits are enforced in `batcom/ai/providers.py`:
- Minimum interval between calls (default: 10s)
- Circuit breaker after 3 consecutive errors
- Automatic retry with exponential backoff

### Context Caching (Gemini)

Gemini's native caching reduces costs by 90%:
- System prompt cached for 1 hour
- Objectives and order history cached
- Automatic cache refresh before expiry
- Detailed token metrics in logs

See: `batcom/ai/providers.py:GeminiLLMClient`

---

## Function Index

Quick alphabetical index of all functions:

**A-D**
- `Root_fnc_applyDefendCommand` - Apply defend command
- `Root_fnc_applyDeployAssetCommand` - Deploy units
- `Root_fnc_applyEscortCommand` - Apply escort command
- `Root_fnc_applyFireSupportCommand` - Apply fire support
- `Root_fnc_applyMoveCommand` - Apply move command
- `Root_fnc_applyPatrolCommand` - Apply patrol command
- `Root_fnc_applySeekCommand` - Apply seek & destroy
- `Root_fnc_applyTransportCommand` - Apply transport
- `Root_fnc_batcomInit` - Main admin command handler
- `BATCOM_fnc_debugInit` - Debug initialization
- `Root_fnc_deployCommander` - Deploy/stop commander

**G-I**
- `BATCOM_fnc_getGroupId` - Get group unique ID
- `BATCOM_fnc_getGroupType` - Classify group type
- `Root_fnc_getTokenStats` - Get token usage stats
- `Root_fnc_init` - Initialize BATCOM
- `BATCOM_fnc_isEnabled` - Check if commander is running

**T-W**
- `Root_fnc_testGeminiConnection` - Test LLM connection
- `Root_fnc_testPythia` - Test Pythia extension
- `BATCOM_fnc_worldScan` - Perform world scan

---

## See Also

- [Command Reference](Command-Reference.md) - Detailed command documentation
- [LLM Configuration Guide](LLM-Configuration-Guide.md) - Configure AI providers
- [Mission Setup Guide](Mission-Setup-Guide.md) - Integrate into missions
- [Architecture Overview](Architecture-Overview.md) - System design

---

**Last Updated**: 2025-12-05
