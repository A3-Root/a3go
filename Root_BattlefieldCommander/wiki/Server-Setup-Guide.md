# Server Setup Guide

Complete guide to installing and configuring BATCOM on your Arma 3 dedicated server.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Verification](#verification)
- [Performance Tuning](#performance-tuning)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Updating](#updating)

---

## Overview

BATCOM requires:
1. **Arma 3 Dedicated Server**
2. **CBA_A3** (Community Base Addons)
3. **BATCOM Mod** (`@BATCOM`)
4. **LLM API Key** (Gemini, OpenAI, etc.)
5. **Internet Connectivity** (for LLM API calls)

### Architecture

```
Arma 3 Server
    ↓
CBA_A3 (required framework)
    ↓
BATCOM Addon (@BATCOM)
    ↓
Internet → LLM Provider API
```

---

## Prerequisites

### System Requirements

**Minimum**:
- Arma 3 Dedicated Server (latest stable version)
- Windows Server 2016+ or Linux (Ubuntu 20.04+)
- 4GB RAM (8GB recommended)
- Internet connection with stable latency (<200ms)
- Outbound HTTPS access (port 443)

**Recommended**:
- 8GB+ RAM
- SSD storage
- Dedicated network connection
- Low-latency internet (<50ms to LLM provider)

### Required Software

1. **Arma 3 Dedicated Server**
   - Steam app ID: 233780
   - Latest stable version
   - [Installation Guide](https://community.bistudio.com/wiki/Arma_3:_Dedicated_Server)

2. **CBA_A3**
   - Download from [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=450814997)
   - Or use Steam Workshop Downloader
   - Or direct download from [CBA GitHub](https://github.com/CBATeam/CBA_A3/releases)

3. **LLM API Access**
   - Recommended: [Google Gemini API key](https://makersuite.google.com/app/apikey) (free tier available)
   - Alternative: OpenAI, Anthropic, DeepSeek, etc.
   - See: [LLM Configuration Guide](LLM-Configuration-Guide.md)

---

## Installation Methods

### Method 1: Steam Workshop (Recommended for Windows)

#### Step 1: Download BATCOM

**Option A: Steam Workshop Downloader**
1. Install [Steam Workshop Downloader](https://github.com/shadoxxhd/steamworkshopdownloader)
2. Download BATCOM (Workshop ID: TBD)
3. Extract to server mods folder

**Option B: Manual from Local Client**
1. Subscribe to BATCOM in Steam Workshop
2. Find mod in: `steamapps/workshop/content/107410/`
3. Copy to server: `arma3server/mods/@BATCOM/`

**Option C: SteamCMD**
```bash
# Linux
steamcmd +login anonymous +workshop_download_item 107410 WORKSHOP_ID +quit

# Windows
steamcmd.exe +login anonymous +workshop_download_item 107410 WORKSHOP_ID +quit
```

#### Step 2: Download CBA_A3

**Workshop ID**: 450814997

Same process as BATCOM, or use existing CBA_A3 installation.

#### Step 3: Organize Mods

```
arma3server/
├── arma3server.exe (or arma3server_x64.exe)
├── mods/
│   ├── @CBA_A3/
│   │   ├── addons/
│   │   ├── keys/
│   │   └── mod.cpp
│   └── @BATCOM/
│       ├── addons/
│       │   └── root_batcom.pbo
│       ├── batcom/
│       │   └── (Python backend files)
│       ├── keys/
│       └── mod.cpp
```

---

### Method 2: GitHub Release (Recommended for Linux)

#### Step 1: Download Latest Release

```bash
cd /path/to/arma3server/mods

# Download BATCOM
wget https://github.com/A3-Root/batcom/releases/latest/download/BATCOM.zip

# Extract
unzip BATCOM.zip -d @BATCOM
```

#### Step 2: Install CBA_A3

```bash
# Download from GitHub
wget https://github.com/CBATeam/CBA_A3/releases/latest/download/cba_a3.zip

# Extract
unzip cba_a3.zip -d @CBA_A3
```

#### Step 3: Set Permissions (Linux)

```bash
chmod -R 755 @BATCOM
chmod -R 755 @CBA_A3
```

---

### Method 3: Build from Source

For developers or contributors.

#### Prerequisites

- **HEMTT** (Hephaestus - Arma 3 build tool)
- **Git**
- **Python 3.10+**

#### Step 1: Clone Repository

```bash
git clone https://github.com/A3-Root/batcom.git
cd batcom
```

#### Step 2: Build with HEMTT

**Windows**:
```batch
hemtt build
```

**Linux**:
```bash
hemtt build
```

#### Step 3: Copy Built Files

```bash
# Built addon is in .hemttout/build/@root_batcom
cp -r .hemttout/build/@root_batcom /path/to/arma3server/mods/@BATCOM
```

---

## Configuration

### Step 1: Configure Server Startup

Edit your server startup script to load mods.

#### Windows (server.bat)

```batch
@echo off
set SERVER_MOD_LIST=@CBA_A3;@BATCOM
set CLIENT_MOD_LIST=@CBA_A3

arma3server_x64.exe ^
    -port=2302 ^
    -config=server.cfg ^
    -cfg=basic.cfg ^
    -profiles=ServerProfile ^
    -serverMod=%SERVER_MOD_LIST% ^
    -mod=%CLIENT_MOD_LIST% ^
    -world=empty ^
    -autoinit
```

#### Linux (server.sh)

```bash
#!/bin/bash

SERVER_MOD_LIST="@CBA_A3;@BATCOM"
CLIENT_MOD_LIST="@CBA_A3"

./arma3server_x64 \
    -port=2302 \
    -config=server.cfg \
    -cfg=basic.cfg \
    -profiles=ServerProfile \
    -serverMod="$SERVER_MOD_LIST" \
    -mod="$CLIENT_MOD_LIST" \
    -world=empty \
    -autoinit
```

**Important Notes**:
- Use `-serverMod` for @BATCOM (server-only, better security)
- Use `-mod` if clients also need BATCOM loaded (usually not needed)
- CBA_A3 can be in either `-mod` or `-serverMod`
- Semicolon `;` separates mods (Windows), colon `:` on Linux with quotes

### Step 2: Configure LLM API Key

**Option A: Environment Variable (Recommended)**

**Windows**:
```batch
set GEMINI_API_KEY=YOUR_API_KEY_HERE
server.bat
```

**Linux**:
```bash
export GEMINI_API_KEY=YOUR_API_KEY_HERE
./server.sh
```

**Persistent (Linux)**:
Edit `/etc/environment` or `.bashrc`:
```bash
echo 'export GEMINI_API_KEY=YOUR_API_KEY_HERE' >> ~/.bashrc
source ~/.bashrc
```

**Persistent (Windows)**:
1. Open System Properties → Advanced → Environment Variables
2. Add new system variable:
   - Name: `GEMINI_API_KEY`
   - Value: `YOUR_API_KEY_HERE`

**Option B: Configuration File**

Edit `@BATCOM/batcom/config/guardrails.json`:

```json
{
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "api_key": "YOUR_API_KEY_HERE",
    "timeout": 30,
    "min_interval": 10
}
```

**Security Warning**: Only use this method if the file is secured (proper permissions, not in version control).

**Option C: In-Game Configuration**

Configure via mission init.sqf (see [Mission Setup Guide](Mission-Setup-Guide.md)):

```sqf
["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_API_KEY"]
], true] call Root_fnc_batcomInit;
```

### Step 3: Configure BATCOM Settings (Optional)

Edit `@BATCOM/addons/main/config.cpp` (requires rebuilding) or use runtime overrides.

#### Key Settings

**Logging**:
```cpp
class logging {
    level = "INFO";          // DEBUG, INFO, WARN, ERROR
    arma_console = 0;        // 0 = disabled, 1 = enabled
};
```

**AI Configuration**:
```cpp
class ai {
    enabled = 1;                     // 0 = disabled, 1 = enabled
    provider = "gemini";             // gemini, openai, anthropic, etc.
    model = "gemini-2.5-flash-lite"; // Model name
    timeout = 30;                    // API timeout (seconds)
    min_interval = 30.0;             // Min seconds between LLM calls
};
```

**Safety Limits**:
```cpp
class safety {
    sandbox_enabled = 1;
    max_groups_per_objective = 500;
    max_units_per_side = 500;
    max_controlled_groups = 500;
};
```

**Scan Intervals**:
```cpp
class scan {
    tick = 2.0;           // World scan every 2 seconds
    ai_groups = 5.0;      // AI group scan every 5 seconds
    players = 3.0;        // Player scan every 3 seconds
    objectives = 5.0;     // Objective check every 5 seconds
};
```

### Step 4: Configure Firewall

Ensure outbound HTTPS (port 443) is allowed for LLM API calls.

**Linux (ufw)**:
```bash
sudo ufw allow out 443/tcp
```

**Windows Firewall**:
1. Open Windows Defender Firewall
2. Advanced Settings → Outbound Rules
3. Ensure HTTPS (port 443) is allowed

---

## Verification

### Step 1: Check Server Startup

Start your server and check the console/logs for:

```
[BATCOM] Initializing...
[BATCOM] Version: X.X.X
[BATCOM] CBA loaded: true
[BATCOM] Configuration loaded
[BATCOM] Ready
```

**Log Locations**:
- **Windows**: `ServerProfile/arma3server_*.rpt`
- **Linux**: `ServerProfile/arma3server_*.rpt`

### Step 2: Test in Debug Console

Connect to server and open debug console (requires admin privileges):

```sqf
// Test BATCOM is loaded
call Root_fnc_testPythia;

// Expected output: true or success message
```

```sqf
// Test LLM connection
private _result = call Root_fnc_testGeminiConnection;
systemChat _result;

// Expected: "Connection successful" or similar
```

### Step 3: Test Basic Mission

Create test mission with minimal setup:

```sqf
// init.sqf
waitUntil {!isNil "Root_fnc_batcomInit"};

["setLLMConfig", createHashMapFromArray [
    ["provider", "gemini"],
    ["api_key", "YOUR_KEY"]
], true] call Root_fnc_batcomInit;

["commanderBrief", "Test mission", true] call Root_fnc_batcomInit;
["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;

["commanderTask", createHashMapFromArray [
    ["description", "Test objective"],
    ["priority", 5],
    ["position", [0, 0, 0]],
    ["radius", 500]
], nil] call Root_fnc_batcomInit;

["deployCommander", true] call Root_fnc_batcomInit;

// Check status after 60 seconds
[] spawn {
    sleep 60;
    private _enabled = call BATCOM_fnc_isEnabled;
    systemChat format ["Commander enabled: %1", _enabled];
};
```

### Step 4: Monitor Performance

Watch for:
- **FPS**: Should remain stable
- **Memory**: Monitor for leaks
- **Network**: Check for excessive API calls
- **Logs**: No critical errors

---

## Performance Tuning

### CPU Optimization

**Reduce Scan Frequency**:
```cpp
class scan {
    tick = 3.0;        // Increase from 2.0 to 3.0
    ai_groups = 10.0;  // Increase from 5.0
};
```

**Limit Controlled Groups**:
```cpp
class runtime {
    max_controlled_groups = 100;  // Reduce from 500
};
```

### Memory Optimization

**Reduce Logging**:
```cpp
class logging {
    level = "WARN";    // Only log warnings and errors
    arma_console = 0;  // Disable console logging
};
```

**Limit Command Queue**:
```cpp
class runtime {
    max_commands_per_tick = 20;  // Reduce from 30
};
```

### Network Optimization

**Reduce LLM Call Frequency**:
```cpp
class ai {
    min_interval = 60.0;  // Increase from 30.0
};
```

**Use Faster LLM Models**:
```json
{
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite"  // Fastest model
}
```

### Recommended Settings by Server Size

**Small Server (10-20 players)**:
```cpp
max_controlled_groups = 50;
max_units_per_side = 200;
min_interval = 30.0;
tick = 2.0;
```

**Medium Server (20-50 players)**:
```cpp
max_controlled_groups = 100;
max_units_per_side = 300;
min_interval = 45.0;
tick = 3.0;
```

**Large Server (50+ players)**:
```cpp
max_controlled_groups = 150;
max_units_per_side = 400;
min_interval = 60.0;
tick = 4.0;
```

---

## Security Considerations

### API Key Protection

**Best Practices**:
1. **Use Environment Variables** - Never store keys in config files committed to version control
2. **Limit File Permissions** - Restrict access to config files containing keys
3. **Rotate Keys Regularly** - Change API keys periodically
4. **Monitor Usage** - Watch for unauthorized API calls
5. **Use Separate Keys** - Different keys for dev/staging/production

**Linux Permissions**:
```bash
# Restrict config file access
chmod 600 @BATCOM/batcom/config/guardrails.json
chown serveruser:servergroup @BATCOM/batcom/config/guardrails.json
```

**Windows Permissions**:
1. Right-click `guardrails.json` → Properties → Security
2. Remove access for all users except server administrator
3. Apply permissions

### Network Security

**Firewall Rules**:
- Allow outbound HTTPS (443) to LLM provider IPs only
- Block unauthorized outbound connections
- Monitor for unusual traffic patterns

**IP Whitelisting** (if available):
```bash
# Example: Allow only Google Gemini IPs
# Check provider documentation for IP ranges
```

### Audit Logging

Enable comprehensive logging for security auditing:

```cpp
class safety {
    audit_log = 1;  // Enable audit logging
};
```

**Log Locations**:
- `@BATCOM/logs/batcom_*.log` - General logs
- `@BATCOM/apicall.*.log` - API call logs
- `@BATCOM/token_usage.json` - Token usage tracking

**Monitor logs** for:
- Unexpected API calls
- Failed authentication attempts
- Unusual command patterns
- Error spikes

---

## Troubleshooting

### BATCOM Not Loading

**Symptoms**:
- No BATCOM messages in logs
- Functions not defined: `Root_fnc_batcomInit` is nil

**Checks**:
```sqf
// Check if CBA is loaded
if (isClass (configFile >> "CfgPatches" >> "cba_main")) then {
    systemChat "CBA loaded";
} else {
    systemChat "CBA NOT loaded";
};

// Check if BATCOM is loaded
if (isClass (configFile >> "CfgPatches" >> "root_batcom")) then {
    systemChat "BATCOM loaded";
} else {
    systemChat "BATCOM NOT loaded";
};
```

**Solutions**:
1. Verify mod folder structure is correct
2. Check server startup command includes `-serverMod=@CBA_A3;@BATCOM`
3. Ensure CBA_A3 is loaded before BATCOM
4. Check file permissions (Linux)
5. Review server RPT logs for errors

### LLM Connection Failing

**Symptoms**:
- "Connection timeout" errors
- "Invalid API key" errors
- No AI commands issued

**Debug**:
```sqf
call Root_fnc_testGeminiConnection;
```

**Solutions**:
1. Verify API key is correct
2. Check internet connectivity: `ping google.com` or `curl https://generativelanguage.googleapis.com`
3. Verify firewall allows outbound HTTPS
4. Check API quota hasn't been exceeded
5. Try alternative provider

**Check Logs**:
```bash
# View recent errors
tail -n 100 @BATCOM/logs/batcom_*.log | grep ERROR
```

### High Server Load

**Symptoms**:
- Low FPS
- High CPU usage
- Lag spikes

**Diagnostics**:
```sqf
// Check controlled groups
private _groups = BATCOM get "controlled_groups";
systemChat format ["Controlled groups: %1", count _groups];

// Check decision timing
diag_log format ["Last decision: %1s ago",
    diag_tickTime - (BATCOM get "last_decision_time")];
```

**Solutions**:
1. Reduce scan frequency (increase tick values)
2. Limit max_controlled_groups
3. Increase min_interval for LLM calls
4. Reduce AO size in missions
5. Disable BATCOM during peak player count

### High API Costs

**Monitor Usage**:
```bash
cat @BATCOM/token_usage.json
```

**Optimize**:
1. Enable Gemini caching (automatic)
2. Increase `min_interval` to 60+ seconds
3. Reduce number of objectives in missions
4. Limit AO size
5. Switch to cheaper provider

See: [LLM Configuration Guide - Cost Optimization](LLM-Configuration-Guide.md#cost-optimization)

### Permission Issues (Linux)

**Symptoms**:
- "Permission denied" errors
- BATCOM fails to write logs

**Fix Permissions**:
```bash
# Set ownership
chown -R serveruser:servergroup @BATCOM

# Set permissions
chmod -R 755 @BATCOM
chmod -R 777 @BATCOM/logs      # Log directory needs write access
chmod 600 @BATCOM/batcom/config/guardrails.json  # Secure config
```

---

## Updating

### Update Process

#### Step 1: Backup Current Installation

```bash
# Linux
cp -r @BATCOM @BATCOM.backup

# Windows
robocopy @BATCOM @BATCOM.backup /E
```

#### Step 2: Stop Server

```bash
# Gracefully shutdown server
# Or use RCON/server manager
```

#### Step 3: Download New Version

**From GitHub**:
```bash
wget https://github.com/A3-Root/batcom/releases/latest/download/BATCOM.zip
unzip -o BATCOM.zip -d @BATCOM
```

**From Steam Workshop**:
Re-download via SteamCMD or Workshop downloader.

#### Step 4: Preserve Configuration

**Important files to preserve**:
- `@BATCOM/batcom/config/guardrails.json` (if contains API keys)
- Any custom configuration files

```bash
# Copy config back
cp @BATCOM.backup/batcom/config/guardrails.json @BATCOM/batcom/config/
```

#### Step 5: Verify Update

```bash
# Check version
grep "version" @BATCOM/mod.cpp
```

#### Step 6: Restart Server

Start server with updated BATCOM.

#### Step 7: Test

```sqf
// In debug console
call Root_fnc_testPythia;
call Root_fnc_testGeminiConnection;
```

### Breaking Changes

Check release notes for breaking changes:
- Configuration format changes
- API changes
- New dependencies
- Required Arma 3 version

---

## Monitoring & Maintenance

### Regular Checks

**Daily**:
- Monitor server logs for errors
- Check API usage and costs
- Verify AI is functioning in active missions

**Weekly**:
- Review token_usage.json for cost trends
- Check for BATCOM updates
- Rotate log files if needed

**Monthly**:
- Rotate API keys
- Review and optimize configuration
- Update to latest BATCOM version

### Log Management

**Rotate Logs** (Linux):
```bash
# Add to logrotate
cat > /etc/logrotate.d/batcom << EOF
/path/to/@BATCOM/logs/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF
```

**Clean Old Logs**:
```bash
# Delete logs older than 30 days
find @BATCOM/logs/ -name "*.log" -mtime +30 -delete
```

### Performance Monitoring

**Key Metrics**:
- Server FPS (target: >30 FPS)
- Memory usage (watch for leaks)
- Network bandwidth (API calls)
- Token usage (cost tracking)

**Tools**:
- Arma 3 built-in profiling
- Server RPT logs
- BATCOM token_usage.json
- Provider API dashboards

---

## Best Practices

### 1. Use Environment Variables for API Keys

Never commit keys to config files.

### 2. Start with Conservative Settings

Begin with:
- `min_interval = 60`
- `max_controlled_groups = 50`
- `tick = 3.0`

Optimize as needed.

### 3. Test in Development Environment

Always test updates in a dev server before production.

### 4. Monitor Costs

Set billing alerts on LLM provider platforms.

### 5. Keep Logs Enabled

At minimum, keep `level = "WARN"` for error tracking.

### 6. Regular Updates

Stay current with BATCOM releases for bug fixes and improvements.

### 7. Document Your Configuration

Keep notes on custom settings and why they were chosen.

---

## Support

### Getting Help

1. **Check Wiki Documentation** - Most issues covered here
2. **Review Server Logs** - Errors usually logged with context
3. **Test Configuration** - Use debug functions
4. **GitHub Issues** - [Report bugs](https://github.com/A3-Root/batcom/issues)

### Useful Debug Commands

```sqf
// Test Pythia
call Root_fnc_testPythia;

// Test LLM connection
call Root_fnc_testGeminiConnection;

// Check initialization
call BATCOM_fnc_debugInit;

// Check if enabled
call BATCOM_fnc_isEnabled;

// Get token stats
call Root_fnc_getTokenStats;
```

---

## Quick Reference

### Startup Command Template

**Windows**:
```batch
arma3server_x64.exe -port=2302 -config=server.cfg -serverMod=@CBA_A3;@BATCOM
```

**Linux**:
```bash
./arma3server_x64 -port=2302 -config=server.cfg -serverMod=@CBA_A3;@BATCOM
```

### Essential Files

```
@BATCOM/
├── addons/
│   └── root_batcom.pbo          # Main addon
├── batcom/
│   ├── config/
│   │   └── guardrails.json      # LLM configuration
│   └── (other Python files)
├── logs/                         # Log directory
├── keys/                         # Signing keys
└── mod.cpp                       # Mod metadata
```

### Environment Variables

```bash
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

---

## See Also

- [Mission Setup Guide](Mission-Setup-Guide.md) - Integrate into missions
- [LLM Configuration Guide](LLM-Configuration-Guide.md) - Configure AI providers
- [API Reference](API-Reference.md) - Complete function documentation
- [Troubleshooting Guide](Troubleshooting-Guide.md) - Detailed debugging

---

**Last Updated**: 2025-12-05
