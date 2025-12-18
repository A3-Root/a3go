# BATCOM Admin Commands Reference

All commands executed via: `[command, params, flag] call Root_fnc_batcomInit`

Execute on **server only** from debug console.

---

## Mission Setup Commands

### `commanderBrief` - Set Mission Intent
Sets the mission description/objective from the AI commander's perspective.

```sqf
["commanderBrief", "MISSION_DESCRIPTION", CLEAR_MEMORY] call Root_fnc_batcomInit;
```

**Parameters:**
- `MISSION_DESCRIPTION` (STRING): Mission objective description
- `CLEAR_MEMORY` (BOOL, optional): Clear AI context memory (default: false)

**Example:**
```sqf
["commanderBrief", "Protect HVT at coordinates [1234, 5678] from enemy assault", true] call Root_fnc_batcomInit;
```

---

### `commanderAllies` - Set Friendly Sides
Defines which factions are friendly (won't be attacked).

```sqf
["commanderAllies", [SIDE1, SIDE2, ...], nil] call Root_fnc_batcomInit;
```

**Parameters:**
- Sides array: List of sides (EAST/WEST/GUER/CIV or strings)

**Defaults:** `["EAST", "GUER"]`

**Example:**
```sqf
["commanderAllies", [east, resistance], nil] call Root_fnc_batcomInit;
["commanderAllies", ["EAST", "GUER"], nil] call Root_fnc_batcomInit;
```

---

### `commanderSides` - Set Controlled Sides
Defines which factions the AI can command.

```sqf
["commanderSides", [SIDE1, SIDE2, ...], nil] call Root_fnc_batcomInit;
```

**Parameters:**
- Sides array: List of controllable sides

**Defaults:** `["EAST"]`

**Example:**
```sqf
["commanderSides", [east], nil] call Root_fnc_batcomInit;
```

---

### `commanderTask` - Add Objective/Task
Adds a tactical objective for the AI to execute. Supports both simple array format and flexible hashmap format for complex tasks.

#### Simple Format (Legacy)
```sqf
["commanderTask", [DESCRIPTION, UNIT_CLASSES, PRIORITY], nil] call Root_fnc_batcomInit;
```

**Parameters:**
- `DESCRIPTION` (STRING): Task description
- `UNIT_CLASSES` (ARRAY): Unit classnames available for spawning (can be empty)
- `PRIORITY` (NUMBER): Priority level (0-10, higher = more important)

**Example:**
```sqf
["commanderTask", ["Deploy AAF rifle squad at northern objective", ["I_Soldier_F"], 8], nil] call Root_fnc_batcomInit;
```

---

#### Advanced Format (Hashmap)
Use hashmap format for complex tasks with additional context.

```sqf
["commanderTask", HASHMAP, nil] call Root_fnc_batcomInit;
```

**Hashmap Keys:**

**Required:**
- `description` (STRING): Task description for LLM
- `priority` (NUMBER): Priority level (0-10)

**Optional:**
- `position` (ARRAY): [x, y, z] coordinates (auto-parsed from description if not provided)
- `radius` (NUMBER): Area radius in meters (default: 0)
- `unit_classes` (ARRAY): Available unit classnames for spawning

**Task-Specific Metadata:**
- `target_unit` (STRING): Specific unit name to protect/eliminate
- `target_group` (STRING): Specific group ID to protect/eliminate
- `patrol_waypoints` (ARRAY): List of waypoint positions [[x,y,z], [x,y,z], ...]
- `area_center` (ARRAY): [x, y, z] center of area
- `area_radius` (NUMBER): Radius for area tasks
- `spawn_assets` (ARRAY): List of asset types AI can deploy
- `task_type` (STRING): Hint for task type ("defend", "patrol", "protect", "attack", etc.)
- `metadata` (HASHMAP): Any additional custom data for LLM context

---

#### Examples

**Protect Specific Unit:**
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Protect HVT 'Bravo-6' from enemy forces"],
    ["priority", 10],
    ["target_unit", "hvt_bravo6"],
    ["position", getPos hvt_bravo6],
    ["radius", 200],
    ["task_type", "protect_hvt"]
], nil] call Root_fnc_batcomInit;
```

**Regular Area Patrol:**
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Maintain continuous patrols around the airfield perimeter"],
    ["priority", 7],
    ["patrol_waypoints", [[5000, 5000, 0], [5200, 5000, 0], [5200, 5200, 0], [5000, 5200, 0]]],
    ["task_type", "patrol"],
    ["area_center", [5100, 5100, 0]],
    ["area_radius", 300]
], nil] call Root_fnc_batcomInit;
```

