from pixel_detector import PixelDetector
from config_loader import ConfigLoader
import os
from datetime import datetime


class StateDetector:
    def __init__(self, config_loader, pixel_detector=None):
        self.config = config_loader
        self.detector = pixel_detector or PixelDetector(
            tolerance=config_loader.config.get("tolerance", 10),
            variance_percent=config_loader.config.get("variance_percent")
        )
        self.current_state = None
        self.last_detection_time = None
        self.detection_history = []
    
    def detect_state(self, screenshot):
        """Detect current state from screenshot"""
        # Check error states first (they have priority)
        for state_name in self.config.get_all_error_states():
            if self._check_state(screenshot, state_name, is_error=True):
                self._update_state(state_name, is_error=True)
                return state_name
        
        # Check normal states
        for state_name in self.config.get_all_states():
            if self._check_state(screenshot, state_name, is_error=False):
                self._update_state(state_name, is_error=False)
                return state_name
        
        # No state detected
        self._update_state(None)
        return None
    
    def _check_state(self, screenshot, state_name, is_error=False):
        """Check if screenshot matches a specific state"""
        if is_error:
            state_config = self.config.get_error_state(state_name)
        else:
            state_config = self.config.get_state(state_name)
        
        if not state_config:
            return False
        
        detection_pixels = state_config.get("detection_pixels", [])
        
        if not detection_pixels:
            return False
        
        # Check all detection pixels
        matches = 0
        for pixel_config in detection_pixels:
            x = pixel_config.get("x")
            y = pixel_config.get("y")
            expected_color = pixel_config.get("color")
            
            if x is None or y is None or expected_color is None:
                continue
            
            # Use variance_percent if available
            variance = self.config.config.get("variance_percent")
            if self.detector.check_pixel_color(screenshot, x, y, expected_color, variance_percent=variance):
                matches += 1
            else:
                # Debug: print what color was found
                actual_color = self.detector.get_pixel_color(screenshot, x, y)
                print(f"State '{state_name}' pixel mismatch at ({x},{y}): expected {expected_color}, got {actual_color}")
        
        # Require all pixels to match
        return matches == len(detection_pixels)
    
    def _update_state(self, state_name, is_error=False):
        """Update current state and history"""
        self.current_state = state_name
        self.last_detection_time = datetime.now()
        
        # Add to history
        self.detection_history.append({
            "state": state_name,
            "is_error": is_error,
            "timestamp": self.last_detection_time
        })
        
        # Keep only last 100 entries
        if len(self.detection_history) > 100:
            self.detection_history = self.detection_history[-100:]
    
    def get_current_state(self):
        """Get current state name"""
        return self.current_state
    
    def get_state_config(self):
        """Get configuration for current state"""
        if not self.current_state:
            return None
        
        # Check if it's an error state
        error_state = self.config.get_error_state(self.current_state)
        if error_state:
            return error_state
        
        return self.config.get_state(self.current_state)
    
    def is_in_state(self, state_name):
        """Check if currently in a specific state"""
        return self.current_state == state_name
    
    def get_detection_confidence(self, screenshot, state_name, is_error=False):
        """Get confidence score for a state (percentage of matching pixels)"""
        if is_error:
            state_config = self.config.get_error_state(state_name)
        else:
            state_config = self.config.get_state(state_name)
        
        if not state_config:
            return 0.0
        
        detection_pixels = state_config.get("detection_pixels", [])
        
        if not detection_pixels:
            return 0.0
        
        matches = 0
        for pixel_config in detection_pixels:
            x = pixel_config.get("x")
            y = pixel_config.get("y")
            expected_color = pixel_config.get("color")
            
            if x is None or y is None or expected_color is None:
                continue
            
            if self.detector.check_pixel_color(screenshot, x, y, expected_color):
                matches += 1
        
        return (matches / len(detection_pixels)) * 100
    
    def save_debug_screenshot(self, screenshot, state_name=None):
        """Save screenshot with state detection info for debugging"""
        debug_dir = "debug_screenshots"
        os.makedirs(debug_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        state_str = state_name or self.current_state or "unknown"
        filename = f"{debug_dir}/state_{state_str}_{timestamp}.png"
        
        # Draw detection points on screenshot (optional enhancement)
        screenshot.save(filename)
        print(f"Debug screenshot saved: {filename}")
    
    def get_state_history(self, limit=10):
        """Get recent state detection history"""
        return self.detection_history[-limit:]
    
    def time_in_current_state(self):
        """Get time spent in current state (seconds)"""
        if not self.last_detection_time:
            return 0
        
        return (datetime.now() - self.last_detection_time).total_seconds()


class StateValidator:
    """Helper class to validate and debug state detection"""
    
    def __init__(self, config_loader, pixel_detector=None):
        self.config = config_loader
        self.detector = pixel_detector or PixelDetector(tolerance=config_loader.config.get("tolerance", 10))
    
    def validate_state_pixels(self, screenshot, state_name, is_error=False):
        """Validate all detection pixels for a state and return detailed report"""
        if is_error:
            state_config = self.config.get_error_state(state_name)
        else:
            state_config = self.config.get_state(state_name)
        
        if not state_config:
            return {"error": f"State '{state_name}' not found"}
        
        detection_pixels = state_config.get("detection_pixels", [])
        
        report = {
            "state": state_name,
            "is_error": is_error,
            "total_pixels": len(detection_pixels),
            "matches": 0,
            "pixel_results": []
        }
        
        for i, pixel_config in enumerate(detection_pixels):
            x = pixel_config.get("x")
            y = pixel_config.get("y")
            expected_color = pixel_config.get("color")
            description = pixel_config.get("description", "")
            
            if x is None or y is None or expected_color is None:
                report["pixel_results"].append({
                    "index": i,
                    "error": "Missing x, y, or color",
                    "description": description
                })
                continue
            
            actual_color = self.detector.get_pixel_color(screenshot, x, y)
            matches = self.detector.check_pixel_color(screenshot, x, y, expected_color)
            
            if matches:
                report["matches"] += 1
            
            report["pixel_results"].append({
                "index": i,
                "x": x,
                "y": y,
                "expected_color": expected_color,
                "actual_color": actual_color,
                "matches": matches,
                "description": description
            })
        
        report["match_percentage"] = (report["matches"] / report["total_pixels"] * 100) if report["total_pixels"] > 0 else 0
        
        return report


if __name__ == "__main__":
    # Test the state detector
    config = ConfigLoader()
    detector = StateDetector(config)
    
    print("State detector initialized")
    print(f"Current state: {detector.get_current_state()}")
    print(f"Available states: {config.get_all_states()}")
    print(f"Available error states: {config.get_all_error_states()}")