"""
Resource template loader for BATCOM

Loads and validates resource pool templates from resource_templates.json
"""

import json
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger('batcom.config.resource_loader')


class ResourceTemplateLoader:
    """Loads and manages resource pool templates"""

    def __init__(self, template_file: str = None):
        """
        Initialize resource template loader

        Args:
            template_file: Path to resource_templates.json (defaults to batcom/resource_templates.json)
        """
        if template_file is None:
            # Default to resource_templates.json in batcom directory
            batcom_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_file = os.path.join(batcom_dir, 'resource_templates.json')

        self.template_file = template_file
        self.templates: Dict[str, Any] = {}
        self._load_templates()

    def _load_templates(self):
        """Load templates from JSON file"""
        try:
            if not os.path.exists(self.template_file):
                logger.warning(f"Resource template file not found: {self.template_file}")
                return

            with open(self.template_file, 'r') as f:
                data = json.load(f)

            self.templates = data.get('templates', {})
            logger.info(f"Loaded {len(self.templates)} resource templates from {self.template_file}")

            # Log available templates
            for template_name in self.templates.keys():
                if not template_name.startswith('_'):  # Skip comment keys
                    logger.info(f"  - {template_name}: {self.templates[template_name].get('description', 'No description')}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse resource template file: {e}")
        except Exception as e:
            logger.error(f"Failed to load resource templates: {e}")

    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by name

        Args:
            template_name: Name of template (e.g., "minimal", "low", "medium", "high", "ultra_high")

        Returns:
            Template configuration dictionary, or None if not found
        """
        template = self.templates.get(template_name)
        if not template:
            logger.warning(f"Template '{template_name}' not found")
            return None

        return template

    def get_template_pool(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the resource pool from a template (sides and their assets)

        Args:
            template_name: Name of template

        Returns:
            Dictionary mapping side -> asset_type -> configuration
        """
        template = self.get_template(template_name)
        if not template:
            return None

        return template.get('sides', {})

    def list_templates(self) -> list:
        """
        Get list of available template names

        Returns:
            List of template names
        """
        return [name for name in self.templates.keys() if not name.startswith('_')]

    def validate_template(self, template_name: str) -> bool:
        """
        Validate that a template is properly structured

        Args:
            template_name: Name of template to validate

        Returns:
            True if template is valid, False otherwise
        """
        template = self.get_template(template_name)
        if not template:
            return False

        # Check required fields
        if 'sides' not in template:
            logger.error(f"Template '{template_name}' missing 'sides' field")
            return False

        sides = template['sides']
        if not isinstance(sides, dict):
            logger.error(f"Template '{template_name}' sides must be a dictionary")
            return False

        # Validate each side's assets
        for side, assets in sides.items():
            if not isinstance(assets, dict):
                logger.error(f"Template '{template_name}' side '{side}' assets must be a dictionary")
                return False

            for asset_type, config in assets.items():
                if not isinstance(config, dict):
                    logger.error(f"Template '{template_name}' asset '{asset_type}' config must be a dictionary")
                    return False

                # Check required asset fields
                if 'max' not in config:
                    logger.error(f"Template '{template_name}' asset '{asset_type}' missing 'max' field")
                    return False

                if 'unit_classes' not in config:
                    logger.error(f"Template '{template_name}' asset '{asset_type}' missing 'unit_classes' field")
                    return False

                if not isinstance(config['unit_classes'], list):
                    logger.error(f"Template '{template_name}' asset '{asset_type}' unit_classes must be a list")
                    return False

        logger.info(f"Template '{template_name}' validation passed")
        return True

    def create_custom_template(self, template_name: str, base_template: str = "medium",
                              modifications: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Create a custom template based on an existing template with modifications

        Args:
            template_name: Name for the new custom template
            base_template: Name of template to use as base
            modifications: Dictionary of modifications to apply

        Returns:
            New template dictionary, or None if base template not found

        Example:
            loader.create_custom_template(
                "my_custom",
                "medium",
                {
                    "EAST": {
                        "heavy_armor": {"max": 5},  # Increase tanks
                        "attack_helicopter": {"max": 0}  # Disable helicopters
                    }
                }
            )
        """
        base = self.get_template(base_template)
        if not base:
            logger.error(f"Base template '{base_template}' not found")
            return None

        # Deep copy the base template
        import copy
        custom = copy.deepcopy(base)
        custom['description'] = f"Custom template based on {base_template}"

        if modifications:
            sides = custom.get('sides', {})
            for side, asset_mods in modifications.items():
                if side not in sides:
                    logger.warning(f"Side '{side}' not in base template, creating new")
                    sides[side] = {}

                for asset_type, asset_config in asset_mods.items():
                    if asset_type not in sides[side]:
                        logger.warning(f"Asset '{asset_type}' not in base template for side '{side}', creating new")
                        sides[side][asset_type] = {
                            'max': 0,
                            'unit_classes': [],
                            'description': 'Custom asset',
                            'defense_only': False
                        }

                    # Update only the fields provided in modifications
                    sides[side][asset_type].update(asset_config)

        logger.info(f"Created custom template '{template_name}' based on '{base_template}'")
        return custom


# Global loader instance (singleton pattern)
_global_loader: Optional[ResourceTemplateLoader] = None


def get_loader(template_file: str = None) -> ResourceTemplateLoader:
    """
    Get or create the global resource template loader

    Args:
        template_file: Optional path to template file (only used on first call)

    Returns:
        Global ResourceTemplateLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = ResourceTemplateLoader(template_file)
    return _global_loader


def load_template(template_name: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to load a template by name

    Args:
        template_name: Name of template to load

    Returns:
        Resource pool dictionary (side -> asset_type -> config)
    """
    loader = get_loader()
    return loader.get_template_pool(template_name)


def list_available_templates() -> list:
    """
    Convenience function to list all available templates

    Returns:
        List of template names
    """
    loader = get_loader()
    return loader.list_templates()
