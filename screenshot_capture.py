import win32gui
import win32ui
import win32con
from PIL import Image
import ctypes
from ctypes import windll
import os
import time

# Set process DPI awareness globally
windll.user32.SetProcessDPIAware()


class ScreenshotCapture:
    def __init__(self, window_title="ArkAscended"):
        self.window_title = window_title
        self.hwnd = None
        
    def find_window(self):
        """Find the Ark window by title"""
        try:
            self.hwnd = win32gui.FindWindow(None, self.window_title)
            if self.hwnd == 0:
                print(f"Window '{self.window_title}' not found")
                return False
            return True
        except Exception as e:
            print(f"Error finding window: {e}")
            return False
    
    def capture_window(self, save_path=None):
        """Capture screenshot of the window"""
        if not self.hwnd or not self.find_window():
            return None
            
        try:
            # Set DPI awareness again before capture
            windll.user32.SetProcessDPIAware()
            
            # Get window dimensions
            left, top, right, bot = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bot - top
            
            # Get device contexts
            hwndDC = win32gui.GetWindowDC(self.hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Copy window content - using 2 as parameter like in old code
            result = windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 2)
            
            # Convert to PIL Image
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            image = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Clean up
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hwndDC)
            
            if result == 1:
                # Save if path provided
                if save_path:
                    image.save(save_path)
                return image
            else:
                print("Error in capturing window image (PrintWindow failed)")
                return None
            
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None
    
    def get_window_rect(self):
        """Get window rectangle coordinates"""
        if not self.hwnd or not self.find_window():
            return None
        try:
            rect = win32gui.GetWindowRect(self.hwnd)
            from collections import namedtuple
            Rect = namedtuple('Rect', ['left', 'top', 'right', 'bottom'])
            return Rect(*rect)
        except Exception as e:
            print(f"Error getting window rect: {e}")
            return None
    
    def is_window_active(self):
        """Check if the window is active/focused"""
        try:
            return win32gui.GetForegroundWindow() == self.hwnd
        except:
            return False
    
    def bring_to_foreground(self):
        """Bring the window to foreground"""
        if not self.hwnd or not self.find_window():
            return False
        try:
            win32gui.SetForegroundWindow(self.hwnd)
            return True
        except:
            return False


if __name__ == "__main__":
    # Test the screenshot capture
    capture = ScreenshotCapture("ArkAscended")
    if capture.find_window():
        print("Window found!")
        img = capture.capture_window("test_screenshot.png")
        if img:
            print(f"Screenshot saved: {img.size}")
    else:
        print("Window not found!")