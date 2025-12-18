# Mission Setup Guide

Complete guide to integrating BATCOM into your Arma 3 missions, from basic setup to advanced configurations.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Basic Mission Setup](#basic-mission-setup)
- [Configuring the AI Commander](#configuring-the-ai-commander)
- [Defining Objectives](#defining-objectives)
- [Advanced Configuration](#advanced-configuration)
- [Example Missions](#example-missions)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

BATCOM integrates into Arma 3 missions through a simple initialization API. The AI commander can be configured entirely through SQF scripting in your mission's init files.

### Integration Points

```
Mission Init
    ↓
1. Configure LLM
2. Set Mission Brief
3. Define Factions
4. Add Objectives
5. Set Constraints (Optional)
6. Deploy Commander
    ↓
AI Takes Control
```

---

## Prerequisites

Before integrating BATCOM:

1. **Server Requirements**
   - BATCOM mod installed: `@BATCOM`
   - CBA_A3 installed: `@CBA_A3`
   - Server running with mods: `-serverMod=@CBA_A3;@BATCOM`

2. **LLM Configuration**
   - Valid API key for chosen provider (Gemini recommended)
   - Internet connectivity from server

3. **Mission Requirements**
   - AI groups present (or resource pools configured for spawning)
   - Clear mission objectives
   - Defined AO boundaries (optional but recommended)

---

## Basic Mission Setup

### Step 1: Initialize in init.sqf

Create or edit `mission.sqm`'s `init.sqf`:

```sqf
// Wait for BATCOM to be ready
waitUntil {!isNil "Root_fnc_batcomInit"};

// Configure LLM provider
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_API_KEY"]
], true] call Root_fnc_batcomInit;

// Set mission intent
["commanderBrief", "Defend the island from invading forces", true] call Root_fnc_batcomInit;

// Define controlled and allied sides
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;
["commanderAllies", ["EAST"], nil] call Root_fnc_batcomInit;

// Add a basic objective
["commanderTask", createHashMapFromArray [
    ["description", "Defend the airfield"],
    ["priority", 10],
    ["position", getMarkerPos "obj_airfield"],
    ["radius", 300],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;

// Deploy the commander
["deployCommander", true] call Root_fnc_batcomInit;
```

### Step 2: Test the Setup

1. Load mission on dedicated server
2. Check RPT logs for BATCOM initialization
3. Observe AI behavior - groups should start receiving orders
4. Use debug command to verify: `call BATCOM_fnc_isEnabled;`

### Step 3: Monitor Performance

```sqf
// Add to debug console or script
[] spawn {
    while {call BATCOM_fnc_isEnabled} do {
        private _stats = call Root_fnc_getTokenStats;
        systemChat format ["AI Status: Active | Tokens: %1", _stats get "total_tokens"];
        sleep 60;
    };
};
```

---

## Configuring the AI Commander

### Setting Mission Context

The mission brief helps the AI understand the overall goal:

```sqf
["commanderBrief", "
    Mission: Operation Sentinel
    Objective: Defend Altis International Airport from CSAT assault
    Intel: Enemy forces approaching from the east with mechanized support
    Rules of Engagement: Weapons free, avoid civilian casualties
", true] call Root_fnc_batcomInit;
```

**Tips**:
- Be specific about mission goals
- Include relevant intel
- Mention constraints (ROE, civilian areas, etc.)
- Keep it concise (1-3 sentences ideal)

### Defining Sides

```sqf
// Set which sides the AI can control
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;

// Set allied sides (AI won't attack these)
["commanderAllies", ["EAST", "INDEPENDENT"], nil] call Root_fnc_batcomInit;
```

**Common Configurations**:

**NATO vs CSAT**:
```sqf
["commanderSides", ["WEST"], nil] call Root_fnc_batcomInit;
["commanderAllies", ["WEST"], nil] call Root_fnc_batcomInit;
```

**Multi-Faction**:
```sqf
["commanderSides", ["EAST", "INDEPENDENT"], nil] call Root_fnc_batcomInit;
["commanderAllies", ["EAST", "INDEPENDENT"], nil] call Root_fnc_batcomInit;
```

### Controlling Specific Groups

By default, BATCOM controls all AI groups of the specified sides. To override:

```sqf
// Only control specific groups
["commanderControlGroups", [group1, group2, group3], "set"] call Root_fnc_batcomInit;

// Add groups to existing control
["commanderControlGroups", [newGroup], "add"] call Root_fnc_batcomInit;

// Remove groups from control
["commanderControlGroups", [playerGroup], "remove"] call Root_fnc_batcomInit;

// Clear all and return to automatic
["commanderControlGroups", [], "clear"] call Root_fnc_batcomInit;
```

**Use Cases**:
- Exclude player-controlled groups
- Create scripted sequences for specific groups
- Gradually hand over control as mission progresses

---

## Defining Objectives

Objectives are the core of BATCOM's decision-making. The AI prioritizes tasks and allocates forces accordingly.

### Simple Format

Quick objective definition:

```sqf
["commanderTask", [
    "Description of the task",           // What to do
    ["O_Soldier_F", "O_MBT_02_cannon_F"], // Relevant units
    8                                     // Priority (0-10)
], nil] call Root_fnc_batcomInit;
```

**Example**:
```sqf
["commanderTask", [
    "Secure the communication tower",
    ["O_Soldier_F", "O_engineer_F"],
    7
], nil] call Root_fnc_batcomInit;
```

### Advanced Format (Recommended)

More control over objective parameters:

```sqf
["commanderTask", createHashMapFromArray [
    ["description", STRING],    // Task description (required)
    ["priority", NUMBER],        // 0-10, higher = more important (required)
    ["position", ARRAY],         // [x, y, z] location (optional)
    ["radius", NUMBER],          // Area radius in meters (optional)
    ["task_type", STRING],       // Task type hint (optional)
    ["metadata", HASHMAP]        // Additional context (optional)
], nil] call Root_fnc_batcomInit;
```

**Example**:
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Defend the command post at all costs"],
    ["priority", 10],
    ["position", [5234, 5678, 0]],
    ["radius", 150],
    ["task_type", "defend_area"],
    ["metadata", createHashMapFromArray [
        ["importance", "critical"],
        ["notes", "Primary HQ - loss means mission failure"],
        ["civilian_area", true]
    ]]
], nil] call Root_fnc_batcomInit;
```

### Task Types

Hint to the AI about the nature of the objective:

| Task Type | Description | Use Case |
|-----------|-------------|----------|
| `defend_area` | Static defense | Defend positions, bases, objectives |
| `attack_position` | Assault objective | Capture enemy positions |
| `patrol_route` | Active patrol | Reconnaissance, area control |
| `seek_and_destroy` | Offensive sweep | Eliminate enemy forces |
| `hold_position` | Defensive stance | Maintain current positions |
| `support` | Provide support | Backup other objectives |
| `ambush` | Ambush position | Roadside ambushes, traps |
| `recon` | Reconnaissance | Intel gathering |

### Priority System

Priority determines force allocation:

| Priority | Meaning | Force Allocation |
|----------|---------|------------------|
| 10 | Critical | Maximum resources |
| 7-9 | High | Significant resources |
| 4-6 | Medium | Balanced allocation |
| 1-3 | Low | Minimal resources |
| 0 | Optional | Only if resources available |

**Example**:
```sqf
// Critical: Defend HQ
["commanderTask", createHashMapFromArray [
    ["description", "Defend HQ"],
    ["priority", 10],
    ["position", getMarkerPos "hq"],
    ["radius", 200]
], nil] call Root_fnc_batcomInit;

// High: Secure supply route
["commanderTask", createHashMapFromArray [
    ["description", "Secure supply route"],
    ["priority", 7],
    ["position", getMarkerPos "route_1"],
    ["radius", 500]
], nil] call Root_fnc_batcomInit;

// Medium: Patrol perimeter
["commanderTask", createHashMapFromArray [
    ["description", "Patrol outer perimeter"],
    ["priority", 5],
    ["position", getMarkerPos "perimeter"],
    ["radius", 1000],
    ["task_type", "patrol_route"]
], nil] call Root_fnc_batcomInit;
```

### Dynamic Objectives

Add objectives during mission:

```sqf
// Trigger-based objective
trigger1 setTriggerStatements [
    "blufor in thislist",
    "
        ['commanderTask', createHashMapFromArray [
            ['description', 'Enemy reinforcements detected - eliminate them'],
            ['priority', 8],
            ['position', getMarkerPos 'enemy_spawn'],
            ['radius', 400],
            ['task_type', 'seek_and_destroy']
        ], nil] call Root_fnc_batcomInit;
    ",
    ""
];
```

---

## Advanced Configuration

### Setting AO Boundaries

Constrain AI operations to specific area:

```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_center", [5000, 5000, 0]],     // Center of AO
    ["ao_radius", 2000],                // Radius in meters
    ["ao_shape", "circle"]              // "circle" or "rectangle"
], nil] call Root_fnc_batcomInit;
```

**Rectangle AO**:
```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_center", [5000, 5000, 0]],
    ["ao_width", 3000],
    ["ao_height", 2000],
    ["ao_shape", "rectangle"]
], nil] call Root_fnc_batcomInit;
```

**From Marker**:
```sqf
private _markerPos = getMarkerPos "ao_main";
private _markerSize = getMarkerSize "ao_main";