**Defend Area:**
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Defend the control tower at all costs"],
    ["priority", 9],
    ["position", [5234, 5678, 0]],
    ["radius", 150],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;
```

**Deploy Units to Position:**
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Deploy rifle squad to northern ridge and establish overwatch"],
    ["priority", 6],
    ["position", [6000, 7000, 0]],
    ["unit_classes", ["I_Soldier_F", "I_Soldier_AR_F", "I_Soldier_GL_F"]],
    ["spawn_assets", ["infantry_squad"]],
    ["task_type", "deploy_and_defend"]
], nil] call Root_fnc_batcomInit;
```

**Eliminate Threats:**
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Locate and eliminate enemy mortar team in sector 5-7"],
    ["priority", 8],
    ["area_center", [5500, 7200, 0]],
    ["area_radius", 500],
    ["task_type", "hunt_enemy"],
    ["metadata", createHashMapFromArray [
        ["target_type", "mortar_team"],
        ["time_limit", 1800]
    ]]
], nil] call Root_fnc_batcomInit;
```

**Escort Mission:**
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Escort supply convoy from base to forward position"],
    ["priority", 7],
    ["target_group", "convoy_1"],
    ["task_type", "escort"],
    ["patrol_waypoints", [[3000, 3000, 0], [4000, 4500, 0], [5000, 6000, 0]]],
    ["metadata", createHashMapFromArray [
        ["convoy_size", 3],
        ["threat_level", "high"]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

**How LLM Uses Task Data:**

The LLM receives all objective data in each decision cycle, including:
- `description`: Main task instruction
- `priority`: Relative importance
- `position`/`radius`: Geographic context
- `metadata`: All additional context fields

The LLM uses this information to:
1. Understand what needs to be done
2. Allocate appropriate forces
3. Generate tactical commands (move, defend, patrol, etc.)
4. Adapt to changing battlefield conditions

**Best Practices:**
- Use clear, descriptive task descriptions
- Set realistic priorities (10 = critical, 1 = low)
- Include position/waypoint data when relevant
- Use metadata for additional context the LLM might need
- Tasks persist until manually removed or completed

---

## LLM Configuration Commands

### `setLLMConfig` - Configure LLM Provider
Sets LLM provider, API key, model, and rate limits at runtime.

```sqf
["setLLMConfig", HASHMAP, true] call Root_fnc_batcomInit;
```

**Parameters (hashmap keys):**
- `provider` (STRING): "gemini" | "openai" | "claude" | "deepseek" | "azure" | "local"
- `api_key` (STRING): API key for provider
- `model` (STRING, optional): Model name (provider-specific defaults)
- `endpoint` (STRING, optional): Custom API endpoint URL
- `rate_limit` (NUMBER, optional): Requests per minute (default: 10)
- `min_interval` (NUMBER, optional): Minimum seconds between calls (default: 10)
- `timeout` (NUMBER, optional): Request timeout in seconds (default: 30)

**Provider Defaults:**
- Gemini: `gemini-2.0-flash-lite`
- OpenAI: `gpt-4o-mini`
- Claude: `claude-3-5-sonnet-20240620`
- DeepSeek: `deepseek-chat`
- Azure: `gpt-4o-mini` (requires endpoint)

**Example:**
```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_GEMINI_KEY"],
    ["model", "gemini-2.0-flash-lite"],
    ["rate_limit", 12]
], true] call Root_fnc_batcomInit;
```

---

### `setLLMApiKey` - Set API Key Only
Updates API key for a specific provider without changing other settings.

```sqf
["setLLMApiKey", [PROVIDER, API_KEY], nil] call Root_fnc_batcomInit;
```

**Parameters:**
- `PROVIDER` (STRING): Provider name ("gemini", "openai", etc.)
- `API_KEY` (STRING): API key

**Example:**
```sqf
["setLLMApiKey", ["gemini", "YOUR_API_KEY_HERE"], nil] call Root_fnc_batcomInit;
```

---

### `setGeminiApiKey` - Legacy Gemini Key
Legacy command, prefer `setLLMApiKey` or `setLLMConfig`.

```sqf
["setGeminiApiKey", "YOUR_GEMINI_KEY", nil] call Root_fnc_batcomInit;
```

---

## Deployment & Control Commands

### `deployCommander` - Start/Stop AI Commander
Activates or deactivates the AI decision loop.

```sqf
["deployCommander", RESET_FLAG] call Root_fnc_batcomInit;
```

**Parameters:**
- `RESET_FLAG` (BOOL): true = fresh start (reset state), false = resume

**Example:**
```sqf
// Start fresh
["deployCommander", true] call Root_fnc_batcomInit;

