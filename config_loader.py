import json
import os
from datetime import datetime


class ConfigLoader:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = None
        self.load()
    
    def load(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print(f"Configuration loaded from {self.config_path}")
        except FileNotFoundError:
            print(f"Config file not found: {self.config_path}")
            self.config = self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"Error parsing config JSON: {e}")
            self.config = self.get_default_config()
    
    def save(self):
        """Save current configuration to file"""
        # Backup existing config
        if os.path.exists(self.config_path):
            backup_path = f"{self.config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(self.config_path, backup_path)
            print(f"Backed up config to {backup_path}")
        
        # Save new config
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
        print(f"Configuration saved to {self.config_path}")
    
    def get_default_config(self):
        """Return default configuration"""
        return {
            "window_title": "ArkAscended",
            "tolerance": 10,
            "click_delay": 0.5,
            "screenshot_dir": "screenshots/",
            "states": {},
            "error_states": {}
        }
    
    def get_state(self, state_name):
        """Get a specific state configuration"""
        return self.config.get("states", {}).get(state_name)
    
    def get_error_state(self, state_name):
        """Get a specific error state configuration"""
        return self.config.get("error_states", {}).get(state_name)
    
    def add_state(self, state_name, state_config):
        """Add or update a state"""
        if "states" not in self.config:
            self.config["states"] = {}
        self.config["states"][state_name] = state_config
    
    def add_detection_pixel(self, state_name, x, y, color, description=""):
        """Add a detection pixel to a state"""
        state = self.get_state(state_name)
        if not state:
            print(f"State {state_name} not found")
            return
        
        if "detection_pixels" not in state:
            state["detection_pixels"] = []
        
        state["detection_pixels"].append({
            "x": x,
            "y": y,
            "color": color,
            "description": description
        })
    
    def add_action(self, state_name, action):
        """Add an action to a state"""
        state = self.get_state(state_name)
        if not state:
            print(f"State {state_name} not found")
            return
        
        if "actions" not in state:
            state["actions"] = []
        
        state["actions"].append(action)
    
    def get_all_states(self):
        """Get all state names"""
        return list(self.config.get("states", {}).keys())
    
    def get_all_error_states(self):
        """Get all error state names"""
        return list(self.config.get("error_states", {}).keys())
    
    def validate_config(self):
        """Validate configuration structure"""
        required_fields = ["window_title", "tolerance", "click_delay"]
        
        for field in required_fields:
            if field not in self.config:
                print(f"Warning: Required field '{field}' missing from config")
                return False
        
        # Validate states
        for state_name, state in self.config.get("states", {}).items():
            if "detection_pixels" not in state:
                print(f"Warning: State '{state_name}' missing detection_pixels")
            
            # Validate detection pixels
            for pixel in state.get("detection_pixels", []):
                if not all(key in pixel for key in ["x", "y", "color"]):
                    print(f"Warning: Invalid detection pixel in state '{state_name}'")
            
            # Validate actions
            for action in state.get("actions", []):
                if "type" not in action:
                    print(f"Warning: Action missing type in state '{state_name}'")
        
        return True


class StateBuilder:
    """Helper class to build state configurations"""
    
    def __init__(self, name):
        self.state = {
            "name": name,
            "detection_pixels": [],
            "actions": [],
            "next_state": None
        }
    
    def add_detection_pixel(self, x, y, color, description=""):
        """Add a detection pixel"""
        self.state["detection_pixels"].append({
            "x": x,
            "y": y,
            "color": color,
            "description": description
        })
        return self
    
    def add_click_action(self, x, y, name="", description=""):
        """Add a click action"""
        self.state["actions"].append({
            "name": name or f"click_{x}_{y}",
            "type": "click",
            "x": x,
            "y": y,
            "description": description
        })
        return self
    
    def add_key_action(self, key, name="", description=""):
        """Add a keyboard action"""
        self.state["actions"].append({
            "name": name or f"key_{key}",
            "type": "key",
            "key": key,
            "description": description
        })
        return self
    
    def add_wait_action(self, duration, name="", description=""):
        """Add a wait action"""
        self.state["actions"].append({
            "name": name or f"wait_{duration}",
            "type": "wait",
            "duration": duration,
            "description": description
        })
        return self
    
    def add_type_action(self, text, name="", description=""):
        """Add a typing action"""
        self.state["actions"].append({
            "name": name or f"type_text",
            "type": "type",
            "text": text,
            "description": description
        })
        return self
    
    def set_next_state(self, next_state):
        """Set the next state"""
        self.state["next_state"] = next_state
        return self
    
    def build(self):
        """Return the built state"""
        return self.state


if __name__ == "__main__":
    # Test the config loader
    config = ConfigLoader()
    
    if config.validate_config():
        print("Configuration is valid")
    
    print("\nAvailable states:")
    for state in config.get_all_states():
        print(f"  - {state}")
    
    print("\nAvailable error states:")
    for state in config.get_all_error_states():
        print(f"  - {state}")