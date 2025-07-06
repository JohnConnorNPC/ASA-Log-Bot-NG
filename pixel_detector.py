from PIL import Image
import numpy as np


class PixelDetector:
    def __init__(self, tolerance=10, variance_percent=None):
        """
        Initialize pixel detector with color tolerance
        tolerance: Maximum difference allowed for each RGB channel (absolute)
        variance_percent: Percentage variance allowed (0-100), overrides tolerance if set
        """
        self.tolerance = tolerance
        self.variance_percent = variance_percent
    
    def get_pixel_color(self, image, x, y):
        """Get RGB color at specific pixel coordinate"""
        if isinstance(image, str):
            image = Image.open(image)
        
        # Ensure coordinates are within bounds
        width, height = image.size
        if x < 0 or x >= width or y < 0 or y >= height:
            return None
            
        return image.getpixel((x, y))[:3]  # Return RGB only, ignore alpha if present
    
    def color_matches(self, color1, color2, tolerance=None, variance_percent=None):
        """Check if two colors match within tolerance"""
        if color1 is None or color2 is None:
            return False
        
        # Use variance_percent if specified
        if variance_percent is not None:
            for c1, c2 in zip(color1, color2):
                # Calculate allowed variance based on percentage
                # For low values, use a minimum variance of 5
                allowed_variance = max(5, int(c2 * variance_percent / 100))
                if abs(c1 - c2) > allowed_variance:
                    return False
            return True
        
        # Otherwise use absolute tolerance
        if tolerance is None:
            tolerance = self.tolerance
            
        # Check each channel
        for c1, c2 in zip(color1, color2):
            if abs(c1 - c2) > tolerance:
                return False
        return True
    
    def find_color_in_region(self, image, target_color, region=None, tolerance=None):
        """
        Find all pixels matching target color in a region
        region: (x1, y1, x2, y2) or None for whole image
        Returns list of (x, y) coordinates
        """
        if isinstance(image, str):
            image = Image.open(image)
            
        if tolerance is None:
            tolerance = self.tolerance
            
        width, height = image.size
        
        # Define search region
        if region:
            x1, y1, x2, y2 = region
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(width, x2)
            y2 = min(height, y2)
        else:
            x1, y1, x2, y2 = 0, 0, width, height
        
        matches = []
        
        # Convert to numpy array for faster processing
        img_array = np.array(image)
        target_array = np.array(target_color)
        
        for y in range(y1, y2):
            for x in range(x1, x2):
                pixel = img_array[y, x][:3]  # RGB only
                if np.all(np.abs(pixel - target_array) <= tolerance):
                    matches.append((x, y))
        
        return matches
    
    def check_pixel_color(self, image, x, y, expected_color, tolerance=None, variance_percent=None):
        """Check if pixel at (x,y) matches expected color"""
        actual_color = self.get_pixel_color(image, x, y)
        return self.color_matches(actual_color, expected_color, tolerance, variance_percent)
    
    def find_first_color(self, image, target_colors, region=None, tolerance=None):
        """
        Find the first occurrence of any target color
        target_colors: list of RGB tuples
        Returns: (x, y, color) or None
        """
        if isinstance(image, str):
            image = Image.open(image)
            
        if tolerance is None:
            tolerance = self.tolerance
            
        width, height = image.size
        
        # Define search region
        if region:
            x1, y1, x2, y2 = region
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(width, x2)
            y2 = min(height, y2)
        else:
            x1, y1, x2, y2 = 0, 0, width, height
        
        # Search for colors
        for y in range(y1, y2):
            for x in range(x1, x2):
                pixel = image.getpixel((x, y))[:3]
                for target_color in target_colors:
                    if self.color_matches(pixel, target_color, tolerance):
                        return (x, y, target_color)
        
        return None
    
    def get_average_color(self, image, region):
        """Get average color in a region"""
        if isinstance(image, str):
            image = Image.open(image)
            
        x1, y1, x2, y2 = region
        width, height = image.size
        
        # Ensure bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(width, x2)
        y2 = min(height, y2)
        
        # Crop and get average
        cropped = image.crop((x1, y1, x2, y2))
        img_array = np.array(cropped)
        avg_color = np.mean(img_array.reshape(-1, img_array.shape[-1]), axis=0)
        
        return tuple(int(c) for c in avg_color[:3])
    
    def color_in_region_percentage(self, image, target_color, region, tolerance=None):
        """Calculate percentage of pixels matching target color in region"""
        matches = self.find_color_in_region(image, target_color, region, tolerance)
        x1, y1, x2, y2 = region
        total_pixels = (x2 - x1) * (y2 - y1)
        
        if total_pixels == 0:
            return 0.0
            
        return (len(matches) / total_pixels) * 100
    

def parse_color_string(color_str):
    """Parse color string in format 'RGB:r,g,b' or '(r,g,b)' or 'r,g,b'"""
    if color_str.startswith("RGB:"):
        color_str = color_str[4:]
    
    color_str = color_str.strip("()")
    parts = color_str.split(",")
    
    if len(parts) != 3:
        raise ValueError(f"Invalid color format: {color_str}")
    
    return tuple(int(part.strip()) for part in parts)


if __name__ == "__main__":
    # Test the pixel detector
    detector = PixelDetector(tolerance=10)
    
    # Example usage
    print("Pixel detector initialized with tolerance:", detector.tolerance)
    
    # Test color parsing
    test_colors = ["RGB:255,255,255", "(128,128,128)", "0,0,255"]
    for color_str in test_colors:
        parsed = parse_color_string(color_str)
        print(f"Parsed '{color_str}' to {parsed}")