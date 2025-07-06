import os
import time
import re
import threading
import uuid
import sqlite3
import base64
import json
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class LogProcessor:
    def __init__(self, config):
        self.config = config
        self.log_crop_coords = {
            "START_X": 780,
            "START_Y": 217,
            "END_Y": 820,
            "WIDTH": 380,
            "HEIGHT": 17,
            "LINE_SPACING": 20
        }
        # OCR config - PSM 6 only (whitelist doesn't seem to work with current Tesseract version)
        # The old system uses a whitelist but it may not be compatible with newer versions
        self.ocr_config = '--psm 6'
        self.log_pattern = re.compile(r'^Day \d{1,6}, \d{2}:\d{2}:\d{2}: ')
        self.line_counts = {}  # Track individual lines
        self.validated_lines = {}  # Lines that have passed threshold
        self.printed_entries = {}
        self.log_seen_threshold = config.get('log_seen_threshold', 4)  # Get from config, default to 4
        self.temp_folder = "temp/"
        os.makedirs(self.temp_folder, exist_ok=True)
        
        # Database configuration
        self.log_db_path = config.get('log_db', './log.db')
        self.log_images_db_path = config.get('log_images_db', './log_images.db')
        
        # Initialize databases
        self.init_databases()
        
        # Load already processed entries from database
        self.load_processed_entries()
        
        # Load replacements configuration
        self.replacements_file = config.get('replacements_file', 'replacements.json')
        self.load_replacements()
    
    def init_databases(self):
        """Initialize SQLite databases for logs and images"""
        # Create logs database
        with sqlite3.connect(self.log_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    day INTEGER,
                    time TEXT,
                    entry_text TEXT UNIQUE,
                    image_id TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_entry_text ON logs(entry_text)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_day_time ON logs(day, time)')
        
        # Create log images database
        with sqlite3.connect(self.log_images_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_images (
                    id TEXT PRIMARY KEY,
                    image_data BLOB,
                    width INTEGER,
                    height INTEGER
                )
            ''')
    
    def load_processed_entries(self):
        """Load already processed entries from database - only recent ones to prevent memory issues"""
        with sqlite3.connect(self.log_db_path) as conn:
            # Only load entries from the last 24 hours to prevent unlimited memory growth
            cursor = conn.execute('''
                SELECT entry_text FROM logs 
                WHERE timestamp > datetime('now', '-1 day')
                ORDER BY id DESC
                LIMIT 10000
            ''')
            for row in cursor:
                self.printed_entries[row[0]] = True
        print(f"Loaded {len(self.printed_entries)} recent entries from database")
    
    def load_replacements(self):
        """Load replacements from JSON file"""
        self.replacements = {}
        self.special_formatting = {}
        
        if os.path.exists(self.replacements_file):
            try:
                with open(self.replacements_file, 'r') as f:
                    data = json.load(f)
                    self.replacements = data.get('replacements', {})
                    self.special_formatting = data.get('special_formatting', {})
                print(f"Loaded {len(self.replacements)} replacement rules from {self.replacements_file}")
            except Exception as e:
                print(f"Error loading replacements file: {e}")
                # Fall back to built-in replacements
                self.replacements = self.get_default_replacements()
        else:
            print(f"Replacements file not found: {self.replacements_file}, using defaults")
            self.replacements = self.get_default_replacements()
    
    def get_default_replacements(self):
        """Get default replacements if no config file"""
        return {
            'killea': 'killed',
            'Killea': 'killed',
            'Killed': 'killed',
            'promoted toa': 'promoted to a',
            'removed trom': 'removed from'
        }
    
    def is_newer_entry(self, entry1, entry2):
        """Check if entry1 is newer than entry2 based on Day and time"""
        # Extract day and time from entries
        match1 = self.log_pattern.match(entry1)
        match2 = self.log_pattern.match(entry2)
        
        if not match1 or not match2:
            return False
        
        # Parse "Day X, HH:MM:SS:"
        day1_match = re.match(r'Day (\d+), (\d{2}):(\d{2}):(\d{2}):', entry1)
        day2_match = re.match(r'Day (\d+), (\d{2}):(\d{2}):(\d{2}):', entry2)
        
        if not day1_match or not day2_match:
            return False
        
        day1 = int(day1_match.group(1))
        hour1 = int(day1_match.group(2))
        min1 = int(day1_match.group(3))
        sec1 = int(day1_match.group(4))
        
        day2 = int(day2_match.group(1))
        hour2 = int(day2_match.group(2))
        min2 = int(day2_match.group(3))
        sec2 = int(day2_match.group(4))
        
        # Compare days first
        if day1 != day2:
            return day1 > day2
        
        # Same day, compare time
        time1 = hour1 * 3600 + min1 * 60 + sec1
        time2 = hour2 * 3600 + min2 * 60 + sec2
        return time1 > time2
    
    def crop_image_to_lines(self, image):
        """Crops the screenshot into individual log lines"""
        y = self.log_crop_coords["START_Y"]
        cropped_lines = []
        line_adjustments = {3: 0, 4: -1, 8: -1, 12: -1, 16: -1}  # Y adjustments at specific lines
        count = 0
        
        while (y + self.log_crop_coords["HEIGHT"] + self.log_crop_coords["LINE_SPACING"] <= image.height) and (y < self.log_crop_coords["END_Y"]):
            crop_coords = (
                self.log_crop_coords["START_X"], 
                y, 
                self.log_crop_coords["START_X"] + self.log_crop_coords["WIDTH"], 
                y + self.log_crop_coords["HEIGHT"]
            )
            cropped_line = image.crop(crop_coords)
            cropped_lines.append(cropped_line)
            y += self.log_crop_coords["LINE_SPACING"]
            count += 1
            
            # Apply line adjustments
            if count in line_adjustments:
                y += line_adjustments[count]
                
        return cropped_lines
    
    def ocr_line(self, image, line_num=None):
        """Perform OCR on a single line image - matching old system"""
        try:
            # The old system does NOT convert to grayscale for logs
            # The old system: ocrImage(cropped_line, False, True, False) where 3rd param is greyscale=False
            
            # OCR the image with whitelist config
            text = pytesseract.image_to_string(image, config=self.ocr_config)
            
            # Strip whitespace
            text = text.strip()
            
            # Replace newlines with spaces (like old system - replace_newline=True)
            text = text.replace('\n', ' ')
            
            # Apply OCR corrections
            text = self.apply_ocr_corrections(text)
            
            # Simple validation - must have some content
            # Lowered threshold to catch short continuation lines like "killed!"
            if not text or len(text) < 2:
                if line_num is not None and len(text) == 1:
                    print(f"Line {line_num}: Very short text detected: '{text}'")
                return ""
            
            return text
        except Exception as e:
            print(f"OCR error: {e}")
            return ""
    
    def apply_ocr_corrections(self, text):
        """Apply OCR corrections from replacements file"""
        # Apply all replacements from the loaded configuration
        for old, new in self.replacements.items():
            text = text.replace(old, new)
            
        # Apply special formatting if configured
        if self.special_formatting:
            # Handle word spacing
            spacing_words = self.special_formatting.get('word_spacing', [])
            for word in spacing_words:
                text = text.replace(word, f" {word} ")
                text = text.replace(f"  {word}", f" {word}")
                text = text.replace(f"{word}  ", f"{word} ")
                text = text.replace(f"{word} !", f"{word}!")
            
            # Clean endings
            clean_endings = self.special_formatting.get('clean_endings', {})
            if clean_endings.get('remove_quotes'):
                text = text.replace("'", "'").replace("'", "'").replace('"', "'")
                text = text.replace("''", "'")
            
            if clean_endings.get('fix_parentheses'):
                text = text.replace("{", "(").replace("}", ")")
                text = text.replace(")))", ")!")
                text = text.replace("'l", "'!")
        
        # Always remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
            
        return text.strip()
    
    def line_matches_format(self, line):
        """Check if line matches log format"""
        return self.log_pattern.match(line) is not None
    
    def process_screenshot(self, screenshot):
        """Process a screenshot and track individual lines"""
        cropped_lines = self.crop_image_to_lines(screenshot)
        
        # OCR all lines in parallel
        ocr_results = {}
        threads = []
        
        def ocr_worker(index, line):
            # Don't skip lines based on contrast - process everything
            # Even low contrast lines might contain important continuation text
            
            ocr_results[index] = self.ocr_line(line, line_num=index)
        
        for i, line in enumerate(cropped_lines):
            # Resize BEFORE OCR, just like old system (default resize, no filter specified)
            width, height = line.size
            resized_line = line.resize((width * 2, height * 2))
            
            thread = threading.Thread(target=ocr_worker, args=(i, resized_line))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Build complete messages first (like old system), then track them
        current_message = ""
        message_images = {}
        current_images = []
        
        # Print all OCR results in order
        print("\n=== OCR Results in Order ===")
        for i in range(len(cropped_lines)):
            line_text = ocr_results.get(i, "").strip()
            # Print ALL lines including empty ones to debug
            print(f"Line {i:2d}: '{line_text}'")
            
            # Fix common format issues for Day lines
            if line_text.startswith("Day ") and not self.line_matches_format(line_text):
                line_text = re.sub(r'(Day \d{1,6}),?', r'\1, ', line_text)
                line_text = re.sub(r'(\d{2}:\d{2}:\d{2}):? ?', r'\1: ', line_text)
                line_text = re.sub(r'\s+', ' ', line_text)
            
            # Build messages like old system
            if line_text and self.line_matches_format(line_text):
                # Start of new log entry
                if current_message:
                    message_images[current_message.strip()] = current_images
                current_message = line_text
                current_images = [cropped_lines[i]]
            else:
                # Continuation line - process like old system
                if not line_text.startswith("Day "):
                    # Append ALL lines (even empty) to current message if we have one
                    if current_message:
                        # Add space and text (even if empty - maintains spacing)
                        current_message = current_message.strip() + " " + line_text.strip()
                        current_images.append(cropped_lines[i])
                else:
                    # Line starts with "Day" but doesn't match format
                    # Old system clears the message and prints warning
                    current_message = ""
                    print(f"Problem line starting with Day: {line_text}")
        
        # Don't forget the last message
        if current_message:
            message_images[current_message.strip()] = current_images
        
        # Apply special rules to complete partial messages
        completed_messages = {}
        for message, images in message_images.items():
            # SPECIAL COMPLETION RULES:
            # These rules help complete messages that are commonly split across lines
            
            # Rule 1: "added to the Tribe" - always ends with "Tribe!"
            if "added to the" in message and not message.endswith("Tribe!"):
                idx = message.find("added to the")
                if idx != -1:
                    message = message[:idx + len("added to the")] + " Tribe!"
            
            # Rule 2: "was promoted to" - DON'T add anything if it ends with this
            # The rank is likely on the next line, so leave it incomplete
            # The continuation line handling will append the rank
            # (Removed the rule that was adding "a Rank!")
            
            # Rule 3: "Somebody was" - likely "Somebody was killed"
            if message.endswith("Somebody was"):
                message = message + " killed!"
            
            # Rule 4: "was promoted" without ending
            if message.endswith("was promoted"):
                message = message + " to a Rank!"
            
            # Rule 5: Clean up incomplete rank assignments
            if "set to Rank" in message and message.endswith("!"):
                # This one seems complete, keep as is
                pass
            elif "set to Rank" in message and not message.endswith("!"):
                message = message.rstrip(".") + "!"
            
            # Rule 6: "was Killed!" or "was Killea!" (OCR error)
            if message.endswith("was Killed!") or message.endswith("was Killea!"):
                # These are complete but fix the OCR error
                message = message.replace("was Killea!", "was killed!")
                message = message.replace("was Killed!", "was killed!")
            
            # Rule 7: "promoted toa" (OCR error - missing space)
            if "promoted toa" in message:
                message = message.replace("promoted toa", "promoted to a")
            
            # Rule 7b: Handle partial promotion messages better
            # Only complete if we have partial rank names, NOT if it just ends with "promoted to"
            if "promoted to" in message and not message.endswith("!") and not message.endswith("promoted to"):
                # Check if it ends with partial rank names
                if message.endswith("promoted to Ad"):
                    message = message + "min!"
                elif message.endswith("promoted to Adm"):
                    message = message + "in!"
                elif message.endswith("promoted to Admi"):
                    message = message + "n!"
                elif message.endswith("promoted to M"):
                    message = message + "ember!"
                elif message.endswith("promoted to Me"):
                    message = message + "mber!"
                elif message.endswith("promoted to Mem"):
                    message = message + "ber!"
                elif message.endswith("promoted to Memb"):
                    message = message + "er!"
                elif message.endswith("promoted to Membe"):
                    message = message + "r!"
                # If we have a complete rank name but no !, add it
                elif ("promoted to Admin" in message or 
                      "promoted to Member" in message or
                      "promoted to Officer" in message or
                      "promoted to Leader" in message):
                    message = message + "!"
            
            # Rule 8: "removed trom" (OCR error - should be "from")
            if "removed trom" in message:
                message = message.replace("removed trom", "removed from")
            
            # Rule 9: "starved to" incomplete
            if message.endswith("starved to"):
                message = message + " death!"
            
            # Rule 10: "Your Tribe killed" entries (ensure they end with !)
            if "Your Tribe killed" in message and not message.endswith("!"):
                message = message.rstrip(".") + "!"
            
            # Rule 11: "demolished a" entries (ensure they end with !)
            if "demolished a" in message and not message.endswith("!"):
                message = message.rstrip(".") + "!"
            
            # Rule 12: "was destroyed" entries
            if "was destroyed" in message and not message.endswith("!"):
                message = message.rstrip(".") + "!"
            
            # Rule 13: "Tamed a/an" entries
            if ("Tamed a" in message or "Tamed an" in message) and not message.endswith("!"):
                message = message.rstrip(".") + "!"
            
            # Rule 14: Fix "Your Tribe Tamed" spacing
            if "YourTribe Tamed" in message:
                message = message.replace("YourTribe Tamed", "Your Tribe Tamed")
            
            # Rule 15: "was killed by" incomplete (missing the killer)
            if message.endswith("was killed by"):
                message = message + " an enemy!"
            
            # Rule 16: "was killed by a" incomplete
            if message.endswith("was killed by a"):
                message = message + "n enemy!"
            
            # Rule 17: "uploaded" or "downloaded" entries
            if ("uploaded" in message or "downloaded" in message) and not message.endswith("!"):
                message = message.rstrip(".") + "!"
            
            # Trim trailing empty/blank line images from all entries
            # This prevents saving images of blank lines after the actual content
            trimmed_images = images[:]
            while len(trimmed_images) > 1:
                # Check if the last image is mostly blank
                last_img = trimmed_images[-1]
                pixels = list(last_img.convert('L').getdata())
                if pixels:
                    mean = sum(pixels) / len(pixels)
                    variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
                    std_dev = variance ** 0.5
                    # If very low variance (blank/uniform), remove it
                    if std_dev < 5:
                        trimmed_images.pop()
                    else:
                        break
                else:
                    break
            
            completed_messages[message] = trimmed_images
        
        message_images = completed_messages
        
        # Get list of complete messages
        messages = list(message_images.keys())
        
        # Update tracking with complete messages
        self.update_message_tracking(messages, message_images)
        
        # Build entries from validated messages
        return self.build_entries_from_validated_messages()
    
    def update_message_tracking(self, messages, message_images):
        """Update tracking for complete messages (like old system)"""
        # Track complete messages instead of individual lines
        for message in messages:
            print(f"Tracking message: {message}")
            
            # Find if we've seen this message before
            found_similar = False
            for tracked_msg in list(self.line_counts.keys()):
                if self.is_similar_text(message, tracked_msg):
                    count = self.line_counts[tracked_msg]
                    self.line_counts[tracked_msg] = count + 1
                    if count + 1 >= self.log_seen_threshold:
                        # Message has been validated!
                        self.validated_lines[tracked_msg] = {
                            'text': tracked_msg,
                            'images': message_images.get(message, [])
                        }
                        print(f"Message validated ({count + 1}x): {tracked_msg}")
                    found_similar = True
                    break
            
            if not found_similar:
                # New message
                self.line_counts[message] = 1
        
        # Decrement counts for messages not seen
        for msg in list(self.line_counts.keys()):
            if msg not in messages:
                count = self.line_counts[msg]
                if count > 1:
                    self.line_counts[msg] = count - 1
                else:
                    del self.line_counts[msg]
                    # Also remove from validated if it exists
                    if msg in self.validated_lines:
                        del self.validated_lines[msg]
    
    def is_similar_text(self, text1, text2, threshold=5):
        """Check if two texts are similar enough"""
        if abs(len(text1) - len(text2)) > 10:
            return False
        
        # Use edit distance for short texts
        if len(text1) < 50:
            differences = sum(1 for a, b in zip(text1, text2) if a != b)
            return differences <= threshold
        
        # For longer texts, allow more differences
        return text1[:30] == text2[:30]  # Check if beginning matches
    
    def build_entries_from_validated_messages(self):
        """Build entries from validated complete messages"""
        if not self.validated_lines:
            return []
        
        entries = []
        
        for message, data in self.validated_lines.items():
            # Only add entries we haven't printed yet
            if message not in self.printed_entries:
                entries.append((message, data['images']))
        
        return entries
    
    
    def save_log_entry_with_images(self, entry_text, images):
        """Save a log entry with its associated images to SQLite databases"""
        if not entry_text.startswith("Day "):
            return
        
        # Parse day and time from entry
        day_match = re.match(r'Day (\d+), (\d{2}:\d{2}:\d{2}):', entry_text)
        if not day_match:
            print(f"Warning: Could not parse day/time from: {entry_text}")
            return
        
        day = int(day_match.group(1))
        time_str = day_match.group(2)
        
        # Generate unique ID for images
        image_id = str(uuid.uuid4())
        
        try:
            # Save combined image if exists
            if images:
                combined_image = self.combine_images(images)
                if combined_image:
                    # Convert image to bytes
                    img_buffer = BytesIO()
                    combined_image.save(img_buffer, format='PNG')
                    img_data = img_buffer.getvalue()
                    
                    # Save to images database
                    with sqlite3.connect(self.log_images_db_path) as conn:
                        conn.execute('''
                            INSERT INTO log_images (id, image_data, width, height)
                            VALUES (?, ?, ?, ?)
                        ''', (image_id, img_data, combined_image.width, combined_image.height))
            else:
                image_id = None
            
            # Save log entry to database
            with sqlite3.connect(self.log_db_path) as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO logs (day, time, entry_text, image_id)
                    VALUES (?, ?, ?, ?)
                ''', (day, time_str, entry_text, image_id))
                
                # Check if it was actually inserted
                if conn.total_changes > 0:
                    print(f"Saved to database: {entry_text}")
                else:
                    print(f"Entry already exists: {entry_text}")
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Error saving log entry: {e}")
    
    def combine_images(self, images):
        """Combine multiple line images into a single image"""
        if not images:
            return None
        
        try:
            # Calculate total height and max width
            total_height = sum(img.height for img in images)
            max_width = max(img.width for img in images)
            
            # Create combined image
            combined = Image.new('RGB', (max_width, total_height))
            
            # Paste each image
            y_offset = 0
            for img in images:
                combined.paste(img, (0, y_offset))
                y_offset += img.height
            
            return combined
        except Exception as e:
            print(f"Error combining images: {e}")
            return None
    
    def process_logs(self, screenshot):
        """Main method to process logs from a screenshot"""
        print("Processing logs from screenshot...")
        
        # Process screenshot - this updates line tracking
        entries_with_images = self.process_screenshot(screenshot)
        
        # Show message tracking status
        print(f"\n=== Message Tracking Status ===")
        for msg, count in self.line_counts.items():
            if count >= self.log_seen_threshold:
                print(f"Message VALIDATED ({count}/{self.log_seen_threshold}): {msg}")
            else:
                print(f"Message tracking ({count}/{self.log_seen_threshold}): {msg}")
        
        # Save validated entries
        new_count = 0
        newest_entry = None
        
        for entry_text, images in entries_with_images:
            if entry_text not in self.printed_entries:
                self.save_log_entry_with_images(entry_text, images)
                self.printed_entries[entry_text] = True
                new_count += 1
                print(f"\nSaved new entry: {entry_text}")
                
                # Track the newest entry we've seen
                if not newest_entry or self.is_newer_entry(entry_text, newest_entry):
                    newest_entry = entry_text
        
        if new_count > 0:
            print(f"\nTotal: Saved {new_count} new log entries")
            if newest_entry:
                print(f"Most recent entry: {newest_entry}")
        else:
            print("\nNo new complete entries to save")
            print(f"Validated entries: {len(self.validated_lines)}")
            print(f"Already processed entries: {len(self.printed_entries)}")
            if not self.validated_lines:
                print("(waiting for messages to be validated)")
            
            # Periodically cleanup to prevent memory issues
            self.cleanup_old_entries()

    def cleanup_old_entries(self):
        """Periodically clean up old entries to prevent memory bloat"""
        current_size = len(self.printed_entries)
        if current_size > 5000:  # Cleanup when we have too many entries
            # Keep only the most recent 2000 entries
            print(f"Cleaning up printed_entries cache ({current_size} entries)...")
            
            # Get recent entries from database
            recent_entries = set()
            with sqlite3.connect(self.log_db_path) as conn:
                cursor = conn.execute('''
                    SELECT entry_text FROM logs 
                    WHERE timestamp > datetime('now', '-6 hours')
                    ORDER BY id DESC
                    LIMIT 2000
                ''')
                for row in cursor:
                    recent_entries.add(row[0])
            
            # Keep only entries that are in recent_entries
            self.printed_entries = {k: v for k, v in self.printed_entries.items() if k in recent_entries}
            print(f"Cleaned up to {len(self.printed_entries)} entries")
        
        # Also cleanup line_counts dictionary
        if len(self.line_counts) > 1000:
            # Remove entries with count 0 or very old entries
            self.line_counts = {k: v for k, v in self.line_counts.items() if v > 0}
            print(f"Cleaned up line_counts to {len(self.line_counts)} entries")


if __name__ == "__main__":
    # Test the log processor
    from PIL import Image
    processor = LogProcessor({})
    
    # Test with a screenshot if available
    test_image = "screenshots/test_logs.png"
    if os.path.exists(test_image):
        img = Image.open(test_image)
        processor.process_logs(img)
    else:
        print("No test image found")