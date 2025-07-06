import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import time
import os
import sys
import ctypes
from datetime import datetime, timedelta
from collections import deque

# Import existing modules
from screenshot_capture import ScreenshotCapture
from pixel_detector import PixelDetector
from config_loader import ConfigLoader
from state_detector import StateDetector
from click_automation import ClickAutomation
from log_processor import LogProcessor
from member_processor import MemberProcessor
from discord_webhook import DiscordWebhook


class ASALogBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ASA-Log-Bot-NG by jc0839")
        self.root.geometry("1180x800")
        
        # Dark mode colors
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.select_bg = "#3e3e3e"
        self.button_bg = "#2d2d2d"
        self.entry_bg = "#2d2d2d"
        self.frame_bg = "#252525"
        
        # Configure root window for dark mode
        self.root.configure(bg=self.bg_color)
        
        # Configure ttk style for dark mode
        self.style = ttk.Style()
        self.configure_dark_theme()
        
        # Initialize components
        self.config = ConfigLoader("config.json")
        self.screenshot = ScreenshotCapture(self.config.config.get("window_title", "ArkAscended"))
        self.pixel_detector = PixelDetector(
            tolerance=self.config.config.get("tolerance", 10),
            variance_percent=self.config.config.get("variance_percent")
        )
        self.state_detector = StateDetector(self.config, self.pixel_detector)
        self.automation = ClickAutomation(
            window_title=self.config.config.get("window_title", "ArkAscended"),
            click_delay=self.config.config.get("click_delay", 0.5)
        )
        self.log_processor = LogProcessor(self.config.config)
        self.member_processor = MemberProcessor(self.config.config)
        
        # Initialize Discord webhook if enabled
        self.discord = None
        if self.config.config.get('discord_enabled', False):
            self.discord = DiscordWebhook(self.config.config)
        
        # Ensure screenshot directory exists
        screenshot_dir = self.config.config.get("screenshot_dir", "screenshots/")
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Thread control
        self.running = False
        self.thread = None
        self.update_queue = queue.Queue()
        
        # Data storage
        self.logs_data = deque(maxlen=1000)  # Increased from 100
        self.members_data = []
        self.activity_data = deque(maxlen=100)  # Increased from 20
        self.stats = {
            'state': 'Idle',
            'window': 'Not Found',
            'members_online': 0,
            'players_total': 0,
            'enemies': 0,
            'logs_processed': 0,
            'logs_new': 0,
            'discord_timer': 0,
            'start_time': datetime.now()
        }
        
        # Clean up old screenshots on startup
        self.cleanup_old_screenshots()
        
        # Tracking variables from original
        self.last_screenshot_path = None
        self.last_test_screenshot_path = None
        
        # Create GUI
        self.create_widgets()
        
        # Start update loop
        self.update_gui()
        
        # Auto-start monitoring
        self.root.after(1000, self.start_monitoring)
        
        # Position window on right edge and minimize console
        self.root.after(100, self.position_window_and_minimize_console)
        
    def configure_dark_theme(self):
        """Configure ttk styles for dark theme"""
        # Configure styles
        self.style.theme_use('clam')
        
        # Frame styles
        self.style.configure('TFrame', background=self.frame_bg, borderwidth=0)
        self.style.configure('TLabelFrame', background=self.frame_bg, foreground=self.fg_color, 
                           bordercolor=self.select_bg, lightcolor=self.frame_bg, darkcolor=self.frame_bg,
                           relief='solid', borderwidth=1)
        self.style.configure('TLabelFrame.Label', background=self.frame_bg, foreground=self.fg_color)
        
        # Label styles
        self.style.configure('TLabel', background=self.frame_bg, foreground=self.fg_color)
        
        # Button styles
        self.style.configure('TButton', background=self.button_bg, foreground=self.fg_color,
                           bordercolor=self.select_bg, lightcolor=self.button_bg, darkcolor=self.button_bg)
        self.style.map('TButton', background=[('active', self.select_bg), ('pressed', '#4e4e4e')])
        
        # Entry styles
        self.style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.fg_color,
                           bordercolor=self.select_bg, insertcolor=self.fg_color)
        
        # Combobox styles
        self.style.configure('TCombobox', fieldbackground=self.entry_bg, foreground=self.fg_color,
                           background=self.button_bg, bordercolor=self.select_bg, 
                           arrowcolor=self.fg_color, insertcolor=self.fg_color)
        self.style.map('TCombobox', fieldbackground=[('readonly', self.entry_bg)])
        
        # Notebook styles
        self.style.configure('TNotebook', background=self.frame_bg, bordercolor=self.select_bg)
        self.style.configure('TNotebook.Tab', background=self.button_bg, foreground=self.fg_color,
                           bordercolor=self.select_bg, padding=[12, 8])
        self.style.map('TNotebook.Tab', background=[('selected', self.select_bg)])
        
        # Treeview styles
        self.style.configure('Treeview', background=self.entry_bg, foreground=self.fg_color,
                           fieldbackground=self.entry_bg, bordercolor=self.select_bg)
        self.style.configure('Treeview.Heading', background=self.button_bg, foreground=self.fg_color,
                           bordercolor=self.select_bg)
        self.style.map('Treeview', background=[('selected', self.select_bg)])
        
        # Scrollbar styles
        self.style.configure('Vertical.TScrollbar', background=self.button_bg, bordercolor=self.button_bg,
                           arrowcolor=self.fg_color, troughcolor=self.entry_bg)
        self.style.configure('Horizontal.TScrollbar', background=self.button_bg, bordercolor=self.button_bg,
                           arrowcolor=self.fg_color, troughcolor=self.entry_bg)
        
    def open_github(self):
        """Open GitHub repository in browser"""
        import webbrowser
        webbrowser.open("https://github.com/JohnConnorNPC/ASA-Log-Bot-NG")
        self.add_activity("Opened GitHub repository", "info")
    
    def open_discord(self):
        """Open Discord support server in browser"""
        import webbrowser
        webbrowser.open("https://discord.com/invite/QjtT94TsBE")
        self.add_activity("Opened Discord support", "info")
    
    def open_website(self):
        """Open ARK tools website in browser"""
        import webbrowser
        webbrowser.open("https://jc0839.fly.dev/")
        self.add_activity("Opened ARK Tools website", "info")
    
    def cleanup_old_screenshots(self):
        """Clean up old detection and test screenshots"""
        screenshot_dir = self.config.config.get("screenshot_dir", "screenshots/")
        try:
            if os.path.exists(screenshot_dir):
                for file in os.listdir(screenshot_dir):
                    if file.startswith(('detection_', 'test_')) and file.endswith('.png'):
                        file_path = os.path.join(screenshot_dir, file)
                        try:
                            os.remove(file_path)
                        except:
                            pass
        except:
            pass
    
    def position_window_and_minimize_console(self):
        """Position window on right edge of screen and minimize console"""
        # Update window to ensure geometry is correct
        self.root.update_idletasks()
        
        # Get window dimensions
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate position (right edge, vertically centered)
        x = screen_width - window_width
        y = (screen_height - window_height) // 2
        
        # Set window position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Minimize console window on Windows
        if sys.platform == "win32":
            try:
                # Get console window handle
                kernel32 = ctypes.WinDLL('kernel32')
                user32 = ctypes.WinDLL('user32')
                
                # Get console window
                console_window = kernel32.GetConsoleWindow()
                
                if console_window:
                    # Minimize console window
                    user32.ShowWindow(console_window, 6)  # SW_MINIMIZE = 6
            except:
                pass
    
    def create_widgets(self):
        # Create main container with dark background
        main_container = ttk.Frame(self.root, padding="10", style='Dark.TFrame')
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure the Dark.TFrame style
        self.style.configure('Dark.TFrame', background=self.bg_color)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=2)  # Left panel gets 2/5
        main_container.columnconfigure(1, weight=3)  # Right panel gets 3/5
        main_container.rowconfigure(1, weight=1)
        
        # Left panel - Status and Controls
        left_panel = ttk.Frame(main_container, style='Dark.TFrame')
        left_panel.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        # Status frame - using regular Frame with custom border
        status_container = tk.Frame(left_panel, bg=self.frame_bg, highlightbackground=self.select_bg, 
                                   highlightthickness=1, bd=0)
        status_container.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        status_label = tk.Label(status_container, text="Status", bg=self.frame_bg, fg=self.fg_color,
                               font=('TkDefaultFont', 9, 'bold'))
        status_label.pack(anchor='nw', padx=10, pady=(5, 0))
        
        status_frame = tk.Frame(status_container, bg=self.frame_bg)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        self.status_labels = {}
        status_items = [
            ('State', 'state'),
            ('Window', 'window'),
            ('Members Online', 'members_online'),
            ('Total Players', 'players_total'),
            ('Enemies', 'enemies'),
            ('Logs Processed', 'logs_processed'),
            ('New Logs', 'logs_new'),
            ('Discord Timer', 'discord_timer'),
            ('Uptime', 'uptime')
        ]
        
        for i, (label, key) in enumerate(status_items):
            tk.Label(status_frame, text=f"{label}:", bg=self.frame_bg, fg=self.fg_color).grid(row=i, column=0, sticky=tk.W, pady=2)
            self.status_labels[key] = tk.Label(status_frame, text="--", font=('Consolas', 10), width=25,
                                             bg=self.frame_bg, fg=self.fg_color)
            self.status_labels[key].grid(row=i, column=1, sticky=tk.W, padx=10, pady=2)
        
        # Control buttons - using regular Frame with custom border
        control_container = tk.Frame(left_panel, bg=self.frame_bg, highlightbackground=self.select_bg, 
                                    highlightthickness=1, bd=0)
        control_container.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
        
        control_label = tk.Label(control_container, text="Controls", bg=self.frame_bg, fg=self.fg_color,
                                font=('TkDefaultFont', 9, 'bold'))
        control_label.pack(anchor='nw', padx=10, pady=(5, 0))
        
        control_frame = tk.Frame(control_container, bg=self.frame_bg)
        control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        self.start_button = ttk.Button(control_frame, text="Start", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(control_frame, text="Clear Logs", command=self.clear_logs)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Members frame - using regular Frame with custom border
        members_container = tk.Frame(left_panel, bg=self.frame_bg, highlightbackground=self.select_bg, 
                                    highlightthickness=1, bd=0)
        members_container.pack(fill=tk.BOTH, expand=True)
        
        members_label = tk.Label(members_container, text="Online Members", bg=self.frame_bg, fg=self.fg_color,
                                font=('TkDefaultFont', 9, 'bold'))
        members_label.pack(anchor='nw', padx=10, pady=(5, 0))
        
        members_frame = tk.Frame(members_container, bg=self.frame_bg)
        members_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Members treeview
        self.members_tree = ttk.Treeview(members_frame, columns=('Name', 'Times Seen'), show='tree headings', height=10)
        self.members_tree.heading('#0', text='#')
        self.members_tree.heading('Name', text='Name')
        self.members_tree.heading('Times Seen', text='Seen')
        self.members_tree.column('#0', width=40)
        self.members_tree.column('Name', width=150)
        self.members_tree.column('Times Seen', width=60)
        self.members_tree.pack(fill=tk.BOTH, expand=True)
        
        # Right panel - Logs and Activity
        right_panel = ttk.Frame(main_container, style='Dark.TFrame')
        right_panel.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(right_panel, style='Dark.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Configure notebook style
        self.style.configure('Dark.TNotebook', background=self.bg_color, borderwidth=0)
        self.style.configure('Dark.TNotebook.Tab', background=self.button_bg, foreground=self.fg_color,
                           bordercolor=self.select_bg, padding=[12, 8])
        self.style.map('Dark.TNotebook.Tab', background=[('selected', self.select_bg)])
        
        # Logs tab
        logs_tab = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(logs_tab, text="Logs")
        
        # Search/Filter frame
        search_frame = ttk.Frame(logs_tab, style='Dark.TFrame')
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.apply_filter())
        
        ttk.Label(search_frame, text="Filter:").pack(side=tk.LEFT, padx=10)
        self.filter_var = tk.StringVar(value="All")
        self.filter_combo = ttk.Combobox(search_frame, textvariable=self.filter_var, 
                                        values=["All", "Kills", "Tames", "Harvests", "Enemy", "Tribe"],
                                        state="readonly", width=15)
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filter())
        
        ttk.Button(search_frame, text="Clear Filter", command=self.clear_filter).pack(side=tk.LEFT, padx=10)
        
        # Logs display
        self.logs_display = scrolledtext.ScrolledText(logs_tab, wrap=tk.WORD, font=('Consolas', 9),
                                                     bg=self.entry_bg, fg=self.fg_color,
                                                     insertbackground=self.fg_color,
                                                     selectbackground=self.select_bg,
                                                     selectforeground=self.fg_color)
        self.logs_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for log colors (brighter for dark mode)
        self.logs_display.tag_configure('kill', foreground='#ff6b6b')
        self.logs_display.tag_configure('tame', foreground='#51cf66')
        self.logs_display.tag_configure('harvest', foreground='#ff9f43')
        self.logs_display.tag_configure('time', foreground='#868e96')
        self.logs_display.tag_configure('discord', foreground='#339af0')
        
        # Activity tab
        activity_tab = ttk.Frame(notebook, style='Dark.TFrame')
        notebook.add(activity_tab, text="Activity")
        
        # Activity display
        self.activity_display = scrolledtext.ScrolledText(activity_tab, wrap=tk.WORD, font=('Consolas', 9),
                                                         bg=self.entry_bg, fg=self.fg_color,
                                                         insertbackground=self.fg_color,
                                                         selectbackground=self.select_bg,
                                                         selectforeground=self.fg_color)
        self.activity_display.pack(fill=tk.BOTH, expand=True)
        
        # Bottom status bar with branding
        status_bar_frame = tk.Frame(self.root, bg=self.button_bg, height=25)
        status_bar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        status_bar_frame.grid_propagate(False)
        
        self.status_bar = tk.Label(status_bar_frame, text="Ready", relief=tk.SUNKEN,
                                  bg=self.button_bg, fg=self.fg_color, bd=1)
        self.status_bar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # GitHub link
        github_label = tk.Label(status_bar_frame, text="GitHub: JohnConnorNPC/ASA-Log-Bot-NG", 
                               bg=self.button_bg, fg='#58a6ff', cursor="hand2", relief=tk.SUNKEN, bd=1)
        github_label.pack(side=tk.RIGHT, padx=5)
        github_label.bind("<Button-1>", lambda e: self.open_github())
        
        # Discord link
        discord_label = tk.Label(status_bar_frame, text="Discord Support", 
                                bg=self.button_bg, fg='#5865F2', cursor="hand2", relief=tk.SUNKEN, bd=1)
        discord_label.pack(side=tk.RIGHT, padx=5)
        discord_label.bind("<Button-1>", lambda e: self.open_discord())
        
        # Website link
        website_label = tk.Label(status_bar_frame, text="ARK Tools Website", 
                                bg=self.button_bg, fg='#00d26a', cursor="hand2", relief=tk.SUNKEN, bd=1)
        website_label.pack(side=tk.RIGHT, padx=5)
        website_label.bind("<Button-1>", lambda e: self.open_website())
        
    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.add_activity("Monitoring started", "success")
            self.thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.thread.start()
            
            # Start Discord timer thread
            self.discord_timer_thread = threading.Thread(target=self.update_discord_timer, daemon=True)
            self.discord_timer_thread.start()
            
    def stop_monitoring(self):
        if self.running:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.add_activity("Monitoring stopped", "warning")
            
    def clear_logs(self):
        self.logs_display.delete(1.0, tk.END)
        self.logs_data.clear()
        self.add_activity("Logs cleared", "info")
        
    def apply_filter(self):
        """Apply search and filter to logs"""
        self.logs_display.delete(1.0, tk.END)
        
        search_term = self.search_var.get().lower()
        filter_type = self.filter_var.get()
        
        for log in self.logs_data:
            # Check filter type
            if filter_type != "All":
                if filter_type == "Kills" and "killed" not in log['text'].lower():
                    continue
                elif filter_type == "Tames" and "tamed" not in log['text'].lower():
                    continue
                elif filter_type == "Harvests" and "harvested" not in log['text'].lower():
                    continue
                elif filter_type == "Enemy" and "enemy" not in log['text'].lower():
                    continue
                elif filter_type == "Tribe" and not any(word in log['text'].lower() for word in ['tribe', 'your']):
                    continue
            
            # Check search term
            if search_term and search_term not in log['text'].lower():
                continue
                
            # Add to display
            timestamp = log.get('timestamp', datetime.now()).strftime("%H:%M:%S")
            log_text = f"[{timestamp}] {log['text']}\n"
            
            # Determine tag
            tag = None
            if 'killed' in log['text'].lower():
                tag = 'kill'
            elif 'tamed' in log['text'].lower():
                tag = 'tame'
            elif 'harvested' in log['text'].lower():
                tag = 'harvest'
                
            self.logs_display.insert(tk.END, log_text, tag)
            
        self.logs_display.see(tk.END)
        
    def clear_filter(self):
        """Clear search and filter"""
        self.search_var.set("")
        self.filter_var.set("All")
        self.apply_filter()
        
    def add_activity(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            'error': '✗',
            'success': '✓',
            'warning': '⚠',
            'info': '•'
        }.get(level, '•')
        
        self.activity_data.append(f"[{timestamp}] {prefix} {message}")
        self.update_queue.put(('activity', None))
        
    def add_log(self, log_entry):
        # Add timestamp to log entry
        log_entry['timestamp'] = datetime.now()
        self.logs_data.append(log_entry)
        self.update_queue.put(('log', log_entry))
        
    def update_stats(self, key, value):
        self.stats[key] = value
        self.update_queue.put(('stats', None))
        
    def update_members(self, members):
        self.members_data = members
        self.update_queue.put(('members', None))
        
    def start_game(self):
        """Start the Ark game using Steam"""
        try:
            self.add_activity("Attempting to start Ark Ascended...", "warning")
            steam_url = "steam://rungameid/2399830"
            
            # Check platform and use appropriate method
            if sys.platform == "win32":
                os.startfile(steam_url)
            elif sys.platform == "linux" or sys.platform == "linux2":
                # On WSL, use cmd.exe to start Windows programs
                import subprocess
                subprocess.run(["cmd.exe", "/c", "start", steam_url], check=False)
            else:
                raise Exception(f"Unsupported platform: {sys.platform}")
            
            return True
        except Exception as e:
            self.add_activity(f"Error starting game: {e}", "error")
            return False
    
    def run_once(self):
        """Run detection once, execute action if found, and return status"""
        self.add_activity("Starting detection cycle")
        
        if not self.screenshot.find_window():
            window_title = self.config.config.get('window_title')
            self.update_stats('window', 'Not Found')
            self.add_activity(f"Window '{window_title}' not found", "error")
            
            # Try to start the game
            if self.start_game():
                self.add_activity("Starting game...", "warning")
                
                # Wait for game to start with progress indicator
                wait_time = self.config.config.get('game_start_wait', 45)
                for i in range(wait_time):
                    self.add_activity(f"Waiting... {wait_time-i} seconds remaining")
                    time.sleep(1)
                
                # Try to find window again
                if not self.screenshot.find_window():
                    self.add_activity("Game window not found after waiting", "error")
                    return False
                else:
                    self.update_stats('window', window_title)
                    self.add_activity("Game window found", "success")
            else:
                return False
        else:
            self.update_stats('window', self.config.config.get('window_title'))
        
        # Take screenshot
        self.add_activity("Capturing screenshot...")
        img = self.screenshot.capture_window()
        if not img:
            self.add_activity("Failed to capture screenshot", "error")
            return False
        
        # Delete old screenshots before saving new one
        screenshot_dir = self.config.config.get('screenshot_dir', 'screenshots/')
        if hasattr(self, 'last_screenshot_path') and self.last_screenshot_path and os.path.exists(self.last_screenshot_path):
            try:
                os.remove(self.last_screenshot_path)
            except:
                pass
        
        # Save screenshot for debugging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"{screenshot_dir}detection_{timestamp}.png"
        img.save(screenshot_path)
        self.last_screenshot_path = screenshot_path
        
        # Detect current state
        self.add_activity("Detecting state...")
        current_state = self.state_detector.detect_state(img)
        
        if current_state is None:
            self.add_activity("No known state detected", "warning")
            self.update_stats('state', 'Unknown')
            return False
        
        self.add_activity(f"Detected state: {current_state}", "success")
        self.update_stats('state', current_state)
        
        # Get state configuration
        state_config = self.state_detector.get_state_config()
        if not state_config:
            self.add_activity("No configuration found for state", "error")
            return False
        
        # Execute actions
        actions = state_config.get("actions", [])
        self.add_activity(f"Executing {len(actions)} action(s)")
        
        for i, action in enumerate(actions):
            action_name = action.get("name", f"action_{i}")
            action_desc = action.get("description", "")
            
            self.add_activity(f"[{i+1}/{len(actions)}] {action_name}: {action_desc}")
            
            # Handle template substitution for type actions
            if action.get("type") == "type" and "{{" in action.get("text", ""):
                text = action.get("text", "")
                # Replace template variables with actual values
                if "{{server_search}}" in text:
                    text = text.replace("{{server_search}}", self.config.config.get("server_search", ""))
                if "{{bed_name}}" in text:
                    text = text.replace("{{bed_name}}", self.config.config.get("bed_name", ""))
                if "{{random_number}}" in text:
                    import random
                    random_num = random.randint(1000, 9999)
                    text = text.replace("{{random_number}}", str(random_num))
                action = action.copy()
                action["text"] = text
            
            success = self.automation.execute_action(action)
            
            if not success:
                self.add_activity(f"Failed to execute action: {action_name}", "error")
                return False
        
        self.add_activity("Action(s) executed successfully!", "success")
        
        # Check if we're at a log screen state and process logs
        if current_state == "log_screen_online_players_selected":
            self.update_stats('state', 'Processing')
            self.add_activity("Processing logs...")
            
            # Track logs before processing
            import sqlite3
            old_log_count = 0
            try:
                with sqlite3.connect(self.log_processor.log_db_path) as conn:
                    cursor = conn.execute('SELECT COUNT(*) FROM logs')
                    old_log_count = cursor.fetchone()[0]
            except:
                pass
            
            # Process logs - suppress output
            import io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                result = self.log_processor.process_logs(img)
            finally:
                sys.stdout = old_stdout
            
            # Update UI with new logs
            try:
                with sqlite3.connect(self.log_processor.log_db_path) as conn:
                    # Get total count
                    cursor = conn.execute('SELECT COUNT(*) FROM logs')
                    new_count = cursor.fetchone()[0]
                    self.update_stats('logs_processed', new_count)
                    self.update_stats('logs_new', new_count - old_log_count)
                    
                    # Get recent logs for display
                    cursor = conn.execute('SELECT entry_text FROM logs ORDER BY id DESC LIMIT 20')
                    recent_logs = [row[0] for row in cursor]
                    
                    # Add new logs
                    for log_text in reversed(recent_logs):
                        # Check if this log is already in our data
                        if not any(log['text'] == log_text for log in self.logs_data):
                            self.add_log({'text': log_text})
            except:
                pass
            
            # Also process online members
            window_rect = self.screenshot.get_window_rect()
            if window_rect:
                # Handle both tuple and named tuple
                if hasattr(window_rect, 'left'):
                    window_pos = (window_rect.left, window_rect.top)
                else:
                    # Plain tuple format: (left, top, right, bottom)
                    window_pos = (window_rect[0], window_rect[1])
                self.member_processor.process_members(img, window_pos)
                
                # Update UI with member info
                self.update_stats('members_online', self.member_processor.online_member_count)
                
                # Get member details from database
                members = []
                try:
                    import sqlite3
                    with sqlite3.connect(self.member_processor.member_db_path) as conn:
                        cursor = conn.execute('''
                            SELECT name, times_seen, 
                                   CASE WHEN last_seen > datetime('now', '-2 minutes') THEN 1 ELSE is_online END as is_online
                            FROM members 
                            WHERE last_seen > datetime('now', '-10 minutes') 
                            ORDER BY is_online DESC, times_seen DESC
                        ''')
                        members = [{'name': row[0], 'times_seen': row[1], 'is_online': row[2]} for row in cursor]
                except:
                    pass
                
                self.update_members(members)
            
            # Send to Discord if enabled
            if self.discord:
                # Store screenshot for Discord to use
                self.discord.last_screenshot = img
                self.discord.check_and_send_new_logs()
                
                # Update UI with server info
                total_players = self.discord.get_server_info()
                self.update_stats('players_total', total_players)
                self.update_stats('enemies', max(0, total_players - self.stats['members_online']))
        
        return True
    
    def monitoring_loop(self):
        """Main monitoring loop that runs in a separate thread"""
        self.add_activity("Monitoring loop started")
        
        while self.running:
            try:
                success = self.run_once()
                if not success:
                    self.update_stats('state', 'Waiting')
                    self.add_activity("Waiting 5 seconds before next check...")
                    time.sleep(5)
                else:
                    self.add_activity("Cycle completed. Waiting 0.5 seconds...")
                    time.sleep(0.5)
                
            except Exception as e:
                self.add_activity(f"Error: {str(e)}", "error")
                import traceback
                self.add_activity(f"Traceback: {traceback.format_exc()}", "error")
                time.sleep(5)
    
    def update_discord_timer(self):
        """Update Discord timer in a separate thread"""
        while self.running:
            if self.discord and hasattr(self.discord, 'last_discord_post_time'):
                interval = self.config.config.get('discord_post_interval', 60)
                elapsed = time.time() - self.discord.last_discord_post_time
                self.update_stats('discord_timer', max(0, int(interval - elapsed)))
            time.sleep(1)
    
    def update_gui(self):
        """Update GUI elements from the queue"""
        processed_count = 0
        max_updates_per_cycle = 10  # Limit updates to prevent GUI freezing
        
        try:
            while processed_count < max_updates_per_cycle:
                try:
                    update_type, data = self.update_queue.get_nowait()
                    processed_count += 1
                except queue.Empty:
                    break
                
                if update_type == 'stats':
                    # Update status labels
                    for key, label in self.status_labels.items():
                        if key in self.stats:
                            if key == 'discord_timer':
                                label.config(text=f"{self.stats[key]}s")
                            elif key == 'uptime':
                                uptime = str(datetime.now() - self.stats['start_time']).split('.')[0]
                                label.config(text=uptime)
                            elif key == 'window':
                                # Color code window status
                                if self.stats[key] == 'Not Found':
                                    label.config(text=self.stats[key], foreground='#ff6b6b')
                                else:
                                    label.config(text=self.stats[key], foreground='#51cf66')
                            elif key == 'state':
                                # Color code state and limit length
                                state = str(self.stats[key])
                                # Truncate long state names
                                if len(state) > 20:
                                    state = state[:17] + "..."
                                
                                if state in ['Processing', 'Active']:
                                    label.config(text=state, foreground='#51cf66')
                                elif state in ['Waiting', 'Idle']:
                                    label.config(text=state, foreground='#ffd93d')
                                else:
                                    label.config(text=state, foreground='#ff6b6b')
                            else:
                                label.config(text=str(self.stats[key]))
                    
                    # Update uptime separately
                    uptime = str(datetime.now() - self.stats['start_time']).split('.')[0]
                    self.status_labels['uptime'].config(text=uptime)
                            
                elif update_type == 'log':
                    # Add new log to display
                    if data:
                        timestamp = data.get('timestamp', datetime.now()).strftime("%H:%M:%S")
                        log_text = f"[{timestamp}] {data['text']}\n"
                        
                        # Determine tag based on log type
                        tag = None
                        if 'killed' in data['text'].lower():
                            tag = 'kill'
                        elif 'tamed' in data['text'].lower():
                            tag = 'tame'
                        elif 'harvested' in data['text'].lower():
                            tag = 'harvest'
                            
                        self.logs_display.insert(tk.END, log_text, tag)
                        self.logs_display.see(tk.END)
                        
                elif update_type == 'members':
                    # Update members tree
                    self.members_tree.delete(*self.members_tree.get_children())
                    for i, member in enumerate(self.members_data, 1):
                        # Add status indicator
                        status = "🟢" if member.get('is_online', 1) else "🔴"
                        name_with_status = f"{status} {member['name']}"
                        self.members_tree.insert('', 'end', text=str(i), 
                                               values=(name_with_status, member['times_seen']))
                                               
                elif update_type == 'activity':
                    # Update activity display
                    self.activity_display.delete(1.0, tk.END)
                    
                    # Configure tags for activity colors
                    self.activity_display.tag_configure('error', foreground='#ff6b6b')
                    self.activity_display.tag_configure('success', foreground='#51cf66')
                    self.activity_display.tag_configure('warning', foreground='#ffd93d')
                    self.activity_display.tag_configure('info', foreground=self.fg_color)
                    
                    for activity in self.activity_data:
                        # Determine tag based on activity prefix
                        tag = 'info'
                        if '✗' in activity:
                            tag = 'error'
                        elif '✓' in activity:
                            tag = 'success'
                        elif '⚠' in activity:
                            tag = 'warning'
                        
                        self.activity_display.insert(tk.END, activity + '\n', tag)
                    self.activity_display.see(tk.END)
                    
        except Exception as e:
            # Log any GUI update errors
            print(f"GUI update error: {e}")
            
        # Schedule next update
        self.root.after(100, self.update_gui)


def main():
    root = tk.Tk()
    app = ASALogBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()