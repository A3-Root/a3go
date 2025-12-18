#include "..\script_component.hpp"
/*
 * Author: Root
 * Convert hashmap to nested array for Pythia compatibility
 *
 * Arguments:
 * 0: HashMap <HASHMAP>
 *
 * Return Value:
 * Array of [key, value] pairs <ARRAY>
 *
 * Example:
 * _array = [_hashmap] call BATCOM_fnc_hashmapToArray;
 */

params [
    ["_hashmap", createHashMap, [createHashMap]]
];

private _debug = missionNamespace getVariable [QGVAR(debugMode), false];
private _dlog = {
    params ["_msg", "_debugFlag"];
    if (_debugFlag) then {diag_log _msg;};
};

["BATCOM: >> hashmapToArray START", _debug] call _dlog;
[format ["BATCOM: >> Input type: %1, key count: %2", typeName _hashmap, count (keys _hashmap)], _debug] call _dlog;
[format ["BATCOM: >> Keys: %1", keys _hashmap], _debug] call _dlog;

private _result = [];
private _processedKeys = 0;

try {
    if (!(_hashmap isEqualType createHashMap)) then {
        throw format ["Expected HASHMAP, got %1", typeName _hashmap];
    };

    {
        private _key = _x;
        private _value = _y;
        private _valueType = typeName _value;

        [format ["BATCOM: >> Processing key '%1', value type: %2", _key, _valueType], _debug] call _dlog;

        // Recursively convert nested hashmaps
        if (_value isEqualType createHashMap) then {
            [format ["BATCOM: >> '%1' is a nested hashmap, converting recursively...", _key], _debug] call _dlog;
            _value = [_value] call FUNC(hashmapToArray);
        };

        // Recursively convert arrays containing hashmaps
        if (_value isEqualType []) then {
            private _arrayCount = count _value;
            [format ["BATCOM: >> '%1' is an array with %2 elements", _key, _arrayCount], _debug] call _dlog;
            _value = _value apply {
                if (_x isEqualType createHashMap) then {
                    [_x] call FUNC(hashmapToArray)
                } else {
                    _x
                }
            };
        };

        _result pushBack [_key, _value];
        _processedKeys = _processedKeys + 1;
        [format ["BATCOM: >> ✓ Processed key '%1' (%2/%3)", _key, _processedKeys, count (keys _hashmap)], _debug] call _dlog;
    } forEach _hashmap;

    [format ["BATCOM: >> hashmapToArray SUCCESS - converted %1 keys to array", count _result], _debug] call _dlog;
} catch {
    [format ["BATCOM: >> ✗✗✗ ERROR in hashmapToArray: %1", _exception], _debug] call _dlog;
    _result = [];
};

[format ["BATCOM: >> hashmapToArray END - returning array with %1 elements", count _result], _debug] call _dlog;
_result
