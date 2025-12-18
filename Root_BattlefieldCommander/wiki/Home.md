# BATCOM Wiki - Documentation Hub

Welcome to the comprehensive documentation for **BATCOM** (Root's Battlefield Commander) - an advanced Arma 3 mod that integrates Large Language Models as intelligent AI commanders.

## Quick Navigation

### Getting Started
- **[Server Setup Guide](Server-Setup-Guide.md)** - Install and configure BATCOM on your server
- **[Mission Setup Guide](Mission-Setup-Guide.md)** - Integrate BATCOM into your missions
- **[LLM Configuration Guide](LLM-Configuration-Guide.md)** - Configure AI providers and optimize costs

### Reference Documentation
- **[API Reference](API-Reference.md)** - Complete API documentation for all functions
- **[Command Reference](Command-Reference.md)** - All tactical commands the AI can issue
- **[Architecture Overview](Architecture-Overview.md)** - System design and technical architecture

### Advanced Topics
- **[Troubleshooting Guide](Troubleshooting-Guide.md)** - Debug issues and optimize performance
- **[Task Examples](../docs/task-examples.md)** - Comprehensive objective and task examples
- **[Admin Commands](../docs/admin-commands.md)** - Complete admin command reference

## What is BATCOM?

BATCOM (short for Battlefield Commander) is a sophisticated AI commander system that uses Large Language Models (LLMs) to make real-time tactical decisions in Arma 3. The AI analyzes the battlefield situation, evaluates objectives, and issues commands to units based on mission goals and tactical constraints.

### Key Features

- **Multi-Provider LLM Support** - Gemini, OpenAI, Claude, DeepSeek, Azure, and local models
- **Intelligent Context Caching** - 90% cost reduction with Gemini's native caching
- **Real-Time Tactical Decisions** - Continuous battlefield analysis and command generation
- **8 Command Types** - Move, defend, patrol, seek & destroy, transport, escort, fire support, deploy assets
- **Flexible Task System** - Simple or advanced objective definitions with priorities
- **Safety & Constraints** - Command validation, AO bounds, resource limits, spawn limits
- **Complete Audit Trail** - Order history, API call logging, token usage tracking
- **Post-Mission Analysis** - Comprehensive data for LLM self-review

### System Architecture

```
┌─────────────────┐
│  Arma 3 (SQF)   │  ← World scanning, command execution, configuration
└────────┬────────┘
         │ Pythia Extension (Python bridge)
         ↓
┌─────────────────┐
│  Python Core    │  ← Decision loop, LLM integration, command validation
└────────┬────────┘
         │ HTTPS API calls
         ↓
┌─────────────────┐
│  LLM Provider   │  ← Gemini, OpenAI, Claude, DeepSeek, Azure, Local
└─────────────────┘
```

## Quick Start

1. **Install Prerequisites**
   - Arma 3 Dedicated Server
   - CBA_A3
   - LLM API Key

2. **Configure Server**
   ```
   -serverMod=@CBA_A3;@BATCOM
   ```

3. **Set API Key**
   ```sqf
   ["setLLMConfig", createHashMapFromArray [
       ["provider", "gemini"],
       ["api_key", "YOUR_API_KEY"]
   ], true] call Root_fnc_batcomInit;
   ```

4. **Initialize Mission**
   ```sqf
   ["commanderBrief", "Your mission description", true] call Root_fnc_batcomInit;
   ["commanderSides", ["EAST"], nil] call Root_fnc_batcomInit;
   ```

5. **Add Tasks & Deploy**
   ```sqf
   ["commanderTask", createHashMapFromArray [
       ["description", "Defend the airfield"],
       ["priority", 10],
       ["position", getPos someMarker],
       ["radius", 200]
   ], nil] call Root_fnc_batcomInit;

   ["deployCommander", true] call Root_fnc_batcomInit;
   ```

## Documentation Structure

This wiki is organized into several comprehensive guides:

### Setup Guides
These guides walk you through installation and configuration:
- Server Setup - Installing BATCOM and dependencies
- Mission Setup - Integrating BATCOM into your scenarios
- LLM Configuration - Choosing and configuring AI providers

### Reference Guides
Complete technical references for developers and advanced users:
- API Reference - All SQF and Python functions
- Command Reference - Tactical commands and their parameters
- Architecture Overview - System design and data flow

### Operational Guides
Guides for running and maintaining BATCOM:
- Troubleshooting - Common issues and solutions
- Performance Optimization - Reduce costs and improve responsiveness
- Monitoring & Logging - Track AI decisions and debug issues

## Support & Resources

- **GitHub Repository**: https://github.com/77th-JSOC/BATCOM
- **Issue Tracker**: https://github.com/77th-JSOC/BATCOM/issues
- **Quick Start Guide**: [docs/quick-start.md](../docs/quick-start.md)
- **Task Examples**: [docs/task-examples.md](../docs/task-examples.md)

## License

See [LICENSE](../LICENSE) file for licensing information.

---

**Last Updated**: 2025-12-05
