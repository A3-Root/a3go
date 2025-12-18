# BATCOM Debug & Testing Functions

Functions for testing, debugging, and monitoring BATCOM functionality.

Execute on **server only** from debug console.

---

## Core Testing

### `Root_fnc_testPythia` - Test Pythia Extension
Verifies Pythia extension is loaded and working.

```sqf
call Root_fnc_testPythia;
```

**Returns:** Test result string
**Purpose:** Confirms Python bridge is functional

**Example:**
```sqf
[] call Root_fnc_testPythia;
// Output: "Pythia extension test passed"
```

---

### `BATCOM_fnc_init` - Initialize BATCOM
Initializes BATCOM Python core with configuration.

```sqf
call BATCOM_fnc_init;
```

**Returns:** Hashmap with status, version, config
**Purpose:** Manual initialization (normally automatic on mission start)

---

### `BATCOM_fnc_debugInit` - Debug Initialization
Initializes BATCOM with verbose logging enabled.

```sqf
call BATCOM_fnc_debugInit;
```

**Returns:** Initialization result with detailed logs
**Purpose:** Troubleshoot initialization issues

---

### `Root_fnc_testGeminiConnection` - Test LLM Connection
Tests connection to configured LLM provider.

```sqf
call Root_fnc_testGeminiConnection;
```

**Returns:** Connection test result
**Purpose:** Verify API key and LLM connectivity
**Note:** Works with any provider despite "Gemini" in name

---

## Monitoring & Stats

### `Root_fnc_getTokenStats` - Get Token Usage
Returns cumulative LLM token usage statistics.

```sqf
call Root_fnc_getTokenStats;
```

**Returns:** Hashmap with:
- `input_tokens` (NUMBER): Total input tokens sent
- `output_tokens` (NUMBER): Total output tokens received
- `total_tokens` (NUMBER): Combined total
- `llm_calls` (NUMBER): Number of LLM API calls

**Example:**
```sqf
private _stats = call Root_fnc_getTokenStats;
systemChat format ["LLM calls: %1 | Tokens: %2",
    _stats get "llm_calls",
    _stats get "total_tokens"
];
```

---

### `BATCOM_fnc_isEnabled` - Check BATCOM Status
Checks if BATCOM is initialized and enabled.

```sqf
call BATCOM_fnc_isEnabled;
```

**Returns:** BOOL (true if enabled)

**Example:**
```sqf
if (call BATCOM_fnc_isEnabled) then {
    systemChat "BATCOM is running";
};
```

---

## Configuration Testing

### `Root_fnc_testInitConfig` - Test Config Loading
Tests configuration loading from config.cpp.

```sqf
call Root_fnc_testInitConfig;
```

**Returns:** Loaded configuration hashmap
**Purpose:** Verify CfgBATCOM settings are loaded correctly

---

## World State Inspection

### `BATCOM_fnc_worldScan` - Manual World Scan
Triggers immediate world state scan and sends to Python.

```sqf
call BATCOM_fnc_worldScan;
```

**Returns:** Snapshot hashmap
**Purpose:** Test world scanning, inspect current battlefield state

**Example:**
```sqf
private _snapshot = call BATCOM_fnc_worldScan;
systemChat format ["Groups scanned: %1", count (_snapshot get "groups")];
```

---

## Group & Player Scanning

### `BATCOM_fnc_scanGroups` - Scan Groups
Scans all groups on server and categorizes them.

```sqf
call BATCOM_fnc_scanGroups;
```

**Returns:** Array of group data hashmaps
**Purpose:** Inspect group detection and categorization

---

### `BATCOM_fnc_scanPlayers` - Scan Players
Scans all players on server.

```sqf
call BATCOM_fnc_scanPlayers;
```

**Returns:** Array of player data hashmaps
**Purpose:** Verify player detection

---

## Utility Functions

### `BATCOM_fnc_getGroupType` - Get Group Type
Determines tactical type of a group (infantry, armor, air, etc.).

```sqf
[GROUP] call BATCOM_fnc_getGroupType;
```

**Parameters:**
- `GROUP` (GROUP): Arma 3 group object

**Returns:** STRING - Type ("infantry", "motorized", "mechanized", "armor", "air_rotary", "air_fixed", "naval", "unknown")

