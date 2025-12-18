#include "..\script_component.hpp"
/*
 * Author: Root
 * Get token usage statistics from the LLM
 *
 * This function retrieves comprehensive token usage statistics including:
 * - Last call stats
 * - Per minute usage
 * - Per hour usage
 * - Per day usage
 * - Total cumulative usage
 * - Averages per call
 *
 * Statistics are also written to: @BATCOM/token_usage.jsonl
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Hashmap with token statistics <HASHMAP>
 *
 * Example:
 * call BATCOM_fnc_getTokenStats;
 *
 * // Get stats and display them
 * private _stats = call BATCOM_fnc_getTokenStats;
 * systemChat format ["Total LLM calls: %1", _stats get "total" get "calls"];
 * systemChat format ["Total tokens: %1", _stats get "total" get "total"];
 */

if (!isServer) exitWith {
    ["BATCOM", "ERROR", "getTokenStats must be called on server"] call FUNC(logMessage);
    createHashMap
};

["BATCOM", "INFO", "Retrieving token usage statistics..."] call FUNC(logMessage);

// Call Python admin command
private _resultArray = ["batcom.admin_command", ["getTokenStats", nil, false]] call FUNC(pythiaCall);

if (isNil "_resultArray") exitWith {
    ["BATCOM", "ERROR", "Failed to retrieve token stats from Python"] call FUNC(logMessage);
    createHashMap
};

// Convert result array to hashmap
private _result = if (_resultArray isEqualType []) then {
    [_resultArray] call FUNC(arrayToHashmap)
} else {
    createHashMap
};

private _status = _result getOrDefault ["status", ""];

if (_status != "ok") then {
    private _error = _result getOrDefault ["error", "unknown error"];
    ["BATCOM", "ERROR", format ["Failed to get token stats: %1", _error]] call FUNC(logMessage);
    createHashMap
} else {
    ["BATCOM", "INFO", "Token statistics retrieved - check Python logs for formatted output"] call FUNC(logMessage);

    // Extract stats hashmap
    private _statsArray = _result getOrDefault ["stats", []];
    private _stats = if (_statsArray isEqualType []) then {
        [_statsArray] call FUNC(arrayToHashmap)
    } else {
        createHashMap
    };

    // Log summary to game
    if (count _stats > 0) then {
        private _total = _stats getOrDefault ["total", createHashMap];
        if (_total isEqualType createHashMap) then {
            private _totalCalls = _total getOrDefault ["calls", 0];
            private _totalTokens = _total getOrDefault ["total", 0];
            private _totalInput = _total getOrDefault ["input", 0];
            private _totalOutput = _total getOrDefault ["output", 0];

            ["BATCOM", "INFO", format ["Token Stats Summary: %1 calls, %2 total tokens (%3 input, %4 output)",
                _totalCalls, _totalTokens, _totalInput, _totalOutput]] call FUNC(logMessage);
        };
    };

    _stats
};
