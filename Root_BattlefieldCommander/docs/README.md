# BATCOM Documentation

Root's Battlefield Commander (BATCOM) - LLM-powered AI commander for Arma 3.

---

## Documentation Files

- **[quick-start.md](quick-start.md)** - Get BATCOM running in 5 steps
- **[admin-commands.md](admin-commands.md)** - Complete admin command reference
- **[task-examples.md](task-examples.md)** - Comprehensive task/objective examples for all scenarios
- **[debug-functions.md](debug-functions.md)** - Debug and testing functions

---

## What is BATCOM?

BATCOM uses Large Language Models (LLMs) to command AI forces in Arma 3 dynamically based on:
- Current battlefield state (friendly/enemy positions, force ratios)
- Mission objectives
- Available resources
- Tactical constraints (AO bounds, rules of engagement)

The LLM generates tactical orders (move, defend, patrol, attack, spawn units, deploy assets) which are executed in real-time.

---

## Architecture

```
┌─────────────┐
│  Arma 3 SQF │ ← World scanning, command execution
└──────┬──────┘
       │ (Pythia extension)
       ↓
┌─────────────┐
│  Python Core│ ← Decision loop, LLM integration
└──────┬──────┘
       │ (API calls)
       ↓
┌─────────────┐
│     LLM     │ ← Gemini/OpenAI/Claude/DeepSeek
└─────────────┘
```

**Key Components:**
- **SQF Layer**: World state scanning, command application, configuration
- **Python Core**: Decision loop, LLM prompt generation, command validation
- **LLM Provider**: Generates tactical orders based on battlefield analysis

---

## Key Features

- **Multi-provider LLM support**: Gemini, OpenAI, Claude, DeepSeek, Azure, local models
- **Real-time tactical decisions**: Analyzes battlefield every 45+ seconds
- **Resource pools**: Limit available assets AI can deploy
- **AO boundaries**: Restrict operations to specific map areas
- **Command validation**: Sandbox prevents invalid/dangerous commands
- **Token tracking**: Monitor LLM API usage
- **Async LLM calls**: Non-blocking API requests

---

## System Requirements

- **Arma 3 Server** (dedicated or hosted)
- **Pythia Extension** (Python bridge for Arma 3)
- **Python 3.8+** with dependencies installed via Pythia
- **LLM API Key** (Gemini, OpenAI, etc.)

---

## Installation

1. Install **Pythia extension** in Arma 3
2. Load **@BATCOM** addon on server: `-serverMod=@Pythia;@BATCOM`
3. Install Python dependencies via Pythia's `install_requirements.bat`
4. Configure LLM API key in mission

See **[quick-start.md](quick-start.md)** for detailed setup.

---

## Basic Usage

```sqf
// 1. Configure LLM
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
], true] call Root_fnc_batcomInit;

// 2. Set mission brief
["commanderBrief", "Defend the airfield from CSAT assault", true] call Root_fnc_batcomInit;

// 3. Set factions
["commanderAllies", ["EAST"], nil] call Root_fnc_batcomInit;
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;

// 4. Deploy AI
["deployCommander", true] call Root_fnc_batcomInit;
```

---

## Supported LLM Providers

| Provider | Default Model | Notes |
|----------|--------------|-------|
| Gemini | `gemini-2.0-flash-lite` | Fast, cost-effective |
| OpenAI | `gpt-4o-mini` | Good balance |
| Claude | `claude-3-5-sonnet` | Best reasoning |
| DeepSeek | `deepseek-chat` | Budget option |
| Azure | `gpt-4o-mini` | Enterprise |
| Local | N/A | Custom endpoints |

---

## Task Types

BATCOM supports flexible task/objective definitions. Tasks can be anything from defending areas to protecting specific units to conducting patrols:

**Common Task Types:**
- **Defend Area**: Hold specific positions against enemy forces
- **Protect Unit/Group**: Guard high-value targets or friendly forces
- **Patrol Area**: Conduct regular patrols in specified zones
- **Eliminate Threats**: Hunt and destroy enemy forces
- **Deploy Forces**: Spawn and position new units
- **Escort Mission**: Protect convoys or moving units
- **Custom Tasks**: Any task described in natural language with relevant metadata

See `admin-commands.md` for detailed examples of each task type.

---

## Command Types

The LLM can issue these tactical commands to execute tasks:

