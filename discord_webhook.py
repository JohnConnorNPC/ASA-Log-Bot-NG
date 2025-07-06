import os
import json
import sqlite3
import requests
import subprocess
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO


class DiscordWebhook:
    def __init__(self, config):
        self.config = config
        self.log_webhook = config.get('log_webhook', '')  # For log entries
        self.members_webhook = config.get('members_webhook', '')  # For member updates
        self.server_ip = config.get('server_ip', '')
        self.server_port = config.get('server_port', 7777)
        self.log_db_path = config.get('log_db', './log.db')
        self.log_images_db_path = config.get('log_images_db', './log_images.db')
        self.member_db_path = config.get('member_db', './member.db')
        self.discord_sent_db_path = './discord_sent.db'  # Track what's been sent
        self.last_sent_log_id = self.load_last_sent_id()
        self.discord_post_interval = config.get('discord_post_interval', 60)  # Default 60 seconds
        self.last_discord_post_time = self.load_last_post_time()
        
        # Initialize Discord sent tracking database
        self.init_discord_sent_db()
        
        # Store last screenshot for day/time overlay
        self.last_screenshot = None
    
    def init_discord_sent_db(self):
        """Initialize database to track sent Discord messages"""
        try:
            with sqlite3.connect(self.discord_sent_db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS discord_sent (
                        image_guid TEXT PRIMARY KEY,
                        log_id INTEGER,
                        entry_text TEXT,
                        sent_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sent_timestamp ON discord_sent(sent_timestamp)')
                print("Discord: Initialized sent tracking database")
        except Exception as e:
            print(f"Discord: Error initializing sent database: {e}")
    
    def is_log_sent(self, image_guid):
        """Check if a log with this image GUID has been sent"""
        if not image_guid:
            return False
        try:
            with sqlite3.connect(self.discord_sent_db_path) as conn:
                cursor = conn.execute('SELECT 1 FROM discord_sent WHERE image_guid = ?', (image_guid,))
                return cursor.fetchone() is not None
        except:
            return False
    
    def mark_log_sent(self, log):
        """Mark a log as sent to Discord"""
        if not log.get('image_id'):
            return
        try:
            with sqlite3.connect(self.discord_sent_db_path) as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO discord_sent (image_guid, log_id, entry_text)
                    VALUES (?, ?, ?)
                ''', (log['image_id'], log['id'], log['text']))
                conn.commit()
                print(f"Discord: Marked as sent - ID: {log['id']}, GUID: {log['image_id']}")
        except Exception as e:
            print(f"Discord: Error marking log as sent: {e}")
        
    def load_last_sent_id(self):
        """Load the last sent log ID from a file"""
        try:
            if os.path.exists('.last_discord_log_id'):
                with open('.last_discord_log_id', 'r') as f:
                    value = int(f.read().strip())
                    print(f"Discord: Loaded last sent log ID: {value}")
                    return value
            else:
                print("Discord: No last sent log ID file found, starting from 0")
        except Exception as e:
            print(f"Discord: Error loading last sent log ID: {e}")
        return 0
    
    def save_last_sent_id(self, log_id):
        """Save the last sent log ID"""
        try:
            with open('.last_discord_log_id', 'w') as f:
                f.write(str(log_id))
            print(f"Discord: Saved last sent log ID: {log_id}")
        except Exception as e:
            print(f"Discord: ERROR saving last sent log ID: {e}")
    
    def load_last_post_time(self):
        """Load the last Discord post time from a file"""
        try:
            if os.path.exists('.last_discord_post_time'):
                with open('.last_discord_post_time', 'r') as f:
                    return float(f.read().strip())
        except:
            pass
        return 0
    
    def save_last_post_time(self):
        """Save the current time as last Discord post time"""
        with open('.last_discord_post_time', 'w') as f:
            f.write(str(time.time()))
    
    def get_server_info(self):
        """Get server info using gamedig command line tool"""
        try:
            # Use gamedig command line tool like the old system
            cmd = f'gamedig --type "asa" {self.server_ip}:{self.server_port}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Get total players from the raw data
                total_players = data.get('raw', {}).get('totalPlayers', 0)
                print(f"Gamedig: Server has {total_players} total players")
                return total_players
            else:
                print(f"Gamedig error: {result.stderr}")
        except Exception as e:
            print(f"Error running gamedig: {e}")
        
        return 0
    
    def get_online_members_count(self):
        """Get count of online members from database"""
        try:
            with sqlite3.connect(self.member_db_path) as conn:
                # Get the most recent snapshot
                cursor = conn.execute('''
                    SELECT member_count 
                    FROM member_snapshots 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    # This now returns the OCR count from the "X/Y" display
                    print(f"Discord: Got member count from DB: {row[0]}")
                    return row[0]
        except Exception as e:
            print(f"Discord: Error getting member count: {e}")
        return 0
    
    def get_online_members_list(self):
        """Get list of online members from database"""
        try:
            with sqlite3.connect(self.member_db_path) as conn:
                # Get the most recent snapshot
                cursor = conn.execute('''
                    SELECT members 
                    FROM member_snapshots 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row and row[0]:
                    # Split comma-separated list
                    return [m.strip() for m in row[0].split(',') if m.strip()]
        except:
            pass
        return []
    
    def get_all_members_with_status(self):
        """Get all members with their online/offline status"""
        try:
            with sqlite3.connect(self.member_db_path) as conn:
                cursor = conn.execute('''
                    SELECT name, is_online 
                    FROM members 
                    WHERE last_seen > datetime("now", "-1 day")
                    ORDER BY is_online DESC, name ASC
                ''')
                return [(row[0], row[1]) for row in cursor]
        except:
            pass
        return []
    
    def get_latest_game_info(self):
        """Get the latest game day and time from database"""
        try:
            with sqlite3.connect(self.log_db_path) as conn:
                cursor = conn.execute('''
                    SELECT day, time, id, entry_text 
                    FROM logs 
                    ORDER BY day DESC, time DESC 
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    print(f"Discord: Latest game info from DB - Day {row[0]}, {row[1]} (ID: {row[2]})")
                    return row[0], row[1]
                else:
                    print("Discord: No logs found in database")
        except Exception as e:
            print(f"Discord: Error getting latest game info: {e}")
        return None, None
    
    def get_new_logs(self):
        """Get new log entries since last sent"""
        new_logs = []
        try:
            with sqlite3.connect(self.log_db_path) as conn:
                # First, let's see what the latest ID in the database is
                cursor = conn.execute('SELECT MAX(id) FROM logs')
                max_db_id = cursor.fetchone()[0] or 0
                
                print(f"Discord: Checking for new logs. Last sent ID: {self.last_sent_log_id}, Max DB ID: {max_db_id}")
                
                cursor = conn.execute('''
                    SELECT id, day, time, entry_text, image_id 
                    FROM logs 
                    WHERE id > ? 
                    ORDER BY id ASC
                    LIMIT 10
                ''', (self.last_sent_log_id,))
                
                for row in cursor:
                    new_logs.append({
                        'id': row[0],
                        'day': row[1],
                        'time': row[2],
                        'text': row[3],
                        'image_id': row[4]
                    })
                
                if new_logs:
                    print(f"Discord: Found {len(new_logs)} new logs (IDs {new_logs[0]['id']} to {new_logs[-1]['id']})")
        except Exception as e:
            print(f"Error getting new logs: {e}")
        
        return new_logs
    
    def get_log_image(self, image_id):
        """Get image data from database"""
        if not image_id:
            return None
            
        try:
            with sqlite3.connect(self.log_images_db_path) as conn:
                cursor = conn.execute('''
                    SELECT image_data 
                    FROM log_images 
                    WHERE id = ?
                ''', (image_id,))
                row = cursor.fetchone()
                if row:
                    return Image.open(BytesIO(row[0]))
        except:
            pass
        return None
    
    def create_status_image(self, logs, total_players, online_members, no_changes=False, screenshot=None, last_db_time=None, show_offline=True):
        """Create a status image using original images from database"""
        # Get log images from database if we have logs
        log_images = []
        max_width = 0
        total_log_height = 0
        
        if logs and not no_changes:
            for log in logs:
                if log.get('image_id'):
                    img = self.get_log_image(log['image_id'])
                    if img:
                        log_images.append(img)
                        max_width = max(max_width, img.width)
                        total_log_height += img.height
        
        # Font settings for header
        try:
            font_large = ImageFont.truetype("arial.ttf", 20)
            font_small = ImageFont.truetype("arial.ttf", 16)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Calculate dimensions
        padding = 10
        header_height = 80  # Increased to accommodate day/time images
        no_changes_height = 40 if no_changes else 0
        
        # If we have log images, use their width, otherwise use default
        if log_images:
            width = log_images[0].width  # All DB images have same width
        else:
            width = 380  # Default width from log_crop_coords
        
        total_height = header_height + total_log_height + no_changes_height + (padding * 3)
        
        # Create image with dark background
        img = Image.new('RGB', (width, total_height), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        
        # Draw header section
        y = padding
        
        # If we have a screenshot, copy the day/time regions directly
        if screenshot:
            try:
                # Day region: x=25, y=36 (moved down 4px), width=152-25=127, height=65-36=29
                day_region = screenshot.crop((25, 36, 152, 65))
                # Time region: x=31, y=89, width=99-31=68, height=112-89=23
                time_region = screenshot.crop((31, 89, 99, 112))
                
                # Paste them into our image - top left corner
                img.paste(day_region, (padding, y))
                # Time directly under day (29 pixels for day height + small gap)
                img.paste(time_region, (padding, y + 29 + 3))
            except Exception as e:
                print(f"Discord: Error copying day/time from screenshot: {e}")
                # Fall back to text
                day, time = self.get_latest_game_info()
                if day and time:
                    draw.text((padding, y), f"Day {day}", fill=(255, 255, 255), font=font_large)
                    draw.text((padding, y + 25), time, fill=(200, 200, 200), font=font_small)
        else:
            # No screenshot, use database values
            day, time = self.get_latest_game_info()
            if day and time:
                draw.text((padding, y), f"Day {day}", fill=(255, 255, 255), font=font_large)
                draw.text((padding, y + 25), time, fill=(200, 200, 200), font=font_small)
            else:
                draw.text((padding, y), "Day ???", fill=(255, 255, 255), font=font_large)
                draw.text((padding, y + 25), "??:??:??", fill=(200, 200, 200), font=font_small)
        
        # Calculate counts
        # Get actual member list count for more accurate enemy calculation
        actual_member_count = len(self.get_online_members_list())
        # Use the higher of OCR count or actual detected members
        effective_members = max(online_members, actual_member_count)
        enemy_count = max(0, total_players - effective_members)
        
        # Draw Members in center with number below
        members_label = "Members"
        # Show actual detected count if higher than OCR
        if actual_member_count > online_members:
            members_num = f"{actual_member_count}"
        else:
            members_num = str(online_members)
        
        # Get text widths for centering
        label_bbox = draw.textbbox((0, 0), members_label, font=font_small)
        label_width = label_bbox[2] - label_bbox[0]
        num_bbox = draw.textbbox((0, 0), members_num, font=font_large)
        num_width = num_bbox[2] - num_bbox[0]
        
        # Center position - Members stays at top
        center_x = width // 2
        draw.text((center_x - label_width // 2, y), members_label, fill=(100, 200, 255), font=font_small)
        draw.text((center_x - num_width // 2, y + 20), members_num, fill=(100, 200, 255), font=font_large)
        
        # Right align Players and Enemies at top
        players_text = f"Players: {total_players}"
        enemies_text = f"Enemies: {enemy_count}"
        
        # Get text widths for right alignment
        players_bbox = draw.textbbox((0, 0), players_text, font=font_small)
        players_width = players_bbox[2] - players_bbox[0]
        enemies_bbox = draw.textbbox((0, 0), enemies_text, font=font_small)
        enemies_width = enemies_bbox[2] - enemies_bbox[0]
        
        # Right align with padding
        right_edge = width - padding
        draw.text((right_edge - players_width, y), players_text, fill=(0, 255, 0), font=font_small)
        
        # Enemies in red (bold-ish by drawing twice)
        draw.text((right_edge - enemies_width, y + 20), enemies_text, fill=(255, 0, 0), font=font_small)
        draw.text((right_edge - enemies_width + 1, y + 20), enemies_text, fill=(255, 0, 0), font=font_small)
        
        # Draw separator line
        y = header_height
        draw.line([(padding, y), (width - padding, y)], fill=(100, 100, 100), width=1)
        y += padding
        
        # Paste original log images or show "no changes" message
        if no_changes:
            # Draw "NO CHANGES" message with last database time
            if last_db_time:
                no_changes_text = f"NO CHANGES - Last Entry: {last_db_time}"
            else:
                no_changes_text = "NO CHANGES - Status Update Only"
            text_bbox = draw.textbbox((0, 0), no_changes_text, font=font_small)
            text_width = text_bbox[2] - text_bbox[0]
            x_offset = (width - text_width) // 2
            draw.text((x_offset, y + 10), no_changes_text, fill=(150, 150, 150), font=font_small)
        else:
            # Paste original log images
            for log_img in log_images:
                # Paste directly since width matches
                img.paste(log_img, (0, y))
                y += log_img.height
        
        return img
    
    def send_to_discord(self, logs):
        """Send logs to Discord webhook"""
        if not self.log_webhook or not logs:
            return
        
        try:
            # Sort logs by day and time to ensure chronological order
            def parse_log_time(log):
                """Extract day and time for sorting"""
                try:
                    day = log.get('day', 0)
                    time_str = log.get('time', '00:00:00')
                    time_parts = time_str.split(':')
                    total_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
                    return (day, total_seconds)
                except:
                    return (0, 0)
            
            # Sort logs by day and time (newest first for Discord display)
            sorted_logs = sorted(logs, key=parse_log_time, reverse=True)
            
            # Get server and member info
            total_players = self.get_server_info()
            online_members = self.get_online_members_count()
            
            # Create status image
            img = self.create_status_image(sorted_logs, total_players, online_members, screenshot=self.last_screenshot)
            
            # Convert image to bytes
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Prepare the message
            message_lines = []
            max_id = self.last_sent_log_id
            for log in sorted_logs:
                log_text = log['text']
                emoji = self.get_log_emoji(log_text)
                message_lines.append(f"{emoji} {log_text}")
                # Track the highest ID we're sending (still use original logs for ID tracking)
                if log['id'] > max_id:
                    max_id = log['id']
            
            # Send to Discord
            files = {
                'file': ('status.png', img_buffer, 'image/png')
            }
            
            payload = {
                'content': '\n'.join(message_lines)[-2000:],  # Discord limit
                'username': 'ASA-Log-Bot-NG'
            }
            
            response = requests.post(
                self.log_webhook,
                data=payload,
                files=files
            )
            
            if response.status_code in [200, 204]:  # Both are success codes
                print(f"Successfully sent {len(logs)} logs to Discord (status: {response.status_code})")
                # Mark each log as sent using its image GUID
                for log in logs:
                    self.mark_log_sent(log)
                # Update last sent ID to the highest ID we sent
                if max_id > self.last_sent_log_id:
                    self.last_sent_log_id = max_id
                    self.save_last_sent_id(self.last_sent_log_id)
                    print(f"Updated last sent log ID to: {self.last_sent_log_id}")
            else:
                print(f"Failed to send to Discord: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending to Discord: {e}")
    
    def check_and_send_new_logs(self):
        """Check for new logs and send them only if interval has passed"""
        # Check if enough time has passed since last post
        current_time = time.time()
        time_since_last_post = current_time - self.last_discord_post_time
        
        if time_since_last_post < self.discord_post_interval:
            # Not time yet
            remaining = self.discord_post_interval - time_since_last_post
            print(f"Discord: Not time to post yet. {remaining:.1f}s remaining (interval: {self.discord_post_interval}s)")
            return
        
        # Update the post time immediately to prevent multiple calls
        self.last_discord_post_time = current_time
        self.save_last_post_time()
        
        # Get new logs
        new_logs = self.get_new_logs()
        if new_logs:
            print(f"Discord: {len(new_logs)} new logs found, posting after {int(time_since_last_post)}s interval")
            
            # Filter out any logs that have already been sent based on image GUID
            unsent_logs = []
            for log in new_logs:
                if log.get('image_id'):
                    # Has image ID, check if already sent
                    if not self.is_log_sent(log['image_id']):
                        unsent_logs.append(log)
                    else:
                        print(f"Discord: Skipping already sent log - ID: {log['id']}, GUID: {log['image_id']}")
                else:
                    # No image ID, include it (can't check if sent without GUID)
                    print(f"Discord: Including log without image ID - ID: {log['id']}")
                    unsent_logs.append(log)
            
            if unsent_logs:
                print(f"Discord: Sending {len(unsent_logs)} truly new logs after GUID filtering")
                self.send_to_discord(unsent_logs)
            else:
                print(f"Discord: All logs already sent (GUID check), sending status update instead")
                self.send_status_update(screenshot=self.last_screenshot)
        else:
            # No new logs, but send status update
            print(f"Discord: No new logs, sending status update after {int(time_since_last_post)}s interval")
            self.send_status_update(screenshot=getattr(self, 'last_screenshot', None))
        
        # Also send member update to members webhook
        self.send_member_update()
    
    def send_status_update(self, screenshot=None):
        """Send a status update when there are no new logs"""
        if not self.log_webhook:
            return
        
        try:
            # Get server and member info
            total_players = self.get_server_info()
            online_members = self.get_online_members_count()
            
            # Get last database entry time
            day, time = self.get_latest_game_info()
            last_db_time = f"Day {day}, {time}" if day and time else None
            
            # Create status image with no changes flag
            img = self.create_status_image([], total_players, online_members, no_changes=True, screenshot=screenshot, last_db_time=last_db_time)
            
            # Convert image to bytes
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Send to Discord
            files = {
                'file': ('status.png', img_buffer, 'image/png')
            }
            
            # Get current game info for message
            day, time = self.get_latest_game_info()
            if day and time:
                status_text = f"📊 Status Update - Day {day}, {time}\n"
            else:
                status_text = "📊 Status Update\n"
            
            # Get actual member count for accurate enemy calculation
            actual_member_count = len(self.get_online_members_list())
            effective_members = max(online_members, actual_member_count)
            enemy_count = max(0, total_players - effective_members)
            
            status_text += f"Players: {total_players} | Members: {online_members}"
            if actual_member_count > online_members:
                status_text += f" (detected {actual_member_count})"
            status_text += f" | Enemies: {enemy_count}"
            
            payload = {
                'content': status_text,
                'username': 'ASA-Log-Bot-NG'
            }
            
            response = requests.post(
                self.log_webhook,
                data=payload,
                files=files
            )
            
            if response.status_code in [200, 204]:
                print(f"Status update sent to Discord (status: {response.status_code})")
            else:
                print(f"Failed to send status update: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending status update: {e}")
    
    def send_member_update(self):
        """Send member status update to the members webhook"""
        if not self.members_webhook:
            return
        
        try:
            # Get all members with status
            all_members = self.get_all_members_with_status()
            if not all_members:
                return
            
            # Separate online and offline members
            online_members = [name for name, is_online in all_members if is_online]
            offline_members = [name for name, is_online in all_members if not is_online]
            
            # Build message
            message = "**Member Status Update**\n\n"
            
            if online_members:
                message += f"🟢 **Online ({len(online_members)}):**\n"
                message += ", ".join(online_members[:20])  # Limit to first 20
                if len(online_members) > 20:
                    message += f" and {len(online_members) - 20} more..."
                message += "\n\n"
            
            if offline_members:
                message += f"🔴 **Offline ({len(offline_members)}):**\n"
                message += ", ".join(offline_members[:20])  # Limit to first 20
                if len(offline_members) > 20:
                    message += f" and {len(offline_members) - 20} more..."
            
            # Send to members webhook
            payload = {
                'content': message[:2000],  # Discord limit
                'username': 'ASA-Log-Bot-NG Members'
            }
            
            response = requests.post(self.members_webhook, json=payload)
            
            if response.status_code in [200, 204]:
                print(f"Member update sent to Discord (online: {len(online_members)}, offline: {len(offline_members)})")
            else:
                print(f"Failed to send member update: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending member update: {e}")
    
    def get_log_emoji(self, log_text):
        """Get appropriate emoji based on log content"""
        log_lower = log_text.lower()
        
        # Death/Kill events (check these first as they're most specific)
        if 'starved to death' in log_lower:
            return '🍖'
        elif 'death essence expired' in log_lower:
            return '👻'
        elif 'killed' in log_lower:
            return '💀'
        
        # Tribe management
        elif 'added to the tribe' in log_lower:
            return '✅'
        elif 'removed from the tribe' in log_lower:
            return '❌'
        elif 'promoted' in log_lower:
            return '⬆️'
        elif 'demoted' in log_lower:
            return '⬇️'
        
        # Taming/Breeding
        elif 'tamed' in log_lower:
            return '🦖'
        elif 'claimed baby' in log_lower or 'hatched' in log_lower:
            return '🥚'
        
        # Building/Structure
        elif 'demolished' in log_lower:
            return '🔨'
        elif 'c4 charge' in log_lower:
            return '💣'
        elif 'destroyed' in log_lower:
            return '💥'
        elif 'auto-decay' in log_lower or 'decayed' in log_lower:
            return '⏰'
        
        # Creature management
        elif 'froze' in log_lower:
            return '❄️'
        elif 'unclaimed' in log_lower:
            return '🔓'
        
        # Upload/Download
        elif 'uploaded' in log_lower:
            return '⬆️'
        elif 'downloaded' in log_lower:
            return '⬇️'
        
        # Combat
        elif 'enemy' in log_lower:
            return '⚔️'
        
        # Special creatures
        elif 'wyvern' in log_lower:
            return '🐉'
        elif 'griffin' in log_lower or 'griffed' in log_lower:
            return '🦅'
        elif 'phoenix' in log_lower:
            return '🔥'
        
        # Default
        else:
            return '📝'
    
    def send_member_update(self):
        """Send online members list to members webhook"""
        if not self.members_webhook:
            return
        
        try:
            # Get online members list (detected names)
            members = self.get_online_members_list()
            detected_count = len(members)
            
            # Get actual member count from OCR
            actual_member_count = self.get_online_members_count()
            
            # Get server info
            total_players = self.get_server_info()
            # Use actual count for enemy calculation
            enemy_count = max(0, total_players - actual_member_count)
            
            # Get current game info
            day, time = self.get_latest_game_info()
            
            # Create embed
            embed = {
                "title": f"Online Tribe Members - {actual_member_count} Total",
                "color": 0x00FF00 if enemy_count == 0 else 0xFFA500 if enemy_count < 5 else 0xFF0000,
                "fields": [],
                "footer": {
                    "text": f"Day {day}, {time}" if day and time else "Unknown time"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add member list
            if members:
                # Split into chunks of 10 for better formatting
                for i in range(0, len(members), 10):
                    chunk = members[i:i+10]
                    embed["fields"].append({
                        "name": f"Members {i+1}-{min(i+10, len(members))}",
                        "value": "\n".join(f"• {member}" for member in chunk),
                        "inline": True
                    })
            else:
                embed["description"] = "No members online"
            
            # Add server status field
            status_text = f"Total Players: {total_players}\nEnemies: {enemy_count}"
            if detected_count != actual_member_count:
                status_text += f"\n\n*Detected {detected_count} names (OCR limitations)*"
            
            embed["fields"].append({
                "name": "Server Status",
                "value": status_text,
                "inline": False
            })
            
            payload = {
                "embeds": [embed],
                "username": "Ark Member Monitor"
            }
            
            response = requests.post(
                self.members_webhook,
                json=payload
            )
            
            if response.status_code in [200, 204]:
                print(f"Member update sent: {actual_member_count} members online (status: {response.status_code})")
            else:
                print(f"Failed to send member update: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending member update: {e}")