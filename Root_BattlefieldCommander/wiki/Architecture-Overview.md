# Architecture Overview

Technical deep-dive into BATCOM's architecture, design decisions, and implementation details.

## Table of Contents

- [System Overview](#system-overview)
- [Layer Architecture](#layer-architecture)
- [Data Flow](#data-flow)
- [Core Components](#core-components)
- [Decision Loop](#decision-loop)
- [Safety & Validation](#safety--validation)
- [Performance Considerations](#performance-considerations)
- [Design Decisions](#design-decisions)

---

## System Overview

BATCOM is a three-layer system that bridges Arma 3's SQF scripting environment with modern Large Language Models through Python.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Arma 3 SQF Layer                      │
│  - World scanning (units, groups, objectives)                │
│  - Command execution (waypoints, orders)                     │
│  - Configuration management                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ Pythia Extension (Python bridge)
                       │ - Data serialization
                       │ - Function calls (Python ↔ SQF)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      Python Core Layer                       │
│  - Decision loop orchestration                               │
│  - World state processing                                    │
│  - LLM integration & prompt engineering                      │
│  - Command validation & safety checks                        │
│  - Token tracking & caching                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS API
                       │ - REST calls
                       │ - Context caching
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      LLM Provider API                        │
│  - Gemini, OpenAI, Claude, DeepSeek, Azure, Local           │
│  - Tactical decision generation                              │
│  - Natural language understanding                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Architecture

### SQF Layer (`addons/main/`)

**Responsibilities**:
- World state scanning
- Command application to groups
- Configuration management
- Event handling
- Integration with Arma 3 engine

**Key Components**:

#### 1. Initialization System
```
XEH_preInit.sqf → Root_fnc_init → BATCOM namespace setup
                                 → Pythia initialization
                                 → Config loading

XEH_postInit.sqf → Auto-start on server
                 → Register event handlers
```

#### 2. World Scanner (`fn_worldScan.sqf`)
```sqf
World Scan Loop (every 2s):
    1. Scan all units & groups
    2. Collect player information
    3. Evaluate objective states
    4. Package into snapshot hashmap
    5. Send to Python via Pythia
    6. Retrieve pending commands
    7. Execute commands
```

**Data Collected**:
- Group positions, headings, speeds
- Unit counts, states, types
- Combat status, ammunition
- Waypoints, behavior modes
- Objective completion states
- Player positions and actions

#### 3. Command Application Functions
Each command type has dedicated application function:
- `fn_applyMoveCommand.sqf` - Movement orders
- `fn_applyDefendCommand.sqf` - Defensive positions
- `fn_applyPatrolCommand.sqf` - Patrol routes
- `fn_applySeekCommand.sqf` - Seek & destroy
- `fn_applyTransportCommand.sqf` - Transport operations
- `fn_applyEscortCommand.sqf` - Escort missions
- `fn_applyFireSupportCommand.sqf` - Fire support
- `fn_applyDeployAssetCommand.sqf` - Unit spawning

**Implementation Pattern**:
```sqf
params ["_group", "_commandParams"];

// 1. Validate parameters
if (isNull _group) exitWith {false};

// 2. Clear existing waypoints
while {count waypoints _group > 0} do {
    deleteWaypoint [_group, 0];
};

// 3. Apply new waypoints/behavior
_wp = _group addWaypoint [_position, 0];
_wp setWaypointType "MOVE";
_wp setWaypointBehaviour "AWARE";

// 4. Log action
diag_log format ["Applied command to %1", _group];

true
```

### Python Layer (`batcom/`)

**Responsibilities**:
- Decision loop orchestration
- LLM prompt engineering
- Command parsing and validation
- State management
- Token tracking
- Logging

**Module Structure**:

```
batcom/
├── api.py                    # Entry point - Pythia interface
├── runtime/
│   ├── commander.py          # Main decision loop orchestrator
│   ├── state.py              # Persistent state manager
│   ├── admin.py              # Admin command handler
│   ├── token_tracker.py      # Token usage tracking
│   └── api_logger.py         # API call logging
├── ai/
│   ├── providers.py          # Multi-provider LLM clients
│   ├── gemini.py             # Gemini-specific utilities
│   ├── order_parser.py       # Parse LLM JSON responses
│   └── sandbox.py            # Command validation
├── decision/
│   ├── evaluator.py          # Evaluate objective states
│   ├── priority.py           # Calculate priorities
│   ├── assignment.py         # Assign groups to objectives
│   ├── planner.py            # Generate tactical plans
│   └── tactics.py            # Tactical behavior engine
├── commands/
│   ├── generator.py          # Generate commands from plans
│   ├── queue.py              # Command queue management
│   └── serializer.py         # Serialize for SQF
├── models/
│   ├── commands.py           # Command data classes
│   ├── world.py              # World state models
│   ├── objectives.py         # Objective models
│   └── tasks.py              # Task assignment models
├── world/
│   └── scanner.py            # Process world snapshots
└── config/
    ├── defaults.py           # Default configuration
    └── guardrails.json       # LLM provider config
```

#### Key Python Classes

**WorldState** (`models/world.py`):
```python
@dataclass
class WorldState:
    timestamp: float
    groups: List[Group]
    players: List[Player]
    objectives: List[Objective]
    commander_state: CommanderState
```

**Group** (`models/world.py`):
```python
@dataclass
class Group:
    id: str              # Unique identifier
    side: str            # WEST, EAST, INDEPENDENT
    position: Position   # [x, y, z]
    heading: float       # Degrees
    speed: float         # m/s
    unit_count: int
    group_type: str      # infantry, armor, air, etc.
    is_in_combat: bool
    units: List[Unit]
```

**Command** (`models/commands.py`):
```python
@dataclass
class Command:
    command_type: str    # move_to, defend_area, etc.
    group_id: str        # Target group
    parameters: dict     # Command-specific params
    priority: int        # 0-10
    timestamp: str       # ISO format
```

**LLMClient** (`ai/providers.py`):
```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def generate_orders(
        self,
        world_state: WorldState,
        objectives: List[Objective],
        order_history: List[Order]
    ) -> List[Order]:
        """Generate tactical orders from world state."""
        pass
```

### Pythia Bridge

**Pythia Extension** enables SQF ↔ Python communication:

**SQF → Python**:
```sqf
["batcom.function_name", [arg1, arg2, ...]] call py3_fnc_callExtension;
```

**Python → SQF**:
```python
# Return value automatically passed back to SQF
return {"status": "success", "data": [...]}
```

**Data Serialization**:
- SQF hashmaps → Python dicts
- SQF arrays → Python lists
- Automatic type conversion
- JSON serialization for complex objects

---

## Data Flow

### Complete Request-Response Cycle

```
1. World Scan (SQF)
   ↓
2. Serialize to Hashmap
   ↓
3. Send via Pythia → world_snapshot()
   ↓
4. Python receives world state
   ↓
5. Commander.process_world_state()
   ↓
6. Evaluate objectives (priority, state)
   ↓
7. Assign groups to objectives
   ↓
8. Check if LLM call needed (min_interval, changes)
   ↓
9. If yes: Build LLM prompt
   ↓
10. Call LLM API (async)
    ↓
11. Parse JSON response → Commands
    ↓
12. Validate commands (sandbox)
    ↓
13. Add to command queue
    ↓
14. SQF calls get_pending_commands()
    ↓
15. Return serialized commands
    ↓
16. SQF executes commands
    ↓
17. Apply to groups (waypoints, behavior)
```

### Decision Timing

```
Mission Start
    ↓
Deploy Commander
    ↓
First World Scan (immediate)
    ↓
Initial State Assessment
    ↓
Wait min_interval (default 45s)
    ↓
First LLM Call
    ↓
Parse & Queue Commands
    ↓
Execute Commands
    ↓
┌─────────────────────┐
│  Decision Loop      │
│  Every ~45-60s:     │
│  1. Scan world      │
│  2. Evaluate changes│
│  3. LLM decision    │
│  4. Execute         │
└─────────────────────┘
```

---

## Core Components

### 1. Commander (`runtime/commander.py`)

**Main orchestrator** of the decision loop.

**Key Methods**:

```python
class Commander:
    def __init__(self, config: dict):
        self.llm_client = create_llm_client(config)
        self.state_manager = StateManager()
        self.command_queue = CommandQueue()
        self.last_decision_time = 0

    async def process_world_state(self, world_state: WorldState):
        """Main decision loop entry point."""

        # 1. Update internal state
        self.state_manager.update(world_state)

        # 2. Evaluate objectives
        objective_states = self.evaluate_objectives(world_state)

        # 3. Check if LLM call needed
        if not self.should_make_decision():
            return

        # 4. Generate tactical plan via LLM
        orders = await self.llm_client.generate_orders(
            world_state,
            self.state_manager.objectives,
            self.state_manager.order_history
        )

        # 5. Parse and validate
        commands = self.parse_orders(orders)
        validated = self.validate_commands(commands)

        # 6. Queue for execution
        for cmd in validated:
            self.command_queue.add(cmd)

        # 7. Update metrics
        self.last_decision_time = time.time()
        self.token_tracker.record(...)
```

**Decision Criteria**:
- Minimum interval elapsed (default 45s)
- Significant world state changes
- New objectives added
- Previous commands completed
- Error recovery needed

### 2. LLM Providers (`ai/providers.py`)

**Multi-provider abstraction** for different LLM APIs.

**Architecture**:
```python
BaseLLMClient (ABC)
    ├── GeminiLLMClient
    ├── OpenAILLMClient
    ├── AnthropicLLMClient
    ├── DeepSeekLLMClient
    ├── AzureOpenAILLMClient
    └── LocalLLMClient
```

**Key Features**:

#### Gemini Context Caching
```python
class GeminiLLMClient(BaseLLMClient):
    def __init__(self, config):
        self.cache = None
        self.cache_timestamp = 0
        self.cache_ttl = 3600  # 1 hour

    async def generate_orders(self, ...):
        # 1. Check cache validity
        if self.cache_needs_refresh():
            self.refresh_cache(objectives, order_history)

        # 2. Build prompt with cached content
        messages = [
            {"role": "system", "content": self.get_cached_system_prompt()},
            {"role": "user", "content": self.format_world_state(world_state)}
        ]

        # 3. Call API with cache reference
        response = await self.client.generate_content(
            messages,
            cached_content=self.cache
        )

        # 4. Track token metrics
        self.track_tokens(response.usage_metadata)
```

**Token Savings**:
- System prompt: ~2000 tokens (cached)
- Objectives: ~500 tokens (cached)
- Order history: ~1800 tokens (cached)
- **Total cached**: ~4300 tokens
- **Per-call**: ~440 tokens (world state only)
- **Savings**: 90%

#### Rate Limiting
```python
class RateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.last_call_time = 0

    async def wait_if_needed(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()
```

#### Circuit Breaker
```python
class CircuitBreaker:
    def __init__(self, max_failures: int = 3):
        self.max_failures = max_failures
        self.failure_count = 0
        self.is_open = False

    def on_success(self):
        self.failure_count = 0

    def on_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.is_open = True
            logger.error("Circuit breaker opened - LLM disabled")
```

### 3. Order Parser (`ai/order_parser.py`)

**Parses LLM JSON responses** into command objects.

**Expected LLM Response Format**:
```json
{
    "reasoning": "Enemy forces detected in sector 3, deploying reaction force",
    "orders": [
        {
            "command_type": "move_to",
            "group_id": "B_Alpha_1_5",
            "parameters": {
                "position": [5234, 5678, 0],
                "waypoint_type": "MOVE"
            },
            "priority": 8
        },
        {
            "command_type": "defend_area",
            "group_id": "B_Bravo_1_6",
            "parameters": {
                "position": [5100, 5700, 0],
                "radius": 150
            },
            "priority": 9
        }
    ]
}
```

**Parsing Logic**:
```python
def parse_orders(response: dict) -> List[Command]:
    """Parse LLM response into Command objects."""
    commands = []

    for order in response.get("orders", []):
        try:
            cmd = Command(
                command_type=order["command_type"],
                group_id=order["group_id"],
                parameters=order.get("parameters", {}),
                priority=order.get("priority", 5),
                timestamp=datetime.now().isoformat()
            )

            # Validate command structure
            if validate_command_structure(cmd):
                commands.append(cmd)
            else:
                logger.warning(f"Invalid command structure: {cmd}")

        except KeyError as e:
            logger.error(f"Missing required field: {e}")

    return commands
```

### 4. Sandbox (`ai/sandbox.py`)

**Multi-layer validation** ensures commands are safe and valid.

**Validation Layers**:

```python
class Sandbox:
    def validate(self, command: Command) -> ValidationResult:
        """Run all validation checks."""

        # 1. Command type whitelist
        if not self.is_command_allowed(command.command_type):
            return ValidationResult(False, "Command type not allowed")

        # 2. Group existence
        if not self.group_exists(command.group_id):
            return ValidationResult(False, "Group not found")

        # 3. AO bounds
        if not self.is_within_ao(command.parameters.get("position")):
            return ValidationResult(False, "Position outside AO")

        # 4. Resource limits
        if command.command_type == "deploy_asset":
            if not self.check_resource_pool(command):
                return ValidationResult(False, "Resource limit exceeded")

        # 5. Side validation
        group_side = self.get_group_side(command.group_id)
        if group_side not in self.controlled_sides:
            return ValidationResult(False, "Group side not controlled")

        # 6. Parameter validation
        if not self.validate_parameters(command):
            return ValidationResult(False, "Invalid parameters")

        return ValidationResult(True, "Validated")
```

**Safety Checks**:
- Command type whitelist
- AO geographic bounds (circle/rectangle)
- Resource pool limits
- Spawn limits per side
- Group ownership verification
- Parameter type validation

### 5. Command Queue (`commands/queue.py`)

**Thread-safe queue** for commands awaiting execution.

```python
class CommandQueue:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()

    def add(self, command: Command):
        """Add command to queue."""
        with self.lock:
            self.queue.append(command)
            self.queue.sort(key=lambda c: c.priority, reverse=True)

    def get_pending(self, max_count: int = 30) -> List[Command]:
        """Retrieve pending commands."""
        with self.lock:
            pending = self.queue[:max_count]
            self.queue = self.queue[max_count:]
            return pending
```

**Features**:
- Priority sorting (high priority first)
- Thread-safe operations
- Bounded retrieval (max per tick)
- Atomic queue operations

---

## Decision Loop

### Detailed Flow

```python
async def decision_loop():
    """Main decision loop - runs every cycle."""

    # 1. SCAN PHASE
    world_state = await scan_world()

    # 2. EVALUATION PHASE
    objective_evaluations = []
    for obj in objectives:
        state = evaluate_objective_state(obj, world_state)
        priority = calculate_priority(obj, state)
        objective_evaluations.append({
            "objective": obj,
            "state": state,
            "priority": priority
        })

    # 3. ASSIGNMENT PHASE
    assignments = assign_groups_to_objectives(
        world_state.groups,
        objective_evaluations
    )

    # 4. DECISION PHASE
    if should_call_llm():
        # Build context
        context = {
            "mission_brief": mission_brief,
            "objectives": objectives,
            "world_state": world_state,
            "previous_orders": order_history[-10:],  # Last 10
            "assignments": assignments
        }

        # Generate prompt
        prompt = build_tactical_prompt(context)

        # Call LLM
        response = await llm_client.call(prompt)

        # Parse response
        orders = parse_orders(response)

        # Update history
        order_history.extend(orders)

    # 5. VALIDATION PHASE
    validated_commands = []
    for order in orders:
        result = sandbox.validate(order)
        if result.is_valid:
            validated_commands.append(order)
        else:
            logger.warning(f"Command rejected: {result.reason}")

    # 6. EXECUTION PHASE
    for cmd in validated_commands:
        command_queue.add(cmd)

    # 7. METRICS PHASE
    token_tracker.record(response.token_usage)
    api_logger.log_call(prompt, response)
```

### Objective Evaluation

**State Calculation**:
```python
def evaluate_objective_state(obj: Objective, world: WorldState) -> str:
    """Determine objective state."""

    # Count friendly/enemy forces in area
    friendly_count = count_forces_in_radius(
        world.groups,
        obj.position,
        obj.radius,
        friendly_sides
    )

    enemy_count = count_forces_in_radius(
        world.groups,
        obj.position,
        obj.radius,
        enemy_sides
    )

    # Determine state
    if enemy_count == 0 and friendly_count > 0:
        return "secured"
    elif enemy_count > friendly_count * 2:
        return "threatened"
    elif enemy_count > 0:
        return "contested"
    else:
        return "undefended"
```

**Priority Calculation**:
```python
def calculate_priority(obj: Objective, state: str) -> float:
    """Calculate dynamic priority based on state."""

    base_priority = obj.priority  # User-defined 0-10

    # State modifiers
    modifiers = {
        "threatened": 1.5,   # Increase priority
        "contested": 1.2,
        "secured": 0.8,      # Decrease priority
        "undefended": 1.0
    }

    modifier = modifiers.get(state, 1.0)
    dynamic_priority = base_priority * modifier

    # Clamp to 0-10
    return max(0, min(10, dynamic_priority))
```

### Group Assignment

**Assignment Algorithm**:
```python
def assign_groups_to_objectives(
    groups: List[Group],
    objectives: List[Objective]
) -> Dict[str, str]:
    """Assign groups to objectives based on proximity and type."""

    assignments = {}

    # Sort objectives by priority
    sorted_objs = sorted(objectives, key=lambda o: o.priority, reverse=True)

    # Sort groups by availability
    available_groups = [g for g in groups if not is_in_combat(g)]

    for obj in sorted_objs:
        # Find best group for objective
        candidates = find_nearby_groups(available_groups, obj.position, 2000)

        if candidates:
            # Select by type preference
            best_group = select_best_group_for_task(
                candidates,
                obj.task_type
            )

            assignments[best_group.id] = obj.id
            available_groups.remove(best_group)

    return assignments
```

---

## Safety & Validation

### Multi-Layer Safety

```
LLM Response
    ↓
1. JSON Schema Validation
    ↓
2. Command Type Whitelist
    ↓
3. Group Existence Check
    ↓
4. Side Verification
    ↓
5. AO Bounds Check
    ↓
6. Resource Pool Limits
    ↓
7. Spawn Limit Check
    ↓
8. Parameter Validation
    ↓
Approved Command → Queue
```

### AO Bounds Validation

**Circle AO**:
```python
def is_within_circle_ao(position: Position, ao: AOConfig) -> bool:
    distance = calculate_distance(position, ao.center)
    return distance <= ao.radius
```

**Rectangle AO**:
```python
def is_within_rectangle_ao(position: Position, ao: AOConfig) -> bool:
    # Transform to local coordinates
    local = world_to_local(position, ao.center, ao.rotation)

    # Check bounds
    return (
        abs(local.x) <= ao.width / 2 and
        abs(local.y) <= ao.height / 2
    )
```

### Resource Pool Management

```python
class ResourcePoolManager:
    def __init__(self, pools: dict):
        self.pools = pools
        self.deployed_counts = defaultdict(int)

    def can_deploy(self, side: str, asset_type: str) -> bool:
        """Check if asset can be deployed."""
        pool = self.pools.get(side, {}).get(asset_type)
        if not pool:
            return False

        max_allowed = pool.get("max", 0)
        currently_deployed = self.deployed_counts[f"{side}_{asset_type}"]

        return currently_deployed < max_allowed

    def record_deployment(self, side: str, asset_type: str):
        """Record successful deployment."""
        self.deployed_counts[f"{side}_{asset_type}"] += 1
```

---

## Performance Considerations

### Optimization Strategies

#### 1. Context Caching
- **Gemini**: Native caching reduces tokens by 90%
- **Cache TTL**: 1 hour (automatic refresh)
- **Cached content**: System prompt, objectives, order history
- **Non-cached**: Current world state only

#### 2. Async Operations
```python
# LLM calls are async - don't block main thread
async def make_decision():
    response = await llm_client.generate_orders(...)
    # Other work can proceed while waiting
```

#### 3. Rate Limiting
- Prevents API quota exhaustion
- Configurable intervals
- Per-provider settings

#### 4. Command Batching
```python
# Retrieve multiple commands per tick
commands = command_queue.get_pending(max_count=30)

# Apply in batch
for cmd in commands:
    apply_command(cmd)
```

#### 5. Selective Scanning
```sqf
// Scan different elements at different rates
scan_tick = 2.0;        // General scan every 2s
ai_groups = 5.0;        // AI groups every 5s
players = 3.0;          // Players every 3s
objectives = 5.0;       // Objectives every 5s
```

### Memory Management

**Python Side**:
- Limited order history (keep last N orders)
- Periodic log rotation
- Bounded command queue
- Cache invalidation

**SQF Side**:
- Clean up completed waypoints
- Remove stale group references
- Limit stored snapshots

---

## Design Decisions

### Why Three Layers?

**SQF Layer**:
- Required for Arma 3 engine integration
- Native performance for game interactions
- Direct access to game state

**Python Layer**:
- Rich ecosystem for LLM integration
- Async/await for non-blocking operations
- Easy debugging and development
- Cross-platform compatibility

**LLM Provider Layer**:
- State-of-the-art tactical reasoning
- Natural language understanding
- Adaptive decision-making
- Continuously improving models

### Why Pythia?

**Alternatives considered**:
- Direct DLL integration (complex, platform-specific)
- Network sockets (latency, firewall issues)
- File-based communication (slow, polling overhead)

**Pythia advantages**:
- Embedded Python runtime (no external dependencies)
- Synchronous function calls
- Data serialization handled
- Cross-platform support
- Established in Arma community

### Why Async Python?

**Benefits**:
- Non-blocking LLM calls (can take 5-30s)
- Continued world scanning during decisions
- Better resource utilization
- Easier error handling

**Implementation**:
```python
# Async decision making
async def process_world_state(world_state):
    # This doesn't block other operations
    response = await llm_client.generate_orders(...)
    return response
```

### Why Command Queue?

**Problems solved**:
- Decouples decision making from execution
- Allows priority-based execution
- Prevents command flooding
- Thread-safe operation
- Enables rate limiting

**Alternative rejected**:
Direct execution - would block on failed commands and cause order-dependent issues.

### Why Multi-Provider Support?

**Rationale**:
- Different providers have different strengths
- Cost optimization (switch based on budget)
- Availability (fallback if one provider down)
- Feature access (Gemini caching, Claude reasoning)
- Future-proofing (new providers emerge)

### Why Sandbox Validation?

**Security**:
- Prevents malicious LLM responses
- Enforces mission constraints
- Protects server stability

**Examples of blocked actions**:
- Spawning unlimited units
- Moving groups outside AO
- Controlling player groups
- Invalid command types

---

## Extensibility

### Adding New Command Types

**1. Define command in Python** (`models/commands.py`):
```python
@dataclass
class NewCommand(Command):
    command_type: str = "new_command"
    special_param: str = ""
```

**2. Add to order parser** (`ai/order_parser.py`):
```python
# Add to parsing logic
```

**3. Add SQF application** (`fn_applyNewCommand.sqf`):
```sqf
params ["_group", "_params"];
// Implementation
```

**4. Update whitelist** (config.cpp):
```cpp
allowed_commands[] = {..., "new_command"};
```

### Adding New LLM Provider

**1. Implement client** (`ai/providers.py`):
```python
class NewProviderClient(BaseLLMClient):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.endpoint = config["endpoint"]

    async def generate_orders(self, world_state, objectives, history):
        # Implementation
        pass
```

**2. Update factory** (`ai/providers.py`):
```python
def create_llm_client(config):
    provider = config["provider"]
    if provider == "new_provider":
        return NewProviderClient(config)
    # ...
```

**3. Add to guardrails.json**:
```json
{
    "provider": "new_provider",
    "endpoint": "https://api.newprovider.com/v1/chat",
    "api_key": "...",
    ...
}
```

---

## See Also

- [API Reference](API-Reference.md) - Complete function documentation
- [LLM Configuration Guide](LLM-Configuration-Guide.md) - Provider setup
- [Command Reference](Command-Reference.md) - Command types
- [Mission Setup Guide](Mission-Setup-Guide.md) - Integration guide

---

**Last Updated**: 2025-12-05