["commanderGuardrails", createHashMapFromArray [
    ["ao_center", _markerPos],
    ["ao_width", (_markerSize select 0) * 2],
    ["ao_height", (_markerSize select 1) * 2],
    ["ao_shape", "rectangle"]
], nil] call Root_fnc_batcomInit;
```

### Resource Pools

Define specific assets the AI can deploy:

```sqf
["commanderGuardrails", createHashMapFromArray [
    ["resource_pool", createHashMapFromArray [
        ["EAST", createHashMapFromArray [
            // Infantry squad
            ["infantry_squad", createHashMapFromArray [
                ["classnames", [
                    "O_Soldier_TL_F",
                    "O_Soldier_F",
                    "O_Soldier_F",
                    "O_Soldier_AR_F",
                    "O_medic_F",
                    "O_engineer_F"
                ]],
                ["max", 5]  // Can deploy up to 5 squads
            ]],

            // Armor platoon
            ["armor_platoon", createHashMapFromArray [
                ["classnames", [
                    "O_MBT_02_cannon_F",
                    "O_MBT_02_cannon_F"
                ]],
                ["max", 2]  // Can deploy up to 2 platoons
            ]],

            // Air support
            ["air_support", createHashMapFromArray [
                ["classnames", [
                    "O_Heli_Attack_02_dynamicLoadout_F"
                ]],
                ["max", 1]
            ]],

            // Recon team
            ["recon_team", createHashMapFromArray [
                ["classnames", [
                    "O_recon_TL_F",
                    "O_recon_M_F",
                    "O_recon_F",
                    "O_recon_LAT_F"
                ]],
                ["max", 3]
            ]]
        ]]
    ]]
], nil] call Root_fnc_batcomInit;
```

**Notes**:
- Asset names are arbitrary - choose descriptive names
- `max` limits how many of each asset type can be active
- AI will request deployments via `deploy_asset` command
- Total units still limited by `max_units_per_side` (default: 500)

### Spawn Limits

Configure maximum units and groups:

**In config.cpp**:
```cpp
class safety {
    max_units_per_side = 500;           // Total units per side
    max_controlled_groups = 500;        // Total groups under control
    max_groups_per_objective = 500;     // Groups per objective
};
```

**Runtime override** (if implemented):
```sqf
BATCOM setVariable ["max_units_per_side", 300];
BATCOM setVariable ["max_controlled_groups", 50];
```

### Decision Timing

Control how often the AI makes decisions:

**In config.cpp**:
```cpp
class ai {
    min_interval = 30.0;  // Minimum 30 seconds between LLM calls
};
```

**Runtime**:
```sqf
// Faster decisions (more API calls, higher cost)
BATCOM setVariable ["ai_min_interval", 15];

