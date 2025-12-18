# BATCOM Quick Start Guide

Minimal steps to get BATCOM running in your mission.

---

## Prerequisites

1. **Pythia Extension** installed in Arma 3
2. **@BATCOM addon** loaded on server
3. **Python dependencies** installed via Pythia's `install_requirements.bat`
4. **LLM API key** (Gemini, OpenAI, Claude, etc.)

---

## 5-Step Setup

### 1. Server Startup
Ensure `@BATCOM` is loaded:
```
-serverMod=@Pythia;@BATCOM
```

### 2. Mission Init (init.sqf or debug console)
```sqf
// Wait for BATCOM to initialize (automatic on mission start)
waitUntil {call BATCOM_fnc_isEnabled};

// Configure LLM provider and API key
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],              // or "openai", "claude", etc.
    ["api_key", "YOUR_API_KEY_HERE"],
    ["model", "gemini-2.0-flash-lite"],  // optional
    ["rate_limit", 12]                   // requests per minute, optional
], true] call Root_fnc_batcomInit;
```

### 3. Set Mission Brief
```sqf
["commanderBrief", "YOUR MISSION DESCRIPTION FROM AI PERSPECTIVE", true] call Root_fnc_batcomInit;
```

**Example:**
```sqf
["commanderBrief", "Defend the airfield at grid 1234-5678 against CSAT assault. Prevent enemy from capturing the control tower.", true] call Root_fnc_batcomInit;
```

### 4. Configure Factions
```sqf
// Set which sides are friendly (won't be attacked)
["commanderAllies", ["EAST", "GUER"], nil] call Root_fnc_batcomInit;

// Set which sides AI can command
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;
```

### 5. Deploy Commander
```sqf
// Start AI decision loop
["deployCommander", true] call Root_fnc_batcomInit;
```

---

## Complete Minimal Example

**Copy-paste into debug console (server exec):**

```sqf
// 1. Wait for init
waitUntil {call BATCOM_fnc_isEnabled};

// 2. Configure LLM (replace YOUR_API_KEY)
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_API_KEY_HERE"]
], true] call Root_fnc_batcomInit;

// 3. Set mission
["commanderBrief", "Defend position at grid 5000-5000 from enemy forces", true] call Root_fnc_batcomInit;

// 4. Set factions
["commanderAllies", ["EAST"], nil] call Root_fnc_batcomInit;
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;

// 5. Deploy
["deployCommander", true] call Root_fnc_batcomInit;

// Confirmation
systemChat "BATCOM deployed - AI is now active";
```

---

## Verification

Check if AI is working:

```sqf
// Monitor token usage (should increment as AI makes decisions)
call Root_fnc_getTokenStats;

// Inspect world state
private _snapshot = call BATCOM_fnc_worldScan;
systemChat format ["BATCOM sees %1 groups", count (_snapshot get "groups")];
```

---

## Optional: Set AO Bounds

Restrict AI operations to specific area:

```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_bounds", createHashMapFromArray [
        ["center", [5000, 5000]],  // Map coordinates
        ["radius", 2000],          // Meters
        ["type", "circle"]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Optional: Configure Resource Pool

Define assets AI can deploy:

```sqf
["commanderGuardrails", createHashMapFromArray [
    ["resource_pool", createHashMapFromArray [
        ["EAST", createHashMapFromArray [
            ["infantry_squad", createHashMapFromArray [
                ["classnames", ["O_Soldier_F", "O_Soldier_AR_F", "O_Soldier_GL_F"]],
                ["max", 3]  // Maximum 3 squads
            ]],
            ["attack_heli", createHashMapFromArray [
                ["classnames", ["O_Heli_Attack_02_dynamicLoadout_F"]],
                ["max", 1]  // Maximum 1 helicopter
            ]]
        ]]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Stopping AI

```sqf
["deployCommander", false] call Root_fnc_batcomInit;
```

Or permanently disable:
```sqf
call BATCOM_fnc_shutdown;
```

---

## Troubleshooting

### "BATCOM is not initialized"
```sqf
// Force initialization
call BATCOM_fnc_debugInit;
```

### "LLM not responding"
```sqf
// Test LLM connection
call Root_fnc_testGeminiConnection;

// Check API key is set
call Root_fnc_getTokenStats;  // Should show provider info in logs
```

### "No groups being controlled"
Check controlled sides are correct:
```sqf
private _snapshot = call BATCOM_fnc_worldScan;
{
    systemChat format ["Group %1: side=%2, controlled=%3",
        _x get "id",
        _x get "side",
        _x get "is_controlled"
    ];
} forEach (_snapshot get "groups");
```

---

## Logs

- **Arma RPT**: Standard Arma 3 logs location
- **Python logs**: `@BATCOM/logs/batcom_YYYYMMDD.log`
- **Token usage**: `@BATCOM/token_usage.json`

---

## Next Steps

- See `admin-commands.md` for all available commands
- See `debug-functions.md` for debugging tools
- Check `@BATCOM/logs/` for detailed AI decision logs
