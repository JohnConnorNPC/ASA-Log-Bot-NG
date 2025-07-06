import pyautogui
import pywinauto
import time
import win32gui
import win32con
from datetime import datetime


class ClickAutomation:
    def __init__(self, window_title="ArkAscended", click_delay=0.5):
        self.window_title = window_title
        self.click_delay = click_delay
        self.hwnd = None
        
        # Configure pyautogui
        pyautogui.FAILSAFE = False  # Disable failsafe for multi-monitor
        pyautogui.PAUSE = 0.1
        
        self.action_history = []
    
    def find_window(self):
        """Find the game window"""
        try:
            self.hwnd = win32gui.FindWindow(None, self.window_title)
            return self.hwnd != 0
        except:
            return False
    
    def bring_window_to_front(self):
        """Bring game window to foreground"""
        if not self.hwnd and not self.find_window():
            print(f"Window '{self.window_title}' not found")
            return False
        
        try:
            # Restore window if minimized
            if win32gui.IsIconic(self.hwnd):
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            
            # Bring to foreground
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.5)  # Give window time to come to front
            return True
        except Exception as e:
            print(f"Error bringing window to front: {e}")
            return False
    
    def get_window_rect(self):
        """Get window position and size"""
        if not self.hwnd and not self.find_window():
            return None
        
        try:
            return win32gui.GetWindowRect(self.hwnd)
        except:
            return None
    
    def click(self, x, y, button='left', clicks=2):  # Default to double-click like old code
        """Click at specific coordinates"""
        try:
            # Get window using pygetwindow (like old code)
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows:
                print(f"Window '{self.window_title}' not found")
                return False
            
            window = windows[0]
            
            # Focus window - try multiple methods
            if window.isActive == False:
                try:
                    # First try the old method
                    pywinauto.application.Application().connect(handle=window._hWnd).top_window().set_focus()
                except:
                    pass
                
                # Also click on the window title bar to ensure it's active
                # Click at window top center
                title_x = window.left + (window.width // 2)
                title_y = window.top + 10
                pyautogui.click(title_x, title_y)
                time.sleep(0.5)
            
            # Get window top-left position
            window_x, window_y = window.topleft
            target_x = window_x + x
            target_y = window_y + y
            
            # Sleep before mouse move (like old code)
            time.sleep(self.click_delay)
            
            # Move mouse to target position
            try:
                pyautogui.moveTo(target_x, target_y)  # No duration, instant like old code
                time.sleep(self.click_delay)
                
                # Click
                if clicks == 1:
                    pyautogui.click(target_x, target_y, button=button)
                else:
                    pyautogui.doubleClick(target_x, target_y, button=button)
                
                # The old code moves to absolute coordinates, not window-relative
                pyautogui.moveTo(1304, 701)
                time.sleep(self.click_delay)
                
            except Exception as e:
                # Try alternative method with win32api
                import win32api, win32con
                win32api.SetCursorPos((target_x, target_y))
                time.sleep(0.1)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, target_x, target_y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, target_x, target_y, 0, 0)
            
            # Record action
            self._record_action('click', {
                'x': x, 'y': y,
                'absolute_x': target_x, 'absolute_y': target_y,
                'button': button, 'clicks': clicks
            })
            
            # Post-click delay
            time.sleep(self.click_delay)
            
            # Move mouse to neutral position (optional)
            # pyautogui.moveTo(1304, 701)
            
            return True
            
        except Exception as e:
            print(f"Error clicking at ({x}, {y}): {e}")
            return False
    
    def double_click(self, x, y):
        """Double click at specific coordinates"""
        return self.click(x, y, clicks=2)
    
    def right_click(self, x, y):
        """Right click at specific coordinates"""
        return self.click(x, y, button='right')
    
    def press_key(self, key, hold_time=0):
        """Press a keyboard key"""
        if not self.bring_window_to_front():
            return False
        
        try:
            if hold_time > 0:
                pyautogui.keyDown(key)
                time.sleep(hold_time)
                pyautogui.keyUp(key)
            else:
                pyautogui.press(key)
            
            self._record_action('key', {'key': key, 'hold_time': hold_time})
            time.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"Error pressing key '{key}': {e}")
            return False
    
    def type_text(self, text, interval=0.1):
        """Type text"""
        if not self.bring_window_to_front():
            return False
        
        try:
            pyautogui.typewrite(text, interval=interval)
            self._record_action('type', {'text': text, 'interval': interval})
            time.sleep(0.2)
            return True
            
        except Exception as e:
            print(f"Error typing text: {e}")
            return False
    
    def key_combination(self, *keys):
        """Press a key combination (e.g., ctrl+a)"""
        if not self.bring_window_to_front():
            return False
        
        try:
            pyautogui.hotkey(*keys)
            self._record_action('hotkey', {'keys': keys})
            time.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"Error pressing key combination: {e}")
            return False
    
    def scroll(self, clicks, x=None, y=None):
        """Scroll mouse wheel"""
        if not self.bring_window_to_front():
            return False
        
        try:
            if x is not None and y is not None:
                rect = self.get_window_rect()
                if rect:
                    absolute_x = rect[0] + x
                    absolute_y = rect[1] + y
                    pyautogui.moveTo(absolute_x, absolute_y, duration=0.2)
            
            pyautogui.scroll(clicks)
            self._record_action('scroll', {'clicks': clicks, 'x': x, 'y': y})
            time.sleep(0.1)
            return True
            
        except Exception as e:
            print(f"Error scrolling: {e}")
            return False
    
    def drag(self, start_x, start_y, end_x, end_y, duration=1.0, button='left'):
        """Drag from one position to another"""
        if not self.bring_window_to_front():
            return False
        
        rect = self.get_window_rect()
        if not rect:
            return False
        
        window_x, window_y = rect[0], rect[1]
        
        try:
            pyautogui.moveTo(window_x + start_x, window_y + start_y, duration=0.2)
            pyautogui.dragTo(window_x + end_x, window_y + end_y, duration=duration, button=button)
            
            self._record_action('drag', {
                'start_x': start_x, 'start_y': start_y,
                'end_x': end_x, 'end_y': end_y,
                'duration': duration, 'button': button
            })
            
            time.sleep(0.2)
            return True
            
        except Exception as e:
            print(f"Error dragging: {e}")
            return False
    
    def wait(self, duration):
        """Wait for specified duration"""
        print(f"Waiting for {duration} seconds...")
        time.sleep(duration)
        self._record_action('wait', {'duration': duration})
        return True
    
    def execute_action(self, action):
        """Execute an action from config"""
        action_type = action.get('type')
        
        if action_type == 'click':
            return self.click(action.get('x'), action.get('y'), clicks=action.get('clicks', 2))
        
        elif action_type == 'double_click':
            return self.double_click(action.get('x'), action.get('y'))
        
        elif action_type == 'right_click':
            return self.right_click(action.get('x'), action.get('y'))
        
        elif action_type == 'key':
            return self.press_key(action.get('key'), action.get('hold_time', 0))
        
        elif action_type == 'type':
            return self.type_text(action.get('text'), action.get('interval', 0.1))
        
        elif action_type == 'hotkey':
            keys = action.get('keys', [])
            return self.key_combination(*keys)
        
        elif action_type == 'scroll':
            return self.scroll(action.get('clicks'), action.get('x'), action.get('y'))
        
        elif action_type == 'drag':
            return self.drag(
                action.get('start_x'), action.get('start_y'),
                action.get('end_x'), action.get('end_y'),
                action.get('duration', 1.0), action.get('button', 'left')
            )
        
        elif action_type == 'wait':
            return self.wait(action.get('duration', 1))
        
        elif action_type == 'complete':
            print("Task marked as complete")
            return True
        
        else:
            print(f"Unknown action type: {action_type}")
            return False
    
    def _record_action(self, action_type, details):
        """Record action in history"""
        self.action_history.append({
            'timestamp': datetime.now(),
            'type': action_type,
            'details': details
        })
        
        # Keep only last 100 actions
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-100:]
    
    def get_action_history(self, limit=10):
        """Get recent action history"""
        return self.action_history[-limit:]
    
    def reset_mouse_position(self):
        """Move mouse to a neutral position"""
        try:
            screen_width, screen_height = pyautogui.size()
            pyautogui.moveTo(screen_width // 2, screen_height // 2, duration=0.2)
            return True
        except:
            return False


if __name__ == "__main__":
    # Test the automation
    automation = ClickAutomation()
    
    if automation.find_window():
        print("Window found!")
        print(f"Window rect: {automation.get_window_rect()}")
        
        # Test bringing window to front
        if automation.bring_window_to_front():
            print("Window brought to front")
    else:
        print("Window not found")