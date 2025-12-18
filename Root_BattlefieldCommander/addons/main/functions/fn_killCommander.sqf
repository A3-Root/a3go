/*
 * Author: Root
 * Emergency stop for BATCOM LLM commander
 *
 * Immediately stops all LLM operations and clears all context/caches/conversation history.
 * Use this when the LLM is misbehaving or when you need a clean restart.
 *
 * This will:
 * - Disable LLM completely (circuit breaker open)
 * - Clear all conversation context and caches
 * - Reset order history
 * - Clear previous AO intelligence
 * - Reset all LLM client state
 *
 * After this, you'll need to either:
 * - Call Root_fnc_deployCommander to restart with fresh state
 * - Restart the mission to reinitialize BATCOM
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Result hashmap with status
 *
 * Example:
 * call Root_fnc_killCommander;
 * call BATCOM_fnc_killCommander;
 *
 * Public: Yes
 */

if (!isServer) exitWith {
    ["Root_fnc_killCommander can only be called on the server"] call Root_fnc_logMessage;
    createHashMapFromArray [["status", "error"], ["error", "Server only"]];
};

// Call Python emergency stop
private _result = ["batcom.batcom_init", ["emergencyStop", [], false]] call py3_fnc_callExtension;

// Convert result from array to hashmap
private _resultHashmap = if (_result isEqualType []) then {
    _result call Root_fnc_arrayToHashmap;
} else {
    _result;
};

// Log result
if ((_resultHashmap getOrDefault ["status", ""]) isEqualTo "ok") then {
    ["EMERGENCY STOP: LLM commander killed and all context cleared"] call Root_fnc_logMessage;
    ["Commander can be restarted with: call Root_fnc_deployCommander;"] call Root_fnc_logMessage;
} else {
    private _error = _resultHashmap getOrDefault ["error", "Unknown error"];
    [format ["EMERGENCY STOP FAILED: %1", _error]] call Root_fnc_logMessage;
};

_resultHashmap
