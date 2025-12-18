<div align="center">

# 🎖️ BATCOM

**Battlefield Commander AI for Arma 3**

*An intelligent AI commander powered by LLMs that dynamically controls and coordinates forces in real-time*

---

</div>

## 📋 Table of Contents

- [Server Setup](#-server-setup)
- [API Configuration](#-api-configuration)
- [Debugging](#-debugging)
- [Mission Initialization](#-mission-initialization)

---

## 🖥️ Server Setup

1. **Install this addon (contains version of Pythia)**
3. **Install dependencies** from `batcom/requirements.txt`

> ⚠️ **Important:** The requirements **MUST** be installed using Pythia's `install_requirements.bat` (Windows) or `install_requirements.sh` (Linux) — **NOT** your local Python installation.

---

## 🔑 API Configuration

There are multiple ways to configure the API and provider:

| Method | Description |
|--------|-------------|
| `guardrails.json` | Configure in `batcom\guardrails.json` |
| In-Game Command | Set up dynamically during gameplay |
| Environment Variable | Store API key as server environment variable *(requires provider to be set via config.cpp or in-game)* |

### In-Game Configuration

Execute the following command on the **server** to configure the LLM:

```sqf
["setLLMConfig", createHashMapFromArray [
  ["provider","gemini"],
  ["api_key","YOUR_GEMINI_KEY"],
  ["model","gemini-2.5-flash-lite"],
  ["endpoint","https://generativelanguage.googleapis.com"],
  ["rate_limit",12]
], true] call Root_fnc_batcomInit;
```

### Testing Connection

Verify your connection is working:

```sqf
[] call Root_fnc_testGeminiConnection;
```

> 📝 *More connector tests for other LLMs will be implemented soon. For now, use the free Gemini LLM.*

### Token Usage

| Location | Description |
|----------|-------------|
| `@batcom\logs\token_usage.json` | File located in Arma 3 install directory |
| `[] call BATCOM_fnc_getTokenStats` | In-game function to retrieve stats |

---

## 🔧 Debugging

Execute these functions to test and debug various issues:

```sqf
[] call Root_fnc_testPythia;
[] call BATCOM_fnc_init;
[] call BATCOM_fnc_debugInit;
[true] call Root_fnc_batcomDebug;
```

### Log Locations

| Log Type | Location |
|----------|----------|
| **RPT Logs** | Standard Arma 3 RPT location |
| **BATCOM Logs** | `@batcom\logs\` *(in Arma 3 install folder)* |

---

## 🚀 Mission Initialization

Once everything is configured, initialize your mission:

```sqf
// Set the high-level mission briefing for the AI
["commanderBrief", "<HIGH LEVEL MISSION INFORMATION / DESCRIPTION / PLAN FROM THE AI PERSPECTIVE>", true] call Root_fnc_batcomInit;

// Define allied sides
["commanderAllies", <ARRAY OF SIDE(S) THE AI CONSIDERS TO BE FRIENDS>, true] call Root_fnc_batcomInit;

// Define controllable sides
["commanderSides", <ARRAY OF SIDE(S) THE AI CAN DIRECTLY ORDER / CONTROL / MANIPULATE>, true] call Root_fnc_batcomInit;

// Add dynamic mission tasks
["commanderTask", [
  "<ANY ADDITIONAL DYNAMIC MISSION TASK>",
  <CLASS NAMES OF SPECIFIC VEHICLE/OBJECT/UNIT MENTIONED IN THE MISSION TASK>,
  <PRIORITY NUMBER WHERE HIGHER NUMBER MEANS MORE IMPORTANT>
], true] call Root_fnc_batcomInit;

// Deploy the AI Commander
// true = resets memory (fresh server/mission)
// false = appends to existing memory
["deployCommander", true] call Root_fnc_batcomInit;
```

### Example

```sqf
["commanderBrief", "Hostile BLUFOR units are coming to kill an HVT at position [16071.8,16995.6,0]. Protect the HVT.", true] call Root_fnc_batcomInit;
["commanderAllies", ["EAST","GUER"], true] call Root_fnc_batcomInit;
["commanderSides", ["EAST"], true] call Root_fnc_batcomInit;
["commanderTask", ["Deploy OPFOR hunter squad at 200m away from the HVT and start patrolling the area.", ["O_Soldier_F","O_Soldier_AR_F"], 8], true] call Root_fnc_batcomInit;
["deployCommander", true] call Root_fnc_batcomInit;
```

> 💡 The LLM will analyze the situation and issue orders dynamically — anything from relocating the HVT to coordinating all available units to fortify the position.
