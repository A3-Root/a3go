#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {"cba_main"};
        author = "Root";
        authors[] = {"Root"};
        url = "https://github.com/A3-Root/batcom";
        VERSION_CONFIG;
    };
};

class Extended_PreInit_EventHandlers {
    class ADDON {
        init = QUOTE(call compile preprocessFileLineNumbers '\z\root_batcom\addons\main\XEH_preInit.sqf');
    };
};

class Extended_PostInit_EventHandlers {
    class ADDON {
        init = QUOTE(call compile preprocessFileLineNumbers '\z\root_batcom\addons\main\XEH_postInit.sqf');
    };
};

// Expose admin functions globally for easy console access
class CfgFunctions {
    class Root {
        class batcom {
            file = QPATHTOF(functions);
            class batcomInit {};
            class batcomDebug {};
            class testPythia {};
            class testGeminiConnection {};
            class debugInit {};
            class batcomSetAOBoundary {};
            class batcomAOLifecycle {};
            class batcomAutoInit {};
            class batcomResourcePoolUI {};
            class trackAOObjectives {};
            class getResourcePoolTemplate {};
            class getDefaultAssetClasses {};
            class commanderStartAO {};
            class commanderEndAO {};
            class initCasualtyTracking {};
            class trackObjectiveContributions {};
            class aoProgress {};
            class taskComplete {};
            class killCommander {};
        };
    };
    // Alias for easier access
    class BATCOM {
        class batcom {
            file = QPATHTOF(functions);
            class killCommander {};
        };
    };
};

class CfgBATCOM {
    class logging {
        level = "INFO";
        arma_console = 0;
    };

    class scan {
        tick = 2.0;
        ai_groups = 5.0;
        players = 3.0;
        objectives = 5.0;
    };

    class runtime {
        max_messages_per_tick = 50;
        max_commands_per_tick = 30;
        max_controlled_groups = 500;
    };

    class ai {
        enabled = 1;
        provider = "gemini";
        model = "gemini-2.5-flash-lite";
        timeout = 30;
        min_interval = 30.0;  // Minimum seconds between LLM calls (rate limiting)

        // Thinking/Reasoning configuration
        thinking_enabled = 1;  // 0=disabled, 1=enabled
        thinking_mode = "openai_compat";  // "native_sdk" or "openai_compat"
        thinking_budget = -1;  // -1=dynamic (recommended), 0=disabled, 512-24576=explicit tokens (Gemini 2.5)
        thinking_level = "low";  // "low" or "high" (Gemini 3 only)
        reasoning_effort = "medium";  // "minimal"|"low"|"medium"|"high"|"none" (OpenAI compat mode)
        include_thoughts = 1;  // 0=exclude thought summaries, 1=include in response
        log_thoughts_to_file = 1;  // 0=console only, 1=log to per-AO files
    };

    class safety {
        sandbox_enabled = 1;
        max_groups_per_objective = 500;
        max_units_per_side = 500;  // Maximum units that can be spawned per side
        allowed_commands[] = {"move_to", "defend_area", "patrol_route", "seek_and_destroy", "transport_group", "escort_group", "fire_support", "deploy_asset"};
        blocked_commands[] = {};
        audit_log = 1;
    };
};
