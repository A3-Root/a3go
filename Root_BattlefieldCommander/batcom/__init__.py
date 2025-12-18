"""
Root's Battlefield Commander (BATCOM)
AI-driven tactical command system for Arma 3

This package provides the Python core for BATCOM, handling:
- World state management
- Decision making (rule-based and AI-assisted)
- Command generation and validation
- Event processing
"""

# Version info
VERSION = "1.0.0"
AUTHOR = "Root"

# Import api module to make functions accessible
try:
    from . import api
    _API_LOADED = True
except Exception as e:
    _API_LOADED = False
    _API_ERROR = str(e)
    # Create a dummy api module to prevent crashes
    class DummyAPI:
        @staticmethod
        def init(*args, **kwargs):
            return {"status": "error", "error": f"API module failed to load: {_API_ERROR}"}

        @staticmethod
        def shutdown(*args, **kwargs):
            return {"status": "error", "error": f"API module failed to load: {_API_ERROR}"}

        @staticmethod
        def is_initialized(*args, **kwargs):
            return False

        @staticmethod
        def get_version(*args, **kwargs):
            return f"ERROR: {_API_ERROR}"

        @staticmethod
        def world_snapshot(*args, **kwargs):
            return {"status": "error", "error": f"API module failed to load: {_API_ERROR}"}

        @staticmethod
        def get_pending_commands(*args, **kwargs):
            return {"status": "error", "error": f"API module failed to load: {_API_ERROR}"}

        @staticmethod
        def batcom_init(*args, **kwargs):
            return {"status": "error", "error": f"API module failed to load: {_API_ERROR}"}

        @staticmethod
        def test_gemini_connection(*args, **kwargs):
            return {"status": "error", "error": f"API module failed to load: {_API_ERROR}"}

    api = DummyAPI()

# Create module-level wrapper functions to avoid import issues
def init(config_dict):
    """Initialize BATCOM"""
    return api.init(config_dict)

def shutdown():
    """Shutdown BATCOM"""
    return api.shutdown()

def is_initialized():
    """Check if BATCOM is initialized"""
    return api.is_initialized()

def get_version():
    """Get BATCOM version"""
    return api.get_version()

def world_snapshot(snapshot_data):
    """Process world state snapshot"""
    return api.world_snapshot(snapshot_data)

def get_pending_commands():
    """Get pending commands"""
    return api.get_pending_commands()

def batcom_init(command, params, flag=False):
    """Handle admin commands"""
    return api.batcom_init(command, params, flag)

def test_gemini_connection():
    """Test Gemini LLM connection"""
    return api.test_gemini_connection()

def test_what_we_receive(data):
    """Test what Python receives from SQF"""
    import json
    try:
        result = f"Type: {type(data)}"
        result += f" | Value: {str(data)[:200]}"
        if isinstance(data, dict):
            result += f" | Keys: {list(data.keys())}"
        elif isinstance(data, (list, tuple)):
            result += f" | Length: {len(data)}"
            if len(data) > 0:
                result += f" | First elem type: {type(data[0])}"
        return result
    except Exception as e:
        return f"ERROR: {e}"

def debug_init():
    """Debug init - returns detailed error info as string"""
    try:
        # Test imports step by step
        steps = []

        try:
            from .utils.logging_setup import setup_logging
            steps.append("✓ utils.logging_setup")
        except Exception as e:
            return f"✗ utils.logging_setup: {e}"

        try:
            from .world.scanner import WorldScanner
            steps.append("✓ world.scanner")
        except Exception as e:
            return f"✗ world.scanner: {e}"

        try:
            from .commands.queue import CommandQueue
            steps.append("✓ commands.queue")
        except Exception as e:
            return f"✗ commands.queue: {e}"

        try:
            from .runtime.state import StateManager
            steps.append("✓ runtime.state")
        except Exception as e:
            return f"✗ runtime.state: {e}"

        try:
            from .runtime.admin import AdminCommandHandler
            steps.append("✓ runtime.admin")
        except Exception as e:
            return f"✗ runtime.admin: {e}"

        try:
            from .runtime.commander import batcom
            steps.append("✓ runtime.commander")
        except Exception as e:
            return f"✗ runtime.commander: {e}"

        # All imports successful - now test init with minimal config
        try:
            test_config = {
                'logging': {},
                'scan': {},
                'runtime': {},
                'ai': {'enabled': False},
                'safety': {}
            }
            result = api.init(test_config)
            steps.append(f"✓ init test: {result}")
        except Exception as e:
            return f"✗ init test failed: {e}"

        return "SUCCESS: " + " | ".join(steps)

    except Exception as e:
        return f"ERROR: {str(e)}"

# Export list
__all__ = [
    "init",
    "shutdown",
    "is_initialized",
    "get_version",
    "world_snapshot",
    "get_pending_commands",
    "batcom_init",
    "test_gemini_connection",
    "debug_init",
    "test_what_we_receive",
    "VERSION",
    "AUTHOR"
]
