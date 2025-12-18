#include "..\script_component.hpp"
/*
 * Apply a deploy_asset command (resource-backed spawn abstraction).
 *
 * Arguments:
 * 0: Command params <HASHMAP>
 *    - side: "EAST"/"WEST"/"RESISTANCE"
 *    - unit_classes: unit class array (from resource mapping)
 *    - position: [x,y,z]
 *    - objective_id: optional objective id
 *
 * Returns:
 * Success <BOOL>
 */

params [
    ["_params", createHashMap, [createHashMap]]
];

// Reuse spawn logic; deploy_asset is a semantic alias
[_params] call FUNC(applySpawnCommand)