// Slower decisions (fewer API calls, lower cost)
BATCOM setVariable ["ai_min_interval", 60];
```

**Trade-offs**:
- **Faster (15-30s)**: More responsive, higher cost
- **Balanced (30-45s)**: Good responsiveness, moderate cost
- **Slower (60s+)**: Less responsive, lower cost

### Command Filtering

Restrict which commands the AI can use:

**In config.cpp**:
```cpp
class safety {
    allowed_commands[] = {
        "move_to",
        "defend_area",
        "patrol_route"
        // Disable: seek_and_destroy, deploy_asset, etc.
    };
    blocked_commands[] = {
        "deploy_asset"  // Explicitly block specific commands
    };
};
```

**Use Cases**:
- Limit AI to defensive tactics only
- Prevent unit spawning
- Force specific tactical behaviors

---

## Example Missions

### Example 1: Basic Defense

Simple defensive mission with static objectives:

```sqf
// init.sqf
waitUntil {!isNil "Root_fnc_batcomInit"};

// Configure AI
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
], true] call Root_fnc_batcomInit;

["commanderBrief", "Defend the airfield from enemy assault", true] call Root_fnc_batcomInit;
["commanderSides", ["WEST"], nil] call Root_fnc_batcomInit;
["commanderAllies", ["WEST"], nil] call Root_fnc_batcomInit;

