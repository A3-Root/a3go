# Troubleshooting Guide

Comprehensive troubleshooting guide for BATCOM issues, errors, and common problems.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [LLM Connection Issues](#llm-connection-issues)
- [AI Behavior Issues](#ai-behavior-issues)
- [Performance Issues](#performance-issues)
- [Server Issues](#server-issues)
- [Mission Issues](#mission-issues)
- [Error Messages](#error-messages)
- [Debug Tools](#debug-tools)
- [Getting Help](#getting-help)

---

## Quick Diagnostics

### Run These First

```sqf
// 1. Check if BATCOM is loaded
if (isClass (configFile >> "CfgPatches" >> "root_batcom")) then {
    systemChat "✓ BATCOM loaded";
} else {
    systemChat "✗ BATCOM NOT loaded";
};

// 2. Check if CBA is loaded
if (isClass (configFile >> "CfgPatches" >> "cba_main")) then {
    systemChat "✓ CBA loaded";
} else {
    systemChat "✗ CBA NOT loaded";
};

// 3. Test Pythia extension
call Root_fnc_testPythia;

// 4. Test LLM connection
private _result = call Root_fnc_testGeminiConnection;
systemChat _result;

// 5. Check if commander is running
if (call BATCOM_fnc_isEnabled) then {
    systemChat "✓ Commander is running";
} else {
    systemChat "✗ Commander is NOT running";
};

// 6. Check debug info
call BATCOM_fnc_debugInit;
```

### Check Logs

**Arma 3 RPT Log**:
- **Windows**: `%LOCALAPPDATA%\Arma 3\` or `ServerProfile\`
- **Linux**: `~/.local/share/Arma 3/` or server profile directory
- Look for lines containing `[BATCOM]`

**Python Logs**:
- Location: `@BATCOM/logs/batcom_YYYYMMDD_HHMMSS.log`
- Check for ERROR or WARN level messages

**API Call Logs**:
- Location: `@BATCOM/apicall.<map>.<mission>.<ao>.<timestamp>.log`
- Shows all LLM API interactions

---

## Installation Issues

### BATCOM Not Loading

**Symptoms**:
- No BATCOM messages in logs
- Functions undefined: `Root_fnc_batcomInit` is nil
- No BATCOM in mod list

**Diagnostic**:
```sqf
isClass (configFile >> "CfgPatches" >> "root_batcom")
// If returns false, BATCOM is not loaded
```

**Causes & Solutions**:

#### 1. Mod Not in Server Command

**Check**: Server startup command
```bash
# Should include:
-serverMod=@CBA_A3;@BATCOM
```

**Fix**: Add BATCOM to serverMod parameter

#### 2. Incorrect Folder Structure

**Check**: Folder structure
```
@BATCOM/
├── addons/
│   └── root_batcom.pbo    # Must exist
├── mod.cpp                # Must exist
└── keys/
```

**Fix**: Reinstall BATCOM with correct structure

#### 3. File Permissions (Linux)

**Check**: Permissions
```bash
ls -la @BATCOM
```

**Fix**: Set correct permissions
```bash
chmod -R 755 @BATCOM
chown -R serveruser:servergroup @BATCOM
```

#### 4. CBA Not Loaded

**Check**: CBA presence
```sqf
isClass (configFile >> "CfgPatches" >> "cba_main")
```

**Fix**: Install CBA_A3 and load before BATCOM
```bash
-serverMod=@CBA_A3;@BATCOM  # CBA must be first
```

#### 5. PBO Corruption

**Check**: PBO integrity
```bash
# Extract PBO and check for errors
```

**Fix**: Re-download BATCOM from official source

---

## LLM Connection Issues

### "Connection timeout" Error

**Symptoms**:
- LLM calls fail
- Timeout errors in logs
- AI makes no decisions

**Diagnostic**:
```sqf
call Root_fnc_testGeminiConnection;
// Check result message
```

**Causes & Solutions**:

#### 1. No Internet Connectivity

**Check**: Network connection
```bash
# Windows
ping google.com

# Linux
ping -c 4 google.com
```

**Fix**: Restore internet connectivity

#### 2. Firewall Blocking HTTPS

**Check**: Firewall rules
```bash
# Windows
netsh advfirewall show currentprofile

# Linux
sudo ufw status
```

**Fix**: Allow outbound HTTPS (port 443)
```bash
# Linux
sudo ufw allow out 443/tcp

# Windows: Windows Defender Firewall → Outbound Rules → Allow HTTPS
```

#### 3. Proxy Issues

**Check**: Proxy settings

**Fix**: Configure proxy for Arma 3 server or bypass proxy

#### 4. Provider Service Down

**Check**: Provider status
- Gemini: https://status.cloud.google.com/
- OpenAI: https://status.openai.com/
- Claude: https://status.anthropic.com/

**Fix**: Wait for service restoration or switch to alternative provider

#### 5. Timeout Too Short

**Check**: Config timeout setting
```json
{
    "timeout": 30  // May be too short
}
```

**Fix**: Increase timeout
```sqf
["setLLMConfig", createHashMapFromArray [
    ["timeout", 60]  // Increase to 60 seconds
], true] call Root_fnc_batcomInit;
```

---

### "Invalid API key" Error

**Symptoms**:
- Authentication errors
- "401 Unauthorized" in logs
- LLM calls rejected

**Diagnostic**:
```sqf
call Root_fnc_testGeminiConnection;
// Will report "Invalid API key" if key is wrong
```

**Causes & Solutions**:

#### 1. API Key Not Set

**Check**: Key configuration
```sqf
// Check if key is set
diag_log str (BATCOM get "api_key");
```

**Fix**: Set API key
```sqf
["setLLMApiKey", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_API_KEY"]
], nil] call Root_fnc_batcomInit;
```

#### 2. Incorrect API Key

**Check**: Verify key on provider platform
- Gemini: https://makersuite.google.com/app/apikey
- OpenAI: https://platform.openai.com/api-keys

**Fix**: Use correct API key

#### 3. API Key Expired

**Check**: Key validity on provider platform

**Fix**: Generate new API key

#### 4. Wrong Provider Key

**Check**: Provider vs key mismatch
```json
{
    "provider": "gemini",
    "api_key": "sk-..."  // This is an OpenAI key!
}
```

**Fix**: Use correct key for provider

---

### "Rate limit exceeded" Error

**Symptoms**:
- "429 Too Many Requests" errors
- LLM calls rejected
- Intermittent failures

**Diagnostic**:
Check `token_usage.json` for call frequency

**Causes & Solutions**:

#### 1. Too Frequent Calls

**Check**: Decision interval
```sqf
diag_log str (BATCOM get "ai_min_interval");
```

**Fix**: Increase interval
```sqf
["setLLMConfig", createHashMapFromArray [
    ["min_interval", 30]  // Increase from 10 to 30
], true] call Root_fnc_batcomInit;
```

#### 2. Free Tier Limits

**Check**: Provider tier
- Gemini Free: 15 req/min
- OpenAI Free: 3 req/min

**Fix**: Upgrade to paid tier or increase interval

#### 3. Multiple Instances

**Check**: Multiple BATCOM instances running

**Fix**: Ensure only one instance per API key

---

## AI Behavior Issues

### AI Not Moving Groups

**Symptoms**:
- Groups stay in place
- No waypoints added
- Commands not executed

**Diagnostic**:
```sqf
// Check controlled groups
private _groups = BATCOM get "controlled_groups";
systemChat format ["Controlled: %1", count _groups];

// Check objectives
private _objs = BATCOM get "objectives";
systemChat format ["Objectives: %1", count _objs];

// Check command queue
["batcom.get_pending_commands", []] call py3_fnc_callExtension;
```

**Causes & Solutions**:

#### 1. Commander Not Deployed

**Check**:
```sqf
call BATCOM_fnc_isEnabled;  // Should return true
```

**Fix**:
```sqf
["deployCommander", true] call Root_fnc_batcomInit;
```

#### 2. No Groups Controlled

**Check**: Group control
```sqf
private _groups = BATCOM get "controlled_groups";
if (count _groups == 0) then {
    systemChat "No groups under control!";
};
```

**Fix**: Ensure correct sides are set
```sqf
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;
```

#### 3. No Objectives Defined

**Check**:
```sqf
private _objs = BATCOM get "objectives";
if (count _objs == 0) then {
    systemChat "No objectives!";
};
```

**Fix**: Add objectives
```sqf
["commanderTask", createHashMapFromArray [
    ["description", "Test objective"],
    ["priority", 5],
    ["position", [5000, 5000, 0]],
    ["radius", 500]
], nil] call Root_fnc_batcomInit;
```

#### 4. Groups Player-Controlled

**Check**: Group ownership

**Fix**: Only AI groups can be controlled - player groups are ignored

#### 5. Commands Blocked by Sandbox

**Check**: Debug logs for validation failures

**Fix**: Check AO bounds, resource limits, command whitelist

---

### AI Making Poor Decisions

**Symptoms**:
- Illogical unit movements
- Not defending objectives
- Wasteful deployments

**Causes & Solutions**:

#### 1. Unclear Mission Brief

**Check**: Mission brief content
```sqf
diag_log str (BATCOM get "mission_brief");
```

**Fix**: Provide clear, specific brief
```sqf
["commanderBrief", "
    Defend the airfield from enemy assault from the east.
    Priority: Protect the control tower and runways.
", true] call Root_fnc_batcomInit;
```

#### 2. Poor Objective Priorities

**Check**: Objective priorities

**Fix**: Use full 0-10 scale appropriately
```sqf
// Critical objective
["priority", 10]

// Standard objective
["priority", 5]

// Optional objective
["priority", 2]
```

#### 3. Wrong Model for Task

**Check**: LLM model used
```json
{
    "model": "gpt-3.5-turbo"  // May not be sophisticated enough
}
```

**Fix**: Use better model
```sqf
["setLLMConfig", createHashMapFromArray [
    ["model", "gemini-2.5-flash-lite"]  // Better tactical reasoning
], true] call Root_fnc_batcomInit;
```

#### 4. Insufficient Context

**Check**: Order history length

**Fix**: Ensure order history is maintained (automatic in BATCOM)

---

### AI Spamming Commands

**Symptoms**:
- Groups constantly changing orders
- Waypoints deleted/recreated rapidly
- Erratic movement

**Causes & Solutions**:

#### 1. Decision Interval Too Short

**Check**:
```sqf
diag_log str (BATCOM get "ai_min_interval");
```

**Fix**: Increase interval
```sqf
["setLLMConfig", createHashMapFromArray [
    ["min_interval", 60]  // Slow down decisions
], true] call Root_fnc_batcomInit;
```

#### 2. Objectives Too Close Together

**Check**: Objective positions

**Fix**: Spread objectives apart or reduce count

#### 3. Too Many Groups

**Check**: Group count
```sqf
private _groups = BATCOM get "controlled_groups";
systemChat format ["Groups: %1", count _groups];
```

**Fix**: Limit controlled groups
```cpp
// In config.cpp
max_controlled_groups = 50;  // Reduce from 500
```

---

## Performance Issues

### Low Server FPS

**Symptoms**:
- Server FPS drops below 30
- Lag spikes
- Player complaints of lag

**Diagnostic**:
```sqf
diag_fps  // Check current FPS
```

**Causes & Solutions**:

#### 1. Too Frequent World Scans

**Check**: Scan frequency
```cpp
// config.cpp
class scan {
    tick = 2.0;  // May be too frequent
};
```

**Fix**: Increase scan interval
```cpp
class scan {
    tick = 4.0;  // Reduce frequency
};
```

#### 2. Too Many Controlled Units

**Check**: Unit count
```sqf
{count units _x} forEach (BATCOM get "controlled_groups");
```

**Fix**: Limit controlled groups
```cpp
max_controlled_groups = 50;
max_units_per_side = 200;
```

#### 3. Complex LLM Prompts

**Check**: Token usage in `token_usage.json`

**Fix**: Reduce AO size, limit objectives

#### 4. Other Server Load

**Check**: Server CPU/RAM usage

**Fix**: Optimize mission, reduce other mods

---

### High Memory Usage

**Symptoms**:
- Memory usage grows over time
- Server crashes after extended play
- "Out of memory" errors

**Diagnostic**:
Check server memory usage via task manager/top

**Causes & Solutions**:

#### 1. Log Accumulation

**Check**: Log file sizes
```bash
ls -lh @BATCOM/logs/
```

**Fix**: Rotate logs regularly
```bash
# Delete old logs
find @BATCOM/logs/ -name "*.log" -mtime +7 -delete
```

#### 2. Order History Buildup

**Check**: History length (in Python code)

**Fix**: Automatic in BATCOM (keeps last 20 orders)

#### 3. Memory Leak

**Check**: Memory growth over time

**Fix**: Restart server periodically, report bug if confirmed

---

### High API Costs

**Symptoms**:
- Unexpected API bills
- Token usage higher than expected
- Budget exceeded

**Diagnostic**:
```bash
cat @BATCOM/token_usage.json
```

**Causes & Solutions**:

#### 1. Caching Not Working

**Check**: Token metrics in logs
```
# With caching: ~440 tokens/call
# Without caching: ~4300 tokens/call
```

**Fix**: Verify using Gemini with caching enabled
```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["model", "gemini-2.5-flash-lite"]  // Supports caching
], true] call Root_fnc_batcomInit;
```

#### 2. Too Frequent Decisions

**Check**: Call frequency in API logs

**Fix**: Increase decision interval
```sqf
["setLLMConfig", createHashMapFromArray [
    ["min_interval", 60]  // Reduce call frequency
], true] call Root_fnc_batcomInit;
```

#### 3. Large AO/Many Objectives

**Check**: World state size in API logs

**Fix**: Reduce AO size
```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_radius", 1500]  // Smaller AO
], nil] call Root_fnc_batcomInit;
```

#### 4. Expensive Model

**Check**: Model used
```json
{
    "model": "claude-3-opus"  // Very expensive
}
```

**Fix**: Use cheaper model
```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["model", "gemini-2.5-flash-lite"]  // Much cheaper
], true] call Root_fnc_batcomInit;
```

---

## Server Issues

### Server Crash on Startup

**Symptoms**:
- Server exits immediately
- Error in RPT log
- Can't load mission

**Diagnostic**:
Check server RPT log for errors

**Common Errors & Fixes**:

#### "Cannot load root_batcom.pbo"

**Cause**: Corrupted PBO or wrong location

**Fix**: Reinstall BATCOM, verify folder structure

#### "Python extension failed to load"

**Cause**: Pythia not installed or incompatible

**Fix**: Install Pythia extension, check compatibility

#### "CBA not found"

**Cause**: CBA_A3 not loaded or wrong version

**Fix**: Install CBA_A3, ensure loaded before BATCOM

---

### Server Won't Start Mission

**Symptoms**:
- Mission selection screen loops
- Mission fails to load
- "Mission file not found" error

**Diagnostic**:
Check mission file integrity

**Causes & Solutions**:

#### 1. Mission Syntax Error

**Check**: Mission init.sqf for errors

**Fix**: Validate SQF syntax, check for missing semicolons

#### 2. BATCOM Init Error

**Check**: BATCOM initialization code

**Fix**: Ensure proper initialization sequence
```sqf
waitUntil {!isNil "Root_fnc_batcomInit"};  // Wait for BATCOM
// Then configure...
```

#### 3. Missing Dependencies

**Check**: Required mods

**Fix**: Ensure all required mods loaded

---

## Mission Issues

### Mission Won't Initialize BATCOM

**Symptoms**:
- `Root_fnc_batcomInit` is nil
- No BATCOM activity in mission
- Errors on init

**Diagnostic**:
```sqf
!isNil "Root_fnc_batcomInit"  // Should be true
```

**Causes & Solutions**:

#### 1. Too Early Initialization

**Problem**: Called before BATCOM loaded

**Fix**: Use waitUntil
```sqf
waitUntil {!isNil "Root_fnc_batcomInit"};
// Now safe to call BATCOM functions
```

#### 2. Wrong Execution Environment

**Problem**: Called on client instead of server

**Fix**: Ensure server execution
```sqf
if (!isServer) exitWith {};  // Server only

waitUntil {!isNil "Root_fnc_batcomInit"};
// BATCOM init code...
```

---

### Objectives Not Working

**Symptoms**:
- AI ignores objectives
- No force allocation to objectives
- Objectives not in commander state

**Diagnostic**:
```sqf
private _objs = BATCOM get "objectives";
{
    diag_log format ["Objective: %1", _x];
} forEach _objs;
```

**Causes & Solutions**:

#### 1. Invalid Objective Format

**Check**: Objective structure
```sqf
// Wrong - missing required fields
["commanderTask", "Defend", nil] call Root_fnc_batcomInit;

// Correct
["commanderTask", createHashMapFromArray [
    ["description", "Defend"],
    ["priority", 5],
    ["position", [5000, 5000, 0]],
    ["radius", 500]
], nil] call Root_fnc_batcomInit;
```

**Fix**: Use proper hashmap format with required fields

#### 2. Objectives Outside AO

**Check**: AO bounds vs objective position

**Fix**: Ensure objectives within AO
```sqf
["commanderGuardrails", createHashMapFromArray [
    ["ao_center", [5000, 5000, 0]],
    ["ao_radius", 2000]  // Must contain objectives
], nil] call Root_fnc_batcomInit;
```

#### 3. Zero Priority Objectives

**Check**: Priority values

**Fix**: Use priority 1-10 (0 is lowest, may be ignored)

---

## Error Messages

### Common Error Patterns

#### "Group not found: B_Alpha_1_5"

**Meaning**: LLM requested command for non-existent group

**Fix**: Usually self-healing (AI will adjust), but check for:
- Groups being deleted externally
- Incorrect side configuration
- Group ID format issues

#### "Position outside AO bounds"

**Meaning**: Command position violates AO constraints

**Fix**:
- Expand AO bounds
- Verify objective positions
- Check LLM is respecting boundaries

#### "Resource pool limit exceeded: infantry_squad"

**Meaning**: Attempt to deploy more assets than allowed

**Fix**: Increase resource pool limits
```sqf
["commanderGuardrails", createHashMapFromArray [
    ["resource_pool", createHashMapFromArray [
        ["EAST", createHashMapFromArray [
            ["infantry_squad", createHashMapFromArray [
                ["max", 10]  // Increase limit
            ]]
        ]]
    ]]
], nil] call Root_fnc_batcomInit;
```

#### "Command type not allowed: xyz"

**Meaning**: Command not in whitelist

**Fix**: Add to allowed_commands or use different command

#### "Circuit breaker open - LLM disabled"

**Meaning**: 3+ consecutive LLM errors, auto-disabled

**Fix**:
1. Resolve underlying error (API key, connectivity, etc.)
2. Restart commander
```sqf
["deployCommander", false] call Root_fnc_batcomInit;
["deployCommander", true] call Root_fnc_batcomInit;
```

---

## Debug Tools

### Built-in Debug Functions

```sqf
// Test Pythia extension
call Root_fnc_testPythia;

// Test LLM connection
call Root_fnc_testGeminiConnection;

// Debug initialization
call BATCOM_fnc_debugInit;

// Check if enabled
call BATCOM_fnc_isEnabled;

// Get token statistics
call Root_fnc_getTokenStats;

// Manual world scan
call BATCOM_fnc_worldScan;

// Get version
call Root_fnc_getVersion;
```

### Enable Debug Logging

**In config.cpp**:
```cpp
class logging {
    level = "DEBUG";    // Most verbose
    arma_console = 1;   // Print to Arma console
};
```

**Runtime** (if supported):
```sqf
BATCOM setVariable ["log_level", "DEBUG"];
```

### Monitor Real-Time

```sqf
// Real-time status display
[] spawn {
    while {true} do {
        hintSilent format [
            "BATCOM Status\n" +
            "Enabled: %1\n" +
            "Groups: %2\n" +
            "Objectives: %3\n" +
            "Last Decision: %4s ago",
            call BATCOM_fnc_isEnabled,
            count (BATCOM get "controlled_groups"),
            count (BATCOM get "objectives"),
            round (diag_tickTime - (BATCOM get "last_decision_time"))
        ];
        sleep 2;
    };
};
```

### Log Analysis

**Search for errors**:
```bash
# Find all ERROR messages
grep "ERROR" @BATCOM/logs/batcom_*.log

# Find API failures
grep "API call failed" @BATCOM/logs/*.log

# Find validation failures
grep "validation failed" @BATCOM/logs/*.log
```

**Check token usage trends**:
```bash
cat @BATCOM/token_usage.json | python -m json.tool
```

---

## Getting Help

### Before Asking for Help

1. **Check this guide** - Most issues covered here
2. **Review logs** - Error messages often explain the problem
3. **Test with minimal mission** - Isolate the issue
4. **Verify installation** - Run diagnostics above
5. **Check provider status** - Ensure LLM service is up

### Information to Provide

When reporting issues, include:

1. **BATCOM version**: `call Root_fnc_getVersion`
2. **Arma 3 version**: Game version
3. **Server or client**: Where issue occurs
4. **Operating system**: Windows/Linux
5. **Mods loaded**: Full mod list
6. **Error messages**: From RPT and Python logs
7. **Reproduction steps**: How to trigger the issue
8. **Config snippets**: Relevant configuration
9. **Mission code**: Initialization code if mission-specific

### Where to Get Help

1. **GitHub Issues**: https://github.com/A3-Root/batcom/issues
   - Bug reports
   - Feature requests
   - Technical issues

2. **Documentation**: Check all wiki pages
   - [API Reference](API-Reference.md)
   - [Mission Setup Guide](Mission-Setup-Guide.md)
   - [Server Setup Guide](Server-Setup-Guide.md)

3. **Discord/Forums**: Community support (if available)

### Template Bug Report

```markdown
**BATCOM Version**: [e.g., 1.0.0]
**Arma 3 Version**: [e.g., 2.14]
**Operating System**: [Windows 10 / Ubuntu 20.04]
**Server/Client**: [Dedicated Server / Client]

**Description**:
Brief description of the issue.

**Steps to Reproduce**:
1. Step one
2. Step two
3. ...

**Expected Behavior**:
What should happen

**Actual Behavior**:
What actually happens

**Error Messages**:
```
Paste error messages here
```

**Configuration**:
```sqf
// Paste relevant config
```

**Logs**:
Attach RPT log and Python log files
```

---

## Checklist for Common Issues

### BATCOM Won't Load
- [ ] CBA_A3 installed and loaded first
- [ ] Correct folder structure (@BATCOM/addons/root_batcom.pbo exists)
- [ ] Included in -serverMod parameter
- [ ] File permissions correct (Linux)
- [ ] No PBO corruption

### LLM Not Connecting
- [ ] API key set correctly
- [ ] Internet connectivity working
- [ ] Firewall allows HTTPS (port 443)
- [ ] Provider service is up
- [ ] Correct provider and model configured
- [ ] Timeout setting sufficient

### AI Not Moving Groups
- [ ] Commander deployed
- [ ] Correct sides configured
- [ ] Objectives defined
- [ ] Groups are AI-controlled (not player)
- [ ] Groups within AO bounds
- [ ] No sandbox validation errors

### Performance Issues
- [ ] Scan intervals not too frequent
- [ ] Controlled groups limited appropriately
- [ ] Decision interval sufficient (30s+)
- [ ] AO size reasonable
- [ ] Logging level appropriate (INFO/WARN)
- [ ] Token usage reasonable (check caching)

---

## See Also

- [Server Setup Guide](Server-Setup-Guide.md) - Installation and configuration
- [Mission Setup Guide](Mission-Setup-Guide.md) - Mission integration
- [LLM Configuration Guide](LLM-Configuration-Guide.md) - Provider setup
- [API Reference](API-Reference.md) - Function documentation

---

**Last Updated**: 2025-12-05