- **move_to**: Reposition forces
- **defend_area**: Establish defensive positions
- **patrol_route**: Active reconnaissance
- **seek_and_destroy**: Offensive operations
- **transport_group**: Use vehicles to move units
- **escort_group**: Protect high-value targets
- **fire_support**: Air/armor fire missions
- **deploy_asset**: Spawn from resource pool

---

## Configuration

### Via config.cpp
Default configuration in `addons/main/config.cpp` under `CfgBATCOM`:
- Logging levels
- Scan intervals
- Rate limits
- Safety constraints

### Runtime Configuration
Use admin commands to override config at runtime:
```sqf
["setLLMConfig", ...] call Root_fnc_batcomInit;
["commanderGuardrails", ...] call Root_fnc_batcomInit;
```

---

## Decision Cycle

1. **World Scan**: Collect battlefield state (groups, positions, threats)
2. **Evaluate Objectives**: Assess objective status and priority
3. **LLM Decision**: Send battlefield data to LLM, receive tactical orders
4. **Validate Commands**: Check orders against safety rules
5. **Execute Commands**: Apply waypoints, spawn units, issue behaviors
6. **Wait**: Minimum 45s interval before next cycle

---

## Safety & Constraints

BATCOM includes multiple safety layers:

- **Command Whitelist**: Only allowed command types execute
- **AO Bounds**: Positions outside AO are rejected
- **Resource Limits**: Max units/assets enforced
- **Spawn Limits**: Maximum units per side
- **Group/Objective Limits**: Prevent command spam
- **Circuit Breaker**: Disables LLM after 3 consecutive errors

Configure via:
```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_bounds", ...],
    ["resource_pool", ...]
], nil] call Root_fnc_batcomInit;
```

---

## Logs & Monitoring

**Log Locations:**
- Arma RPT: Standard Arma 3 logs directory
- BATCOM Python: `@BATCOM/logs/batcom_YYYYMMDD.log`
- Token usage: `@BATCOM/token_usage.json`

**Monitoring Commands:**
```sqf
call Root_fnc_getTokenStats;      // LLM usage stats
call BATCOM_fnc_worldScan;        // Current battlefield state
call BATCOM_fnc_isEnabled;        // Check if running
```

---

## Troubleshooting

### BATCOM not initializing
```sqf
call BATCOM_fnc_debugInit;  // Force init with verbose logs
call Root_fnc_testPythia;   // Test Python bridge
```

### LLM not responding
```sqf
call Root_fnc_testGeminiConnection;  // Test LLM connection
call Root_fnc_getTokenStats;         // Check if calls are being made
```

### Groups not being controlled
- Verify controlled sides: `["commanderSides", [east], nil]`
- Check group classification: `call BATCOM_fnc_worldScan;`

See **[debug-functions.md](debug-functions.md)** for detailed debugging.

---

## Performance Considerations

- **LLM Rate Limit**: Default 10s minimum between calls (configurable)
- **Decision Interval**: 45s minimum between decision cycles
- **World Scan**: Every 2 seconds (configurable in config.cpp)
- **Token Costs**: Monitor via `token_usage.json`

**Recommendations:**
- Use faster models (Gemini Flash, GPT-4o-mini) for real-time ops
- Set rate limits appropriate to your API quota
- Monitor token usage to avoid unexpected costs
- Use AO bounds to limit LLM's scope

---

## Advanced Topics

### Custom Resource Pools
Define specific assets AI can deploy:
```sqf
["commanderGuardrails", createHashMapFromArray [
    ["resource_pool", createHashMapFromArray [
        ["EAST", createHashMapFromArray [
            ["qrf_team", createHashMapFromArray [
                ["classnames", ["O_Soldier_F", "O_medic_F"]],
                ["max", 2]
            ]]
        ]]
    ]]
], nil] call Root_fnc_batcomInit;
```

### Mission Variables
Pass custom data to LLM via mission variables:
```sqf
// Set in mission
missionNamespace setVariable ["BATCOM_missionIntel_HVTGroupId", "alpha_1", true];

// LLM receives in worldstate.mission_variables
```

### Controlled Group Overrides
Force specific groups under AI control:
```sqf
["commanderControlGroups", ["alpha_team", "bravo_team"], nil] call Root_fnc_batcomInit;
```

---

## Contributing

- Report issues: GitHub repository
- Check logs: `@BATCOM/logs/` for detailed debug output
- Test with `call Root_fnc_testGeminiConnection;`

---

## License & Credits

Root's Battlefield Commander (BATCOM)
Author: Root

See repository for full credits and license information.
