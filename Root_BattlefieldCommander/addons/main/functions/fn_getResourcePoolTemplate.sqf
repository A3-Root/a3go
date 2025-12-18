#include "..\script_component.hpp"
/*
 * Author: Root
 * Get resource pool template by name
 *
 * Arguments:
 * 0: Side <STRING> - "EAST", "WEST", "GUER", "CIV"
 * 1: Template Name <STRING> - "default", "light", "heavy", "mixed", "minimal"
 *
 * Return Value:
 * Resource pool template <HASHMAP>
 *
 * Example:
 * private _template = ["EAST", "heavy"] call Root_fnc_getResourcePoolTemplate;
 */

params [
    ["_side", "EAST", [""]],
    ["_templateName", "default", [""]]
];

private _sideUpper = toUpper _side;
private _templateLower = toLower _templateName;

// Get side-specific unit classes
private _infantryClasses = [_sideUpper, "infantry_squad"] call FUNC(getDefaultAssetClasses);
private _ifvClasses = [_sideUpper, "ifv"] call FUNC(getDefaultAssetClasses);
private _tankClasses = [_sideUpper, "tank"] call FUNC(getDefaultAssetClasses);
private _heliClasses = [_sideUpper, "attack_heli"] call FUNC(getDefaultAssetClasses);
private _transportHeliClasses = [_sideUpper, "transport_heli"] call FUNC(getDefaultAssetClasses);
private _jetClasses = [_sideUpper, "jet"] call FUNC(getDefaultAssetClasses);
private _droneClasses = [_sideUpper, "drone"] call FUNC(getDefaultAssetClasses);
private _mortarClasses = [_sideUpper, "mortar"] call FUNC(getDefaultAssetClasses);
private _aaClasses = [_sideUpper, "aa_vehicle"] call FUNC(getDefaultAssetClasses);
private _artilleryClasses = [_sideUpper, "artillery"] call FUNC(getDefaultAssetClasses);

// Template definitions
private _templates = createHashMapFromArray [
    // Default balanced template
    ["default", createHashMapFromArray [
        ["infantry_squad", createHashMapFromArray [["max", 8], ["classes", _infantryClasses]]],
        ["ifv", createHashMapFromArray [["max", 4], ["classes", _ifvClasses]]],
        ["tank", createHashMapFromArray [["max", 2], ["classes", _tankClasses]]],
        ["attack_heli", createHashMapFromArray [["max", 2], ["classes", _heliClasses]]],
        ["transport_heli", createHashMapFromArray [["max", 2], ["classes", _transportHeliClasses]]],
        ["drone", createHashMapFromArray [["max", 3], ["classes", _droneClasses]]]
    ]],

    // Light template - infantry and light vehicles
    ["light", createHashMapFromArray [
        ["infantry_squad", createHashMapFromArray [["max", 12], ["classes", _infantryClasses]]],
        ["ifv", createHashMapFromArray [["max", 2], ["classes", _ifvClasses]]],
        ["transport_heli", createHashMapFromArray [["max", 2], ["classes", _transportHeliClasses]]],
        ["drone", createHashMapFromArray [["max", 4], ["classes", _droneClasses]]]
    ]],

    // Heavy template - armor and air support
    ["heavy", createHashMapFromArray [
        ["infantry_squad", createHashMapFromArray [["max", 6], ["classes", _infantryClasses]]],
        ["ifv", createHashMapFromArray [["max", 6], ["classes", _ifvClasses]]],
        ["tank", createHashMapFromArray [["max", 4], ["classes", _tankClasses]]],
        ["attack_heli", createHashMapFromArray [["max", 4], ["classes", _heliClasses]]],
        ["transport_heli", createHashMapFromArray [["max", 2], ["classes", _transportHeliClasses]]],
        ["jet", createHashMapFromArray [["max", 2], ["classes", _jetClasses]]],
        ["aa_vehicle", createHashMapFromArray [["max", 2], ["classes", _aaClasses]]],
        ["artillery", createHashMapFromArray [["max", 1], ["classes", _artilleryClasses]]]
    ]],

    // Mixed template - everything in moderation
    ["mixed", createHashMapFromArray [
        ["infantry_squad", createHashMapFromArray [["max", 8], ["classes", _infantryClasses]]],
        ["ifv", createHashMapFromArray [["max", 3], ["classes", _ifvClasses]]],
        ["tank", createHashMapFromArray [["max", 2], ["classes", _tankClasses]]],
        ["attack_heli", createHashMapFromArray [["max", 2], ["classes", _heliClasses]]],
        ["transport_heli", createHashMapFromArray [["max", 2], ["classes", _transportHeliClasses]]],
        ["jet", createHashMapFromArray [["max", 1], ["classes", _jetClasses]]],
        ["drone", createHashMapFromArray [["max", 3], ["classes", _droneClasses]]],
        ["mortar", createHashMapFromArray [["max", 1], ["classes", _mortarClasses]]],
        ["aa_vehicle", createHashMapFromArray [["max", 1], ["classes", _aaClasses]]]
    ]],

    // Minimal template - limited resources
    ["minimal", createHashMapFromArray [
        ["infantry_squad", createHashMapFromArray [["max", 4], ["classes", _infantryClasses]]],
        ["ifv", createHashMapFromArray [["max", 1], ["classes", _ifvClasses]]],
        ["attack_heli", createHashMapFromArray [["max", 1], ["classes", _heliClasses]]]
    ]]
];

private _template = _templates getOrDefault [_templateLower, createHashMap];

if (count _template == 0) then {
    ["BATCOM", "WARN", format ["Unknown template '%1', available: default, light, heavy, mixed, minimal", _templateName]] call FUNC(logMessage);
};

_template