// Resume/unpause
["deployCommander", false] call Root_fnc_batcomInit;
```

---

### `commanderControlGroups` - Override Group Control
Forces specific groups to be controlled regardless of side.

```sqf
["commanderControlGroups", [GROUP_ID1, GROUP_ID2, ...], nil] call Root_fnc_batcomInit;
```

**Parameters:**
- Array of group ID strings

**Example:**
```sqf
["commanderControlGroups", ["alpha_team", "bravo_team"], nil] call Root_fnc_batcomInit;
```

---

## Advanced Configuration

### `commanderGuardrails` - Set Guardrails
Configures AO bounds and resource pools.

```sqf
["commanderGuardrails", GUARDRAILS_HASHMAP, nil] call Root_fnc_batcomInit;
```

**Guardrails Structure:**
```sqf
createHashMapFromArray [
    ["ao_bounds", createHashMapFromArray [
        ["center", [X, Y]],
        ["radius", RADIUS_METERS],
        ["type", "circle"]  // or "rectangle"
    ]],
    ["resource_pool", createHashMapFromArray [
        ["EAST", createHashMapFromArray [
            ["infantry_squad", createHashMapFromArray [
                ["classnames", ["O_Soldier_F"]],
                ["max", 3]
            ]],
            ["attack_heli", createHashMapFromArray [
                ["classnames", ["O_Heli_Attack_02_dynamicLoadout_F"]],
                ["max", 1]
            ]]
        ]]
    ]]
]
```

**Example:**
```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_bounds", createHashMapFromArray [
        ["center", [5000, 5000]],
        ["radius", 2000],
        ["type", "circle"]
    ]]
], nil] call Root_fnc_batcomInit;
```

---

## Debug & Monitoring Commands

### `getTokenStats` - Get Token Usage
Returns cumulative LLM token usage statistics.

```sqf
call Root_fnc_getTokenStats;
```

**Returns:** Hashmap with `input_tokens`, `output_tokens`, `total_tokens`, `llm_calls`

**Example:**
```sqf
private _stats = call Root_fnc_getTokenStats;
systemChat format ["Tokens used: %1", _stats get "total_tokens"];
```

---

## Complete Setup Example

```sqf
// 1. Configure LLM
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_API_KEY"],
    ["model", "gemini-2.0-flash-lite"],
    ["rate_limit", 12]
], true] call Root_fnc_batcomInit;

// 2. Set mission context
["commanderBrief", "Protect HVT at grid 1234-5678 from CSAT forces. HVT must survive.", true] call Root_fnc_batcomInit;

// 3. Set factions
["commanderAllies", ["EAST", "GUER"], nil] call Root_fnc_batcomInit;
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;

// 4. Set AO bounds
["commanderGuardrails", createHashMapFromArray [
    ["ao_bounds", createHashMapFromArray [
        ["center", [5000, 5000]],
        ["radius", 3000],
        ["type", "circle"]
    ]]
], nil] call Root_fnc_batcomInit;

// 5. Add objectives
// Simple format:
["commanderTask", ["Defend HVT position", [], 10], nil] call Root_fnc_batcomInit;

// Advanced format (recommended for complex tasks):
["commanderTask", createHashMapFromArray [
    ["description", "Protect control tower from enemy assault"],
    ["priority", 10],
    ["position", [5000, 5000, 0]],
    ["radius", 200],
    ["task_type", "defend_area"]
], nil] call Root_fnc_batcomInit;

// 6. Deploy (start AI)
["deployCommander", true] call Root_fnc_batcomInit;
```
