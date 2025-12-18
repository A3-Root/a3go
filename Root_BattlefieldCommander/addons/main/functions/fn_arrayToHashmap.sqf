#include "..\script_component.hpp"
/*
 * Author: Root
 * Convert nested array from Pythia back to hashmap
 * This is the reverse of fn_hashmapToArray
 *
 * Arguments:
 * 0: Array of [key, value] pairs <ARRAY>
 *
 * Return Value:
 * Hashmap <HASHMAP>
 *
 * Example:
 * _hashmap = [_array] call BATCOM_fnc_arrayToHashmap;
 */

params [
    ["_array", [], [[]]]
];

private _debug = missionNamespace getVariable [QGVAR(debugMode), false];
private _dlog = {
    params ["_msg", "_debugFlag"];
    if (_debugFlag) then {diag_log _msg;};
};

["BATCOM: << arrayToHashmap START", _debug] call _dlog;
[format ["BATCOM: << Input type: %1, element count: %2", typeName _array, count _array], _debug] call _dlog;

private _result = createHashMap;
private _processedElements = 0;

{
    // Validate that this is a [key, value] pair
    private _isValid = _x isEqualType [] && {count _x == 2};

    if (!_isValid) then {
        diag_log format ["BATCOM: << ERROR: Skipping malformed element %1/%2 (type=%3, count=%4, value=%5)",
            _forEachIndex + 1, count _array, typeName _x,
            if (_x isEqualType []) then {count _x} else {-1}, _x];
    };

    if (_isValid) then {
        private _key = if (count _x > 0) then {_x select 0} else {""};
        private _value = if (count _x > 1) then {_x select 1} else {nil};

        if (isNil "_value") exitWith {
            diag_log format ["BATCOM: << ERROR: _value is nil for key '%1' at element %2", _key, _forEachIndex + 1];
        };

        private _valueType = typeName _value;

        [format ["BATCOM: << Processing element %1/%2: key='%3', value type=%4",
            _forEachIndex + 1, count _array, _key, _valueType], _debug] call _dlog;

        // Recursively convert nested arrays back to hashmaps
        if (_value isEqualType []) then {
            // Check if this is an array of [key, value] pairs (nested hashmap)
            if (count _value > 0 && {(_value select 0) isEqualType []} && {count (_value select 0) == 2}) then {
                [format ["BATCOM: << Checking if '%1' value is a nested hashmap array...", _key], _debug] call _dlog;
                // Check if all elements are [key, value] pairs
                private _isHashmapArray = true;
                {
                    if !(_x isEqualType [] && {count _x == 2}) then {
                        _isHashmapArray = false;
                    };
                } forEach _value;

                if (_isHashmapArray) then {
                    [format ["BATCOM: << '%1' is a nested hashmap array, converting recursively...", _key], _debug] call _dlog;
                    _value = [_value] call FUNC(arrayToHashmap);
                } else {
                    [format ["BATCOM: << '%1' is a regular array, keeping as-is", _key], _debug] call _dlog;
                };
            };
        };

        _result set [_key, _value];
        _processedElements = _processedElements + 1;
        [format ["BATCOM: << ✓ Processed '%1' (%2/%3)", _key, _processedElements, count _array], _debug] call _dlog;
    };
} forEach _array;

[format ["BATCOM: << arrayToHashmap SUCCESS - converted to hashmap with %1 keys", count (keys _result)], _debug] call _dlog;
[format ["BATCOM: << arrayToHashmap END - keys: %1", keys _result], _debug] call _dlog;
_result