**Example:**
```sqf
private _type = [group player] call BATCOM_fnc_getGroupType;
systemChat format ["Your group type: %1", _type];
```

---

### `BATCOM_fnc_getGroupId` - Get Group ID
Gets unique group identifier used by BATCOM.

```sqf
[GROUP] call BATCOM_fnc_getGroupId;
```

**Parameters:**
- `GROUP` (GROUP): Arma 3 group object

**Returns:** STRING - Unique group ID

**Example:**
```sqf
private _id = [group player] call BATCOM_fnc_getGroupId;
systemChat format ["Your group ID: %1", _id];
```

---

## Logging & Debug Output

### `BATCOM_fnc_logMessage` - Log Message
Logs message to both RPT and Python logs.

```sqf
[PREFIX, LEVEL, MESSAGE] call BATCOM_fnc_logMessage;
```

**Parameters:**
- `PREFIX` (STRING): Log prefix (e.g., "BATCOM")
- `LEVEL` (STRING): "INFO" | "WARN" | "ERROR" | "DEBUG"
- `MESSAGE` (STRING): Log message

**Example:**
```sqf
["BATCOM", "INFO", "Custom debug message"] call BATCOM_fnc_logMessage;
```

---

### `BATCOM_fnc_debugLog` - Debug Log
Shorthand for debug-level logging.

```sqf
[MESSAGE] call BATCOM_fnc_debugLog;
```

**Parameters:**
- `MESSAGE` (STRING): Debug message

**Example:**
```sqf
["Testing commander deployment"] call BATCOM_fnc_debugLog;
```

---

## Complete Debug Workflow

```sqf
// 1. Verify Pythia is working
call Root_fnc_testPythia;

// 2. Check BATCOM initialization
if !(call BATCOM_fnc_isEnabled) then {
    // Force initialization with debug output
    call BATCOM_fnc_debugInit;
};

// 3. Verify configuration loaded
private _config = call Root_fnc_testInitConfig;
systemChat format ["Config loaded: %1 keys", count _config];

// 4. Test LLM connection
call Root_fnc_testGeminiConnection;

// 5. Scan current world state
private _snapshot = call BATCOM_fnc_worldScan;
systemChat format ["Groups: %1 | Players: %2",
    count (_snapshot get "groups"),
    count (_snapshot get "players")
];

// 6. Check token usage
private _tokens = call Root_fnc_getTokenStats;
systemChat format ["Token usage: %1 (calls: %2)",
    _tokens get "total_tokens",
    _tokens get "llm_calls"
];

// 7. Inspect your group
private _myType = [group player] call BATCOM_fnc_getGroupType;
private _myId = [group player] call BATCOM_fnc_getGroupId;
systemChat format ["Your group: %1 (type: %2)", _myId, _myType];
```

---

## Log File Locations

- **Arma RPT logs**: `%LOCALAPPDATA%\Arma 3\` or Arma 3 server logs directory
- **BATCOM Python logs**: `@BATCOM/logs/batcom_YYYYMMDD_HHMMSS.log`
- **Token usage**: `@BATCOM/token_usage.json`

---

## Common Debug Scenarios

### LLM Not Responding
```sqf
// 1. Check if BATCOM is running
call BATCOM_fnc_isEnabled;  // Should return true

// 2. Test LLM connection
call Root_fnc_testGeminiConnection;

// 3. Check token stats (should increment)
call Root_fnc_getTokenStats;

// 4. Check Python logs in @BATCOM/logs/
```

### Groups Not Being Controlled
```sqf
// 1. Scan groups and check detection
private _snapshot = call BATCOM_fnc_worldScan;
private _groups = _snapshot get "groups";

// 2. Check your group's classification
{
    systemChat format ["Group %1: side=%2, controlled=%3",
        _x get "id",
        _x get "side",
        _x get "is_controlled"
    ];
} forEach _groups;

// 3. Verify controlled sides are set
// Should be set via ["commanderSides", [east], nil] call Root_fnc_batcomInit;
```

### Initialization Failures
```sqf
// 1. Debug init with verbose output
call BATCOM_fnc_debugInit;

// 2. Test Pythia separately
call Root_fnc_testPythia;

// 3. Check if Python imports work
private _result = ["python", ["import sys; sys.path.insert(0, '..'); from batcom import api; print('API import OK')"]] call py3_fnc_callExtension;
```