// Primary objective: Defend control tower
["commanderTask", createHashMapFromArray [
    ["description", "Defend the control tower"],
    ["priority", 10],
    ["position", getMarkerPos "tower"],
    ["radius", 150],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;

// Secondary: Defend hangar
["commanderTask", createHashMapFromArray [
    ["description", "Defend aircraft hangars"],
    ["priority", 7],
    ["position", getMarkerPos "hangar"],
    ["radius", 200],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;

// Tertiary: Patrol perimeter
["commanderTask", createHashMapFromArray [
    ["description", "Patrol airfield perimeter"],
    ["priority", 4],
    ["position", getMarkerPos "airfield"],
    ["radius", 800],
    ["task_type", "patrol_route"]
], nil] call Root_fnc_batcomInit;

// Set AO bounds
["commanderGuardrails", createHashMapFromArray [
    ["ao_center", getMarkerPos "airfield"],
    ["ao_radius", 1500]
], nil] call Root_fnc_batcomInit;

// Deploy
["deployCommander", true] call Root_fnc_batcomInit;
```

### Example 2: Offensive Operations

Attack mission with dynamic objectives:

```sqf
// init.sqf
waitUntil {!isNil "Root_fnc_batcomInit"};

["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
], true] call Root_fnc_batcomInit;

["commanderBrief", "
    Assault enemy positions and secure the town.
    Priority: Minimize civilian casualties.
", true] call Root_fnc_batcomInit;

["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;
["commanderAllies", ["EAST"], nil] call Root_fnc_batcomInit;

// Phase 1: Secure approach
["commanderTask", createHashMapFromArray [
    ["description", "Clear enemy defenses on approach road"],
    ["priority", 9],
    ["position", getMarkerPos "approach"],
    ["radius", 400],
    ["task_type", "seek_and_destroy"]
], nil] call Root_fnc_batcomInit;

// Phase 2: Assault town
["commanderTask", createHashMapFromArray [
    ["description", "Assault and secure the town square"],
    ["priority", 10],
    ["position", getMarkerPos "town_square"],
    ["radius", 300],
    ["task_type", "attack_position"],
    ["metadata", createHashMapFromArray [
        ["civilian_area", true]
    ]]
], nil] call Root_fnc_batcomInit;

// Phase 3: Secure flanks
["commanderTask", createHashMapFromArray [
    ["description", "Secure eastern flank"],
    ["priority", 6],
    ["position", getMarkerPos "flank_east"],
    ["radius", 500],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;

// Configure resource pool for reinforcements
["commanderGuardrails", createHashMapFromArray [
    ["ao_center", getMarkerPos "ao_center"],
    ["ao_radius", 2500],
    ["resource_pool", createHashMapFromArray [
        ["EAST", createHashMapFromArray [
            ["infantry_reinforcement", createHashMapFromArray [
                ["classnames", [
                    "O_Soldier_TL_F", "O_Soldier_F", "O_Soldier_F",
                    "O_Soldier_AR_F", "O_medic_F", "O_Soldier_LAT_F"
                ]],
                ["max", 3]
            ]],
            ["armor_support", createHashMapFromArray [
                ["classnames", ["O_APC_Tracked_02_cannon_F"]],
                ["max", 2]
            ]]
        ]]
    ]]
], nil] call Root_fnc_batcomInit;

["deployCommander", true] call Root_fnc_batcomInit;
```

### Example 3: Dynamic Mission with Triggers

Objectives added based on mission progression:

```sqf
// init.sqf
waitUntil {!isNil "Root_fnc_batcomInit"};

["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
], true] call Root_fnc_batcomInit;

["commanderBrief", "Patrol the region and respond to threats", true] call Root_fnc_batcomInit;
["commanderSides", ["INDEPENDENT"], nil] call Root_fnc_batcomInit;
["commanderAllies", ["INDEPENDENT", "WEST"], nil] call Root_fnc_batcomInit;

// Initial patrol objective
["commanderTask", createHashMapFromArray [
    ["description", "Patrol main highway"],
    ["priority", 5],
    ["position", getMarkerPos "highway"],
    ["radius", 1000],
    ["task_type", "patrol_route"]
], nil] call Root_fnc_batcomInit;

["deployCommander", true] call Root_fnc_batcomInit;

// Trigger: Enemy contact
trigger_contact setTriggerStatements [
    "EAST countSide thisList > 0",
    "
        ['commanderTask', createHashMapFromArray [
            ['description', 'Enemy contact detected - neutralize threat'],
            ['priority', 9],
            ['position', getPos thisTrigger],
            ['radius', 600],
            ['task_type', 'seek_and_destroy']
        ], nil] call Root_fnc_batcomInit;

        hint 'AI Commander: New objective - Enemy contact!';
    ",
    ""
];

// Trigger: Civilian rescue
trigger_civrescue setTriggerStatements [
    "civilian in thisList",
    "
        ['commanderTask', createHashMapFromArray [
            ['description', 'Evacuate civilians from danger zone'],
            ['priority', 10],
            ['position', getPos thisTrigger],
            ['radius', 300],
            ['task_type', 'defend_area'],
            ['metadata', createHashMapFromArray [
                ['civilian_evacuation', true]
            ]]
        ], nil] call Root_fnc_batcomInit;

        hint 'AI Commander: Priority - Civilian evacuation!';
    ",
    ""
];
```

### Example 4: Multi-Commander Setup

Multiple AI commanders for different factions:

```sqf
// init.sqf - Run on server only
if (!isServer) exitWith {};

waitUntil {!isNil "Root_fnc_batcomInit"};

// NOTE: Current BATCOM version supports single commander
// This is a conceptual example for future multi-commander support

// Configure LLM (shared)
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
], true] call Root_fnc_batcomInit;

// BLUFOR Commander
["commanderBrief", "NATO forces: Defend the island", true] call Root_fnc_batcomInit;
["commanderSides", ["WEST"], nil] call Root_fnc_batcomInit;
["commanderAllies", ["WEST"], nil] call Root_fnc_batcomInit;

["commanderTask", createHashMapFromArray [
    ["description", "Defend main base"],
    ["priority", 10],
    ["position", getMarkerPos "blufor_base"],
    ["radius", 500]
], nil] call Root_fnc_batcomInit;

// OPFOR would need separate instance (not yet supported)
// Future: ["deployCommander", "WEST"] call Root_fnc_batcomInit;

["deployCommander", true] call Root_fnc_batcomInit;
```

---

## Best Practices

### 1. Clear Mission Briefs

**Good**:
```sqf
["commanderBrief", "Defend the communications relay from enemy assault. Priority: Prevent destruction of relay equipment.", true] call Root_fnc_batcomInit;
```

**Bad**:
```sqf
["commanderBrief", "Do stuff with the thing", true] call Root_fnc_batcomInit;
```

### 2. Prioritize Objectives Carefully

Use the full 0-10 range:
- **10**: Mission-critical objectives
- **7-9**: Important but not critical
- **4-6**: Standard objectives
- **1-3**: Nice-to-have
- **0**: Optional

### 3. Set Realistic AO Bounds

```sqf
// Too large - AI has too much area to manage
["ao_radius", 10000]  // 10km radius

// Too small - AI feels constrained
["ao_radius", 200]    // 200m radius

// Just right - Focused AO
["ao_radius", 2000]   // 2km radius
```

### 4. Use Task Types

Always specify task_type when possible:
```sqf
["task_type", "defend_area"]  // Helps AI understand intent
```

### 5. Provide Context in Metadata

```sqf
["metadata", createHashMapFromArray [
    ["civilian_area", true],
    ["importance", "critical"],
    ["notes", "Radio tower - loss means communications blackout"]
]]
```

### 6. Test Configuration Before Mission

```sqf
// Test script
call Root_fnc_testGeminiConnection;
call BATCOM_fnc_debugInit;
```

### 7. Monitor During Development

```sqf
// Debug display
[] spawn {
    while {true} do {
        hintSilent format [
            "BATCOM Status\nEnabled: %1\nGroups: %2\nObjectives: %3",
            call BATCOM_fnc_isEnabled,
            count (BATCOM get "controlled_groups"),
            count (BATCOM get "objectives")
        ];
        sleep 5;
    };
};
```

### 8. Start Simple, Add Complexity

**Phase 1**: Basic setup with 1-2 objectives
**Phase 2**: Add dynamic objectives via triggers
**Phase 3**: Add resource pools and advanced constraints
**Phase 4**: Fine-tune priorities and timing

---

## Troubleshooting

### AI Not Moving Groups

**Check**:
```sqf
// Is commander enabled?
private _enabled = call BATCOM_fnc_isEnabled;
systemChat format ["Enabled: %1", _enabled];

// Are groups controlled?
private _groups = BATCOM get "controlled_groups";
systemChat format ["Controlled groups: %1", count _groups];

// Are objectives defined?
private _objs = BATCOM get "objectives";
systemChat format ["Objectives: %1", count _objs];
```

**Solutions**:
1. Verify commander is deployed: `["deployCommander", true] call Root_fnc_batcomInit;`
2. Check correct sides are set
3. Ensure groups exist and are AI-controlled
4. Verify objectives have positions and priorities

### LLM Connection Failing

```sqf
// Test connection
private _result = call Root_fnc_testGeminiConnection;
systemChat _result;
```

**Common Issues**:
- API key not set or invalid
- No internet connectivity
- Rate limit exceeded
- Provider service down

**See**: [LLM Configuration Guide](LLM-Configuration-Guide.md)

### Groups Not Following Commands

**Check command application**:
```sqf
// Enable debug logging
// In config.cpp:
class logging {
    level = "DEBUG";
    arma_console = 1;
};
```

**Look for**:
- Command validation failures
- AO boundary violations
- Invalid group IDs
- Command queue backlog

### High API Costs

**Monitor usage**:
```sqf
private _stats = call Root_fnc_getTokenStats;
systemChat format ["Cost: $%1", _stats get "total_cost"];
```

**Reduce costs**:
1. Increase decision interval: `BATCOM setVariable ["ai_min_interval", 60];`
2. Reduce AO size
3. Use Gemini with caching
4. Limit number of objectives

**See**: [LLM Configuration Guide - Cost Optimization](LLM-Configuration-Guide.md#cost-optimization)

### Performance Issues

**Symptoms**:
- Low FPS
- Lag spikes
- Slow AI response

**Solutions**:
1. Reduce world scan frequency in config.cpp
2. Limit max_controlled_groups
3. Reduce AO size
4. Lower max_commands_per_tick

---

## Mission Lifecycle

### Startup Sequence

1. **Server Init** → BATCOM loads
2. **Mission Init** → Your init.sqf runs
3. **Configuration** → LLM and sides configured
4. **Objective Setup** → Tasks added
5. **Deploy** → Commander activates
6. **First Scan** → World state captured (2s delay)
7. **First Decision** → LLM called (~45s after deploy)
8. **Command Execution** → Groups receive orders
9. **Continuous Loop** → Scan → Decide → Execute

### Shutdown Sequence

```sqf
// Stop commander
["deployCommander", false] call Root_fnc_batcomInit;

// Or end mission
endMission "END1";
```

### Mid-Mission Changes

```sqf
// Pause commander
["deployCommander", false] call Root_fnc_batcomInit;

// Modify objectives
["commanderTask", createHashMapFromArray [
    ["description", "New objective"],
    ["priority", 8],
    ["position", getMarkerPos "new_obj"],
    ["radius", 300]
], nil] call Root_fnc_batcomInit;

// Resume
["deployCommander", true] call Root_fnc_batcomInit;
```

---

## See Also

- [API Reference](API-Reference.md) - Complete function documentation
- [LLM Configuration Guide](LLM-Configuration-Guide.md) - Configure AI providers
- [Command Reference](Command-Reference.md) - Available tactical commands
- [Server Setup Guide](Server-Setup-Guide.md) - Server installation
- [Task Examples](../docs/task-examples.md) - More objective examples

---

**Last Updated**: 2025-12-05
