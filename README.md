# ASA-Log-Bot-NG

An automated logging bot for ARK: Survival Ascended that monitors tribe logs and posts updates to Discord.

**Created by:** jc0839  
**Discord Support:** [Join our Discord](https://discord.com/invite/QjtT94TsBE)

## 🚀 Features

- Automatically launches ARK: Survival Ascended
- Navigates through game menus
- Joins configured game servers
- Spawns character using configured bed
- Monitors and logs tribe activities
- Posts tribe logs to Discord webhooks
- Posts online member updates to Discord webhooks
- Retrieves total player count using GameDig

## 📋 Prerequisites

### 1. Python 3.8+
- Download from [python.org](https://www.python.org/downloads/)
- ⚠️ **Important:** Check "Add Python to PATH" during installation

### 2. Tesseract OCR
- Download: [tesseract-ocr-w64-setup-5.3.3.20231005.exe](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe)
- Run the installer with default settings
- The installer will automatically add Tesseract to your system PATH

### 3. Node.js & npm
- Download from [nodejs.org](https://nodejs.org/)
- Download the Windows Installer (.msi) for the LTS version
- npm is included with Node.js

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/JohnConnorNPC/ASA-Log-Bot-NG.git
cd ASA-Log-Bot-NG
```

### 2. Install Python Dependencies
Run the provided script:
```bash
install_requirements.cmd
```

Or manually:
```bash
pip install -r requirements.txt
```

### 3. Install GameDig
After installing Node.js, install GameDig globally:
```bash
npm install -g gamedig
```

### 4. Configure the Application
1. Copy the example configuration:
   ```bash
   copy config.example.json config.json
   ```
2. Edit `config.json` with your preferred text editor
3. Adjust the values according to your server and Discord webhook settings

## ⚙️ Required ARK Settings

Before running the bot, configure ARK: Survival Ascended with these specific settings:

### Video Settings
- **Resolution:** 1920x1080
- **Graphics Quality:** Low settings
- Reset to default settings first, then apply these changes

### General/UI Settings
| Setting | Value |
|---------|-------|
| Hide Floating Player Names | ON |
| Structure Tooltip Settings | OFF |
| Item Notification Settings | Minimal |
| Floating Names | OFF |
| Toggle Extended HUD Info | **ON** ⚠️ |

> ⚠️ **IMPORTANT:** Toggle Extended HUD Info MUST be enabled for the bot to function properly

### General/Camera Settings
| Setting | Value |
|---------|-------|
| Player Camera Mode | OFF |
| Camera Shake Scale | 0 |
| Camera View Bob | OFF |
| All Tooltip and Notification Settings | OFF |

### Advanced Settings
| Setting | Value |
|---------|-------|
| Bandwidth | Low |
| Force Show Item Names | OFF |
| UI Vibration | OFF |

## 🎮 Running the Bot

Double-click `run.cmd` or execute from command line:
```bash
run.cmd
```

## 📝 Configuration Notes

The `config.json` file should contain:
- Server connection details
- Discord webhook URLs
- Character spawn settings
- Bot behavior preferences

## 🤝 Support

Need help? Join our [Discord Support Server](https://discord.com/invite/QjtT94TsBE)
