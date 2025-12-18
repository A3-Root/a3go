# Command Reference

Complete reference for all tactical commands the BATCOM AI can issue, including parameters, use cases, and implementation details.

## Table of Contents

- [Overview](#overview)
- [Command Types](#command-types)
  - [move_to](#move_to)
  - [defend_area](#defend_area)
  - [patrol_route](#patrol_route)
  - [seek_and_destroy](#seek_and_destroy)
  - [transport_group](#transport_group)
  - [escort_group](#escort_group)
  - [fire_support](#fire_support)
  - [deploy_asset](#deploy_asset)
- [Command Structure](#command-structure)
- [Parameter Reference](#parameter-reference)
- [Tactical Considerations](#tactical-considerations)
- [Command Combinations](#command-combinations)

---

## Overview

BATCOM's AI commander can issue 8 different types of tactical commands. Each command has specific parameters, behavior patterns, and use cases.

### Command Lifecycle

```
LLM Decision
    ↓
JSON Order Generated
    ↓
Parse to Command Object
    ↓
Validation (Sandbox)
    ↓
Add to Command Queue
    ↓
Retrieve from Queue (SQF)
    ↓
Apply to Group
    ↓
Execute in Game
```

### Common Parameters

All commands share these core parameters:

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `command_type` | STRING | Command identifier | Yes |
| `group_id` | STRING | Target group ID | Yes |
| `priority` | NUMBER | 0-10, execution priority | No (default: 5) |
| `timestamp` | STRING | ISO timestamp | No (auto-added) |
| `parameters` | HASHMAP | Command-specific params | Varies |

---

## Command Types

### move_to

**Purpose**: Reposition a group to a specific location.

**Use Cases**:
- Tactical repositioning
- Rally points
- Flanking maneuvers
- Withdrawal/retreat
- Reinforcement positioning

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `position` | ARRAY | Destination [x, y, z] | Yes | - |
| `waypoint_type` | STRING | Waypoint behavior | No | "MOVE" |
| `speed` | STRING | Movement speed | No | "NORMAL" |
| `formation` | STRING | Formation type | No | Current |
| `combat_mode` | STRING | Combat behavior | No | "YELLOW" |

#### Waypoint Types

- `"MOVE"` - Standard movement
- `"SAD"` - Search and destroy en route
- `"HOLD"` - Hold at position
- `"GETOUT"` - Dismount vehicles

#### Speed Options

- `"LIMITED"` - Slow, tactical
- `"NORMAL"` - Standard pace
- `"FULL"` - Maximum speed

#### Example LLM Response

```json
{
    "command_type": "move_to",
    "group_id": "B_Alpha_1_5",
    "parameters": {
        "position": [5234, 5678, 0],
        "waypoint_type": "MOVE",
        "speed": "NORMAL",
        "combat_mode": "YELLOW"
    },
    "priority": 7
}
```

#### SQF Implementation

**Function**: `Root_fnc_applyMoveCommand`

**Location**: `addons/main/functions/fn_applyMoveCommand.sqf:1`

```sqf
params ["_group", "_position", "_waypointType"];

// Clear existing waypoints
while {count waypoints _group > 0} do {
    deleteWaypoint [_group, 0];
};

// Add new waypoint
private _wp = _group addWaypoint [_position, 0];
_wp setWaypointType _waypointType;
_wp setWaypointBehaviour "AWARE";
_wp setWaypointCombatMode "YELLOW";
_wp setWaypointSpeed "NORMAL";
```

#### Tactical Considerations

**When to Use**:
- Group needs to change position
- Reinforcing another position
- Repositioning for better advantage
- Withdrawal from untenable position

**AI Decision Factors**:
- Distance to objective
- Current threat level
- Group type (fast units for urgent moves)
- Terrain considerations

---

### defend_area

**Purpose**: Establish defensive position in an area.

**Use Cases**:
- Defend objectives
- Create defensive perimeter
- Hold critical positions
- Ambush positions
- Overwatch positions

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `position` | ARRAY | Defense center [x, y, z] | Yes | - |
| `radius` | NUMBER | Defense radius (meters) | Yes | - |
| `behavior` | STRING | Defensive posture | No | "AWARE" |
| `combat_mode` | STRING | Rules of engagement | No | "RED" |
| `formation` | STRING | Defensive formation | No | "LINE" |

#### Behavior Options

- `"CARELESS"` - No combat readiness
- `"SAFE"` - Lowered weapons
- `"AWARE"` - Alert, weapons ready (default)
- `"COMBAT"` - Expect contact
- `"STEALTH"` - Silent movement

#### Combat Mode Options

- `"BLUE"` - Never fire
- `"GREEN"` - Hold fire
- `"WHITE"` - Hold fire, defend only
- `"YELLOW"` - Fire at will, keep formation
- `"RED"` - Fire at will (default)

#### Example LLM Response

```json
{
    "command_type": "defend_area",
    "group_id": "B_Bravo_1_6",
    "parameters": {
        "position": [5100, 5700, 0],
        "radius": 150,
        "behavior": "COMBAT",
        "combat_mode": "RED"
    },
    "priority": 9
}
```

#### SQF Implementation

**Function**: `Root_fnc_applyDefendCommand`

**Location**: `addons/main/functions/fn_applyDefendCommand.sqf:1`

```sqf
params ["_group", "_position", "_radius"];

// Clear waypoints
while {count waypoints _group > 0} do {
    deleteWaypoint [_group, 0];
};

// Move to position
private _wp1 = _group addWaypoint [_position, 0];
_wp1 setWaypointType "MOVE";
_wp1 setWaypointBehaviour "AWARE";

// Set up defense
private _wp2 = _group addWaypoint [_position, _radius];
_wp2 setWaypointType "HOLD";
_wp2 setWaypointBehaviour "COMBAT";
_wp2 setWaypointCombatMode "RED";
_wp2 setWaypointFormation "LINE";
```

#### Tactical Considerations

**When to Use**:
- Objective requires defense
- Creating strongpoint
- Blocking enemy advance
- Providing overwatch
- Holding captured territory

**AI Decision Factors**:
- Objective priority
- Terrain defensibility
- Group composition (infantry best)
- Threat direction
- Supporting positions

**Best Group Types**:
- Infantry (excellent)
- Mechanized infantry (good)
- Armor (good for strongpoints)
- AT teams (specialized defense)

---

### patrol_route

**Purpose**: Active patrolling along specified route.

**Use Cases**:
- Reconnaissance
- Area control
- Security patrols
- Show of force
- Early warning

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `positions` | ARRAY | Array of waypoints [[x,y,z], ...] | Yes | - |
| `patrol_type` | STRING | Patrol behavior | No | "SAD" |
| `speed` | STRING | Movement speed | No | "LIMITED" |
| `cycle` | BOOL | Loop patrol route | No | true |

#### Patrol Types

- `"MOVE"` - Standard patrol
- `"SAD"` - Search and destroy patrol (default)
- `"GUARD"` - Guard waypoints

#### Example LLM Response

```json
{
    "command_type": "patrol_route",
    "group_id": "B_Charlie_1_7",
    "parameters": {
        "positions": [
            [5000, 5000, 0],
            [5200, 5100, 0],
            [5300, 5200, 0],
            [5100, 5300, 0]
        ],
        "patrol_type": "SAD",
        "speed": "LIMITED",
        "cycle": true
    },
    "priority": 5
}
```

#### SQF Implementation

**Function**: `Root_fnc_applyPatrolCommand`

**Location**: `addons/main/functions/fn_applyPatrolCommand.sqf:1`

```sqf
params ["_group", "_positions"];

// Clear waypoints
while {count waypoints _group > 0} do {
    deleteWaypoint [_group, 0];
};

// Add patrol waypoints
{
    private _wp = _group addWaypoint [_x, 0];
    _wp setWaypointType "SAD";
    _wp setWaypointBehaviour "AWARE";
    _wp setWaypointSpeed "LIMITED";
} forEach _positions;

// Cycle back to start
private _wpCycle = _group addWaypoint [_positions select 0, 0];
_wpCycle setWaypointType "CYCLE";
```

#### Tactical Considerations

**When to Use**:
- Area security needed
- Reconnaissance required
- Show of force
- Detect enemy movements
- Maintain area control

**AI Decision Factors**:
- AO size
- Threat level
- Available forces
- Objective coverage
- Intel gathering needs

**Best Group Types**:
- Recon teams (excellent)
- Light infantry (good)
- Motorized units (good for large areas)
- Air units (fast coverage)

---

### seek_and_destroy

**Purpose**: Actively hunt and eliminate enemy forces in an area.

**Use Cases**:
- Clearing enemy forces
- Offensive operations
- Counter-attack
- Area denial
- Threat elimination

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `position` | ARRAY | Search area center [x, y, z] | Yes | - |
| `radius` | NUMBER | Search radius (meters) | Yes | - |
| `target_types` | ARRAY | Enemy types to prioritize | No | All |
| `behavior` | STRING | Tactical behavior | No | "AWARE" |

#### Example LLM Response

```json
{
    "command_type": "seek_and_destroy",
    "group_id": "B_Delta_1_8",
    "parameters": {
        "position": [5500, 5500, 0],
        "radius": 500,
        "target_types": ["armor", "infantry"],
        "behavior": "COMBAT"
    },
    "priority": 8
}
```

#### SQF Implementation

**Function**: `Root_fnc_applySeekCommand`

**Location**: `addons/main/functions/fn_applySeekCommand.sqf:1`

```sqf
params ["_group", "_position", "_radius"];

// Clear waypoints
while {count waypoints _group > 0} do {
    deleteWaypoint [_group, 0];
};

// Search and destroy waypoint
private _wp = _group addWaypoint [_position, _radius];
_wp setWaypointType "SAD";
_wp setWaypointBehaviour "COMBAT";
_wp setWaypointCombatMode "RED";
_wp setWaypointSpeed "NORMAL";
```

#### Tactical Considerations

**When to Use**:
- Enemy forces detected
- Clearing objectives
- Offensive push
- Neutralizing threats
- Aggressive posture needed

**AI Decision Factors**:
- Enemy force strength
- Friendly force advantage
- Objective importance
- Time constraints
- Civilian presence

**Best Group Types**:
- Mechanized infantry (excellent)
- Armor (good for heavy resistance)
- Combined arms (ideal)
- Attack helicopters (fast strikes)

---

### transport_group

**Purpose**: Transport infantry using vehicles.

**Use Cases**:
- Rapid deployment
- Helicopter insertions
- Vehicle-mounted movement
- Evacuation
- Reinforcement delivery

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `cargo_group_id` | STRING | Group to transport | Yes | - |
| `transport_group_id` | STRING | Vehicle group | Yes | - |
| `destination` | ARRAY | Drop-off point [x, y, z] | Yes | - |
| `pickup_position` | ARRAY | Pickup point [x, y, z] | No | Cargo position |
| `dismount_distance` | NUMBER | Distance before landing (heli) | No | 0 |

#### Example LLM Response

```json
{
    "command_type": "transport_group",
    "group_id": "B_Echo_1_9",
    "parameters": {
        "cargo_group_id": "B_Alpha_1_5",
        "transport_group_id": "B_Heli_1_1",
        "destination": [6000, 6000, 0],
        "dismount_distance": 50
    },
    "priority": 7
}
```

#### SQF Implementation

**Function**: `Root_fnc_applyTransportCommand`

**Location**: `addons/main/functions/fn_applyTransportCommand.sqf:1`

```sqf
params ["_cargoGroup", "_transportGroup", "_destination"];

// Get vehicle
private _vehicle = vehicle (leader _transportGroup);

// Clear waypoints for both groups
while {count waypoints _cargoGroup > 0} do {
    deleteWaypoint [_cargoGroup, 0];
};
while {count waypoints _transportGroup > 0} do {
    deleteWaypoint [_transportGroup, 0];
};

// Cargo: Get in waypoint
private _wpGetIn = _cargoGroup addWaypoint [getPos _vehicle, 0];
_wpGetIn setWaypointType "GETIN";

// Transport: Move to destination
private _wpTransport = _transportGroup addWaypoint [_destination, 0];
_wpTransport setWaypointType "TR UNLOAD";

// Cargo: Get out at destination
private _wpGetOut = _cargoGroup addWaypoint [_destination, 0];
_wpGetOut setWaypointType "GETOUT";
```

#### Tactical Considerations

**When to Use**:
- Rapid repositioning needed
- Long distances
- Time-critical deployment
- Bypassing obstacles
- Evacuation needed

**AI Decision Factors**:
- Distance to objective
- Urgency
- Transport availability
- Landing zone suitability
- Enemy air defense

**Requirements**:
- Transport group must have vehicles
- Sufficient capacity for cargo
- Valid landing/drop-off zone

---

### escort_group

**Purpose**: Protect high-value target group.

**Use Cases**:
- VIP protection
- Convoy escort
- Protect support assets
- Secure transport
- Guard commanders

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `protected_group_id` | STRING | Group to protect | Yes | - |
| `escort_distance` | NUMBER | Distance to maintain (meters) | No | 50 |
| `formation` | STRING | Escort formation | No | "WEDGE" |

#### Example LLM Response

```json
{
    "command_type": "escort_group",
    "group_id": "B_Foxtrot_1_10",
    "parameters": {
        "protected_group_id": "B_Command_1_1",
        "escort_distance": 75,
        "formation": "WEDGE"
    },
    "priority": 9
}
```

#### SQF Implementation

**Function**: `Root_fnc_applyEscortCommand`

**Location**: `addons/main/functions/fn_applyEscortCommand.sqf:1`

```sqf
params ["_escortGroup", "_protectedGroup"];

// Clear escort waypoints
while {count waypoints _escortGroup > 0} do {
    deleteWaypoint [_escortGroup, 0];
};

// Follow protected group
_escortGroup setFormation "WEDGE";
_escortGroup setBehaviour "COMBAT";
_escortGroup setCombatMode "RED";

// Attach to protected group
private _wp = _escortGroup addWaypoint [getPos (leader _protectedGroup), 0];
_wp setWaypointType "MOVE";
_wp attachTo (leader _protectedGroup);
```

#### Tactical Considerations

**When to Use**:
- High-value target needs protection
- Command groups vulnerable
- Support assets at risk
- Transport convoys
- VIP movements

**AI Decision Factors**:
- Protected asset value
- Threat level
- Escort capability
- Route danger
- Available forces

**Best Escort Types**:
- Armor (excellent for ground threats)
- Mechanized infantry (versatile)
- Attack helicopters (air threats)
- AT teams (armor threats)

---

### fire_support

**Purpose**: Provide indirect fire or close air support.

**Use Cases**:
- Artillery strikes
- Mortar support
- Close air support
- Suppression fire
- Area denial

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `target_position` | ARRAY | Target location [x, y, z] | Yes | - |
| `support_type` | STRING | Type of support | No | "artillery" |
| `rounds` | NUMBER | Number of rounds | No | 5 |
| `radius` | NUMBER | Effect radius (meters) | No | 100 |

#### Support Types

- `"artillery"` - Artillery fire
- `"mortar"` - Mortar fire
- `"cas"` - Close air support
- `"gunship"` - Attack helicopter

#### Example LLM Response

```json
{
    "command_type": "fire_support",
    "group_id": "B_Artillery_1_1",
    "parameters": {
        "target_position": [5800, 5900, 0],
        "support_type": "artillery",
        "rounds": 10,
        "radius": 150
    },
    "priority": 8
}
```

#### SQF Implementation

**Function**: `Root_fnc_applyFireSupportCommand`

**Location**: `addons/main/functions/fn_applyFireSupportCommand.sqf:1`

```sqf
params ["_fireSupportGroup", "_targetPosition"];

// Clear waypoints
while {count waypoints _fireSupportGroup > 0} do {
    deleteWaypoint [_fireSupportGroup, 0];
};

// Fire mission waypoint
private _vehicle = vehicle (leader _fireSupportGroup);

// Artillery
if (_vehicle isKindOf "Artillery") then {
    _vehicle commandArtilleryFire [_targetPosition, "8Rnd_82mm_Mo_shells", 10];
};

// Air support
if (_vehicle isKindOf "Air") then {
    private _wp = _fireSupportGroup addWaypoint [_targetPosition, 0];
    _wp setWaypointType "SAD";
    _wp setWaypointCombatMode "RED";
};
```

#### Tactical Considerations

**When to Use**:
- Enemy concentration detected
- Softening defenses
- Suppressing enemy
- Area denial
- Breaking enemy morale

**AI Decision Factors**:
- Target value
- Collateral damage risk
- Ammunition availability
- Time to impact
- Civilian proximity

**Requirements**:
- Appropriate fire support assets
- Clear line of fire/flight
- Target in range
- No friendly forces in area

---

### deploy_asset

**Purpose**: Spawn new units from resource pool.

**Use Cases**:
- Reinforcements
- Replace losses
- Escalation
- Specialized units
- Dynamic force generation

#### Parameters

| Parameter | Type | Description | Required | Default |
|-----------|------|-------------|----------|---------|
| `asset_type` | STRING | Resource pool asset ID | Yes | - |
| `side` | STRING | Side to spawn for | Yes | - |
| `position` | ARRAY | Spawn location [x, y, z] | Yes | - |
| `heading` | NUMBER | Initial heading (degrees) | No | 0 |

#### Example LLM Response

```json
{
    "command_type": "deploy_asset",
    "group_id": "new_group_placeholder",
    "parameters": {
        "asset_type": "infantry_squad",
        "side": "EAST",
        "position": [5400, 5600, 0],
        "heading": 180
    },
    "priority": 6
}
```

#### SQF Implementation

**Function**: `Root_fnc_applyDeployAssetCommand`

**Location**: `addons/main/functions/fn_applyDeployAssetCommand.sqf:1`

```sqf
params ["_assetType", "_side", "_position", "_classnames"];

// Check resource pool limit
if (![_assetType, _side] call BATCOM_fnc_canDeployAsset) exitWith {
    diag_log format ["Cannot deploy %1 - limit reached", _assetType];
    nil
};

// Create group
private _group = createGroup _side;

// Spawn units
{
    private _unit = _group createUnit [_x, _position, [], 0, "FORM"];
} forEach _classnames;

// Record deployment
[_assetType, _side] call BATCOM_fnc_recordDeployment;

// Return new group
_group
```

#### Tactical Considerations

**When to Use**:
- Force levels insufficient
- Specialized units needed
- Replacing losses
- Escalating response
- Reinforcing success

**AI Decision Factors**:
- Current force strength
- Resource pool limits
- Spawn limits per side
- Strategic need
- Asset availability

**Validation**:
- Resource pool configured
- Limit not exceeded
- Valid spawn position
- Side matches controlled sides

---

## Command Structure

### JSON Format

Commands from LLM are JSON objects:

```json
{
    "reasoning": "Brief explanation of tactical decision",
    "orders": [
        {
            "command_type": "move_to",
            "group_id": "B_Alpha_1_5",
            "parameters": {
                "position": [5234, 5678, 0],
                "waypoint_type": "MOVE"
            },
            "priority": 7
        }
    ]
}
```

### SQF Format

After parsing and validation, commands are hashmaps:

```sqf
createHashMapFromArray [
    ["command_type", "move_to"],
    ["group_id", "B_Alpha_1_5"],
    ["parameters", createHashMapFromArray [
        ["position", [5234, 5678, 0]],
        ["waypoint_type", "MOVE"]
    ]],
    ["priority", 7],
    ["timestamp", "2024-01-15T10:30:00"]
]
```

---

## Parameter Reference

### Position Format

All positions are world coordinates:
```
[x, y, z]
```
- `x`: East-West coordinate
- `y`: North-South coordinate
- `z`: Altitude (usually 0 for ground)

### Group ID Format

Group IDs follow pattern:
```
<side>_<groupName>_<uniqueId>
```

Example: `"B_Alpha_1_5"` = BLUFOR, Alpha group, ID 1_5

### Priority Scale

```
10 - Critical, mission-essential
9  - Very high priority
7-8 - High priority
5-6 - Medium priority
3-4 - Low priority
1-2 - Very low priority
0  - Optional, if resources available
```

---

## Tactical Considerations

### Command Selection Matrix

| Situation | Recommended Command | Alternative |
|-----------|-------------------|-------------|
| Enemy at objective | `defend_area` | `seek_and_destroy` |
| Objective undefended | `move_to` | `patrol_route` |
| Enemy concentration | `seek_and_destroy` | `fire_support` |
| Large AO coverage | `patrol_route` | Multiple `move_to` |
| Rapid deployment | `transport_group` | `move_to` (slower) |
| VIP movement | `escort_group` | `defend_area` (static) |
| Enemy armor threat | `fire_support` | `seek_and_destroy` (AT) |
| Need reinforcements | `deploy_asset` | Redeploy existing |

### Force Type Suitability

| Command | Infantry | Mechanized | Armor | Air | Artillery |
|---------|----------|------------|-------|-----|-----------|
| move_to | ✓✓✓ | ✓✓✓ | ✓✓ | ✓✓✓ | ✓ |
| defend_area | ✓✓✓ | ✓✓✓ | ✓✓ | ✗ | ✗ |
| patrol_route | ✓✓✓ | ✓✓ | ✓ | ✓✓✓ | ✗ |
| seek_and_destroy | ✓✓ | ✓✓✓ | ✓✓✓ | ✓✓✓ | ✗ |
| transport | ✗ | ✗ | ✗ | ✓✓✓ | ✗ |
| escort | ✓✓ | ✓✓✓ | ✓✓✓ | ✓✓ | ✗ |
| fire_support | ✗ | ✗ | ✗ | ✓✓✓ | ✓✓✓ |

Legend: ✓✓✓ Excellent, ✓✓ Good, ✓ Acceptable, ✗ Not suitable

---

## Command Combinations

### Coordinated Attack

```json
{
    "orders": [
        {
            "command_type": "fire_support",
            "group_id": "artillery_1",
            "parameters": {
                "target_position": [5000, 5000, 0]
            },
            "priority": 10
        },
        {
            "command_type": "seek_and_destroy",
            "group_id": "infantry_1",
            "parameters": {
                "position": [5000, 5000, 0],
                "radius": 300
            },
            "priority": 9
        },
        {
            "command_type": "escort_group",
            "group_id": "armor_1",
            "parameters": {
                "protected_group_id": "infantry_1"
            },
            "priority": 8
        }
    ]
}
```

### Defense in Depth

```json
{
    "orders": [
        {
            "command_type": "defend_area",
            "group_id": "infantry_1",
            "parameters": {
                "position": [5000, 5000, 0],
                "radius": 100
            },
            "priority": 10
        },
        {
            "command_type": "defend_area",
            "group_id": "infantry_2",
            "parameters": {
                "position": [4800, 5000, 0],
                "radius": 150
            },
            "priority": 8
        },
        {
            "command_type": "patrol_route",
            "group_id": "recon_1",
            "parameters": {
                "positions": [[4500, 5000, 0], [5500, 5000, 0]]
            },
            "priority": 6
        }
    ]
}
```

### Rapid Deployment

```json
{
    "orders": [
        {
            "command_type": "deploy_asset",
            "group_id": "new",
            "parameters": {
                "asset_type": "infantry_squad",
                "side": "EAST",
                "position": [4900, 4900, 0]
            },
            "priority": 7
        },
        {
            "command_type": "transport_group",
            "group_id": "heli_1",
            "parameters": {
                "cargo_group_id": "B_Alpha_1_5",
                "destination": [5000, 5000, 0]
            },
            "priority": 9
        }
    ]
}
```

---

## See Also

- [API Reference](API-Reference.md) - Function documentation
- [Mission Setup Guide](Mission-Setup-Guide.md) - Define objectives
- [Architecture Overview](Architecture-Overview.md) - Command lifecycle
- [Task Examples](../docs/task-examples.md) - Objective examples

---

**Last Updated**: 2025-12-05
