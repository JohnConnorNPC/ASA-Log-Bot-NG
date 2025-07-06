import os
import time
import sqlite3
from datetime import datetime
from PIL import Image
import pytesseract
import pyautogui

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class MemberProcessor:
    def __init__(self, config):
        self.config = config
        
        # Member detection coordinates
        self.member_coords = {
            # Online members indicator pixel
            "ONLINE_PIXEL": (630, 207),
            "ONLINE_COLOR": [128, 231, 255],  # RGB for online members
            
            # Member count region (shows "12/25" etc) - updated coordinates
            "COUNT_REGION": (553, 276, 704, 318),
            
            # Member list names region
            "LIST_REGION": (176, 327, 402, 910),
            
            # Scrollbar positions
            "SCROLLBAR_TOP": (702, 340),
            "SCROLLBAR_BOTTOM": (702, 889),
            "SCROLLBAR_POS": (702, 500),
            "SCROLLBAR_COLOR": [53, 133, 150],
            
            # Scroll position for mouse
            "SCROLL_X": 703,
            "SCROLL_Y": 581
        }
        
        # Tracking
        self.member_set = set()  # Unique member names
        self.last_write_time = time.time()
        self.write_interval = 60  # Write every 60 seconds
        self.seen_threshold = config.get('log_seen_threshold', 6)
        self.member_counts = {}  # Track how many times each member is seen
        self.last_scroll_direction = "down"
        self.online_member_count = 0  # Track the actual count from OCR
        self.member_last_seen = {}  # Track last seen time for each member
        self.offline_timeout = 120  # 2 minutes timeout for marking as offline
        
        # OCR configs
        self.count_ocr_config = '--psm 7 -c "tessedit_char_whitelist= 0123456789/"'
        self.name_ocr_config = '--psm 6'
        
        # Database configuration
        self.member_db_path = config.get('member_db', './member.db')
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for members"""
        with sqlite3.connect(self.member_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    times_seen INTEGER DEFAULT 1,
                    is_online INTEGER DEFAULT 1
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON members(name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_last_seen ON members(last_seen)')
            
            # Add is_online column if it doesn't exist (for existing databases)
            try:
                conn.execute('ALTER TABLE members ADD COLUMN is_online INTEGER DEFAULT 1')
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Create a table for member snapshots (historical record)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS member_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    member_count INTEGER,
                    members TEXT
                )
            ''')
    
    def is_members_visible(self, screenshot):
        """Check if the members list is visible"""
        try:
            x, y = self.member_coords["ONLINE_PIXEL"]
            pixel = screenshot.getpixel((x, y))
            expected = self.member_coords["ONLINE_COLOR"]
            
            # Check with tolerance
            tolerance = 20
            return all(abs(pixel[i] - expected[i]) <= tolerance for i in range(3))
        except:
            return False
    
    def read_member_count(self, screenshot):
        """Read the member count (e.g., "5/70")"""
        try:
            region = self.member_coords["COUNT_REGION"]
            cropped = screenshot.crop(region)
            
            # OCR the count
            text = pytesseract.image_to_string(cropped, config=self.count_ocr_config).strip()
            
            # Extract just the current count
            if "/" in text:
                current = text.split("/")[0].strip()
                if current.isdigit() and 1 <= int(current) <= 100:
                    return int(current)
        except Exception as e:
            print(f"Error reading member count: {e}")
        return None
    
    def read_member_names(self, screenshot):
        """Read the member names from the list with improved OCR"""
        try:
            region = self.member_coords["LIST_REGION"]
            cropped = screenshot.crop(region)
            
            # Resize 2x for better OCR (like log processor)
            width, height = cropped.size
            cropped = cropped.resize((width * 2, height * 2))
            
            # DON'T convert to grayscale - match log processor approach
            # Check if image has enough variance (not empty)
            pixels = list(cropped.convert('L').getdata())
            if pixels:
                mean = sum(pixels) / len(pixels)
                variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
                std_dev = variance ** 0.5
                
                # Skip if image is too uniform
                if std_dev < 10:
                    return []
            
            # OCR the names
            text = pytesseract.image_to_string(cropped, config=self.name_ocr_config).strip()
            
            # Split into lines and clean
            names = []
            for line in text.split('\n'):
                line = line.strip()
                # Improved validation
                if line and len(line) > 2:
                    # Must have some letters or numbers
                    if any(c.isalnum() for c in line):
                        # Skip lines that are mostly special characters
                        alnum_count = sum(1 for c in line if c.isalnum())
                        if alnum_count >= len(line) * 0.3:  # At least 30% alphanumeric
                            # Truncate at first parenthesis to remove Steam name
                            if '(' in line:
                                line = line[:line.index('(')].strip()
                            if line:  # Make sure we still have a name after truncation
                                names.append(line)
            
            return names
        except Exception as e:
            print(f"Error reading member names: {e}")
        return []
    
    def check_scrollbar_position(self, screenshot):
        """Check if scrollbar is at top, bottom, or middle"""
        try:
            # Check top
            x, y = self.member_coords["SCROLLBAR_TOP"]
            pixel = screenshot.getpixel((x, y))
            if self.is_scrollbar_color(pixel):
                return "top"
            
            # Check bottom
            x, y = self.member_coords["SCROLLBAR_BOTTOM"]
            pixel = screenshot.getpixel((x, y))
            if self.is_scrollbar_color(pixel):
                return "bottom"
            
            return "middle"
        except:
            return "unknown"
    
    def is_scrollbar_color(self, pixel):
        """Check if pixel matches scrollbar color"""
        expected = self.member_coords["SCROLLBAR_COLOR"]
        tolerance = 20
        return all(abs(pixel[i] - expected[i]) <= tolerance for i in range(3))
    
    def scroll_member_list(self, window_pos):
        """Scroll the member list"""
        # Use absolute coordinates
        scroll_x = 703
        scroll_y = 581
        
        # Move mouse to scroll position
        pyautogui.moveTo(scroll_x, scroll_y)
        time.sleep(0.1)
        
        # Determine scroll direction
        if self.last_scroll_direction == "down":
            pyautogui.scroll(-1500)  # Scroll down
        else:
            pyautogui.scroll(1500)   # Scroll up
    
    def update_member_tracking(self, names):
        """Update member tracking with new names"""
        current_time = time.time()
        
        for name in names:
            # Update last seen time
            self.member_last_seen[name] = current_time
            
            if name in self.member_counts:
                # Increment by 1.5 to reach threshold faster when seen
                # This compensates for the slower decrement
                self.member_counts[name] += 1.5
                # Check if we've reached the threshold (accounting for float)
                if self.member_counts[name] >= self.seen_threshold and name not in self.member_set:
                    count_str = f"{int(self.member_counts[name])}" if self.member_counts[name] == int(self.member_counts[name]) else f"{self.member_counts[name]:.1f}"
                    print(f"Member validated ({count_str}x): {name}")
            else:
                self.member_counts[name] = 1.5  # Start at 1.5 instead of 1
                print(f"New member detected: {name}")
            
            # Add to validated set if seen enough times
            if self.member_counts[name] >= self.seen_threshold:
                self.member_set.add(name)
    
    def remove_old_members(self):
        """Remove members not seen in last 4x threshold checks"""
        # Double the retention period without changing config
        threshold = self.seen_threshold * 4  # Was 2x, now 4x
        to_remove = []
        
        for name in list(self.member_counts.keys()):
            # Decrement count for members not in current view
            if name not in self.current_view_members:
                # Decrement more slowly - only by 0.5 instead of 1
                # This effectively doubles the time before removal
                self.member_counts[name] -= 0.5
                if self.member_counts[name] <= -threshold:
                    to_remove.append(name)
        
        # Remove old members
        for name in to_remove:
            del self.member_counts[name]
            if name in self.member_set:
                self.member_set.remove(name)
                print(f"Member removed (not seen for extended period): {name}")
        
        # Cleanup member_counts dict if it gets too large
        if len(self.member_counts) > 200:
            # Keep only members with positive counts
            self.member_counts = {k: v for k, v in self.member_counts.items() if v > 0}
            print(f"Cleaned up member_counts to {len(self.member_counts)} entries")
    
    def write_members_to_database(self):
        """Write current member list to database"""
        # Use OCR count if available, otherwise fall back to detected count
        member_count = self.online_member_count if self.online_member_count > 0 else len(self.member_set)
        
        try:
            with sqlite3.connect(self.member_db_path) as conn:
                # First, mark all members as offline who haven't been seen recently
                current_time = time.time()
                offline_members = []
                
                for member in list(self.member_set):
                    last_seen = self.member_last_seen.get(member, 0)
                    if current_time - last_seen > self.offline_timeout:
                        offline_members.append(member)
                        self.member_set.remove(member)
                        if member in self.member_counts:
                            del self.member_counts[member]
                        if member in self.member_last_seen:
                            del self.member_last_seen[member]
                        print(f"Member went offline (not seen for {int(current_time - last_seen)}s): {member}")
                
                # Update database for offline members
                for member in offline_members:
                    conn.execute('''
                        UPDATE members SET is_online = 0 WHERE name = ?
                    ''', (member,))
                
                # Update or insert each online member
                for member in self.member_set:
                    conn.execute('''
                        INSERT INTO members (name, first_seen, last_seen, times_seen, is_online)
                        VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 1)
                        ON CONFLICT(name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            times_seen = times_seen + 1,
                            is_online = 1
                    ''', (member,))
                
                # Save a snapshot with the OCR count
                members_json = ','.join(sorted(self.member_set))
                conn.execute('''
                    INSERT INTO member_snapshots (member_count, members)
                    VALUES (?, ?)
                ''', (member_count, members_json))
                
                conn.commit()
                print(f"Saved member count: {member_count} (OCR), detected names: {len(self.member_set)}, offline: {len(offline_members)}")
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Error saving members: {e}")
    
    def process_members(self, screenshot, window_pos):
        """Main method to process online members"""
        if not self.is_members_visible(screenshot):
            print("Members list not visible")
            return
        
        print("\n=== Processing Online Members ===")
        
        # Read member count
        count = self.read_member_count(screenshot)
        if count:
            print(f"Member count: {count}")
            self.online_member_count = count
        else:
            print("Could not read member count from OCR")
        
        # Read current visible members
        self.current_view_members = self.read_member_names(screenshot)
        print(f"Visible members: {len(self.current_view_members)}")
        
        # Update tracking
        self.update_member_tracking(self.current_view_members)
        
        # Remove old members
        self.remove_old_members()
        
        # Check if it's time to write
        current_time = time.time()
        if current_time - self.last_write_time >= self.write_interval:
            self.write_members_to_database()
            self.last_write_time = current_time
        
        # Check scrollbar and scroll if needed
        scrollbar_pos = self.check_scrollbar_position(screenshot)
        print(f"Scrollbar position: {scrollbar_pos}")
        
        if scrollbar_pos == "top":
            self.last_scroll_direction = "down"
            self.scroll_member_list(window_pos)
            print("Scrolling down...")
        elif scrollbar_pos == "bottom":
            self.last_scroll_direction = "up"
            self.scroll_member_list(window_pos)
            print("Scrolling up...")
        elif scrollbar_pos == "middle":
            # Continue in last direction
            self.scroll_member_list(window_pos)
            print(f"Scrolling {self.last_scroll_direction}...")
        
        # Show current tracked members
        print(f"\nOnline members (from OCR): {self.online_member_count}")
        print(f"Total validated member names: {len(self.member_set)}")
        
        # Show members being tracked but not yet validated
        tracking = [name for name, count in self.member_counts.items() 
                   if count > 0 and count < self.seen_threshold]
        if tracking:
            print(f"Members being tracked ({len(tracking)}):")
            for name in tracking[:5]:  # Show first 5
                count = self.member_counts[name]
                # Format count nicely (show as int if it's close to int)
                count_str = f"{int(count)}" if count == int(count) else f"{count:.1f}"
                print(f"  {name} ({count_str}/{self.seen_threshold})")
            if len(tracking) > 5:
                print(f"  ... and {len(tracking) - 5} more")


if __name__ == "__main__":
    # Test the member processor
    processor = MemberProcessor({'log_seen_threshold': 6})
    print("Member processor initialized")