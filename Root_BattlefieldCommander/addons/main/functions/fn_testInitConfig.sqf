#include "..\script_component.hpp"
/*
 * Author: Root
 * Test init with actual config to see what's being sent
 *
 * Arguments:
 * None
 *
 * Return Value:
 * None
 *
 * Example:
 * [] call BATCOM_fnc_testInitConfig;
 */

if (!isServer) exitWith {
    diag_log "BATCOM: Test must be run on server";
};

diag_log "========================================";
diag_log "BATCOM: Testing Init Config";
diag_log "========================================";

// Test 1: Simple config (like debug_init)
diag_log "Test 1: Simple config...";
private _simpleConfig = createHashMapFromArray [
    ["logging", createHashMap],
    ["scan", createHashMap],
    ["runtime", createHashMap],
    ["ai", createHashMapFromArray [["enabled", false]]],
    ["safety", createHashMap]
];

private _result1 = try {
    private _response = ["batcom.init", [_simpleConfig]] call FUNC(pythiaCall);
    if (isNil "_response") then {
        throw "batcom.init returned nil for simple config";
    };
    _response
} catch {
    diag_log format ["Exception: %1", _exception];
    nil
};

diag_log format ["Simple config result: %1", _result1];

// Shutdown to reset
if (!isNil "_result1") then {
    ["batcom.shutdown", []] call FUNC(pythiaCall);
    uiSleep 0.5;
};

// Test 2: Config with values
diag_log "";
diag_log "Test 2: Config with values...";
private _fullConfig = createHashMapFromArray [
    ["logging", createHashMapFromArray [
        ["level", "INFO"],
        ["arma_console", 0]
    ]],
    ["scan", createHashMapFromArray [
        ["tick", 2.0],
        ["ai_groups", 5.0],
        ["players", 3.0],
        ["objectives", 5.0]
    ]],
    ["runtime", createHashMapFromArray [
        ["max_messages_per_tick", 50],
        ["max_commands_per_tick", 30],
        ["max_controlled_groups", 500]
    ]],
    ["ai", createHashMapFromArray [
        ["enabled", true],
        ["provider", "gemini"],
        ["model", "gemini-2.5-flash-lite"],
        ["timeout", 30],
        ["min_interval", 10.0]
    ]],
    ["safety", createHashMapFromArray [
        ["sandbox_enabled", true],
        ["max_groups_per_objective", 10],
        ["max_units_per_side", 100],
        ["allowed_commands", ["move_to", "defend_area"]],
        ["blocked_commands", []],
        ["audit_log", true]
    ]]
];

diag_log format ["Full config size: %1 keys", count (keys _fullConfig)];

private _result2 = try {
    private _response = ["batcom.init", [_fullConfig]] call FUNC(pythiaCall);
    if (isNil "_response") then {
        throw "batcom.init returned nil for full config";
    };
    _response
} catch {
    diag_log format ["Exception: %1", _exception];
    nil
};

diag_log format ["Full config result: %1", _result2];

diag_log "========================================";
