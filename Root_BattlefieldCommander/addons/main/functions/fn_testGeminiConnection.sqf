#include "..\script_component.hpp"
/*
 * Author: Root
 * Test Gemini LLM connection and display greeting
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Success <BOOL>
 *
 * Example:
 * [] call BATCOM_fnc_testGeminiConnection;
 */

if (!isServer) exitWith {
    diag_log "BATCOM: Test must be run on server";
    false
};

diag_log "BATCOM: Testing Gemini connection...";

// Call Python to test connection
private _resultArray = try {
    private _response = ["batcom.test_gemini_connection", []] call FUNC(pythiaCall);
    if (isNil "_response") then {
        throw "batcom.test_gemini_connection returned nil";
    };
    _response
} catch {
    diag_log format ["BATCOM: ✗ Exception when calling test: %1", _exception];
    nil
};

if (isNil "_resultArray") exitWith {
    diag_log "BATCOM: ✗ ERROR - No response from Python";
    diag_log "BATCOM: Is BATCOM initialized? Run: [] call BATCOM_fnc_init";
    diag_log "BATCOM: Or run diagnostic: [] call Root_fnc_testPythia";
    false
};

// Check if result is an error string
if (_resultArray isEqualType "") exitWith {
    diag_log format ["BATCOM: ✗ ERROR - Python returned string: %1", _resultArray];
    diag_log "BATCOM: This suggests an import or function call error";
    false
};

// Convert result array to hashmap (Pythia doesn't support dict->hashmap)
if (!(_resultArray isEqualType [])) exitWith {
    diag_log format ["BATCOM: ✗ ERROR - Unexpected response type: %1", typeName _resultArray];
    diag_log format ["BATCOM: Response: %1", _resultArray];
    false
};

private _result = [_resultArray] call FUNC(arrayToHashmap);

// Check result
private _status = _result getOrDefault ["status", ""];

if (_status == "ok") then {
    private _model = _result getOrDefault ["model", "gemini-2.5-flash-lite"];
    private _greeting = _result getOrDefault ["greeting", ""];

    diag_log format ["BATCOM: ✓ SUCCESS - Connected to %1", _model];
    diag_log format ["BATCOM: LLM says: %1", _greeting];

    ["BATCOM", "INFO", format ["Gemini test successful: %1", _greeting]] call FUNC(logMessage);

    true
} else {
    private _error = _result getOrDefault ["error", "Unknown error"];

    diag_log format ["BATCOM: ✗ FAILED - %1", _error];

    ["BATCOM", "ERROR", format ["Gemini test failed: %1", _error]] call FUNC(logMessage);

    // Provide helpful hints
    if (_error find "not initialized" >= 0) then {
        diag_log "BATCOM: HINT - Run: [] call BATCOM_fnc_init";
    };

    if (_error find "GEMINI_API_KEY" >= 0) then {
        diag_log "BATCOM: HINT - Set environment variable: GEMINI_API_KEY";
        diag_log "BATCOM: HINT - Restart server after setting the variable";
    };

    if (_error find "disabled" >= 0) then {
        diag_log "BATCOM: HINT - Enable LLM in config.cpp (ai.enabled = 1)";
    };

    false
};
