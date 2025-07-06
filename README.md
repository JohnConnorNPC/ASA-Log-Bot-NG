# ASA-Log-Bot-NG Installation Guide
### by jc0839
Discord Support: https://discord.com/invite/QjtT94TsBE

## Prerequisites
1. **Python 3.8 or higher**
   - Download from: https://www.python.org/downloads/
   - During installation, make sure to check "Add Python to PATH"

2. **Tesseract OCR**
   - Download from: https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe
   - Run the installer and follow the default installation steps
   - The installer will automatically add Tesseract to your system PATH

## Installation Steps
1. **Clone or download the project**
   ```
   git clone https://github.com/JohnConnorNPC/ASA-Log-Bot-NG.git
   cd ASA-Log-Bot-NG
   ```

2. **Install Python dependencies**
   - Run the provided script:
     ```
     install_requirements.cmd
     ```
   - Or manually:
     ```
     pip install -r requirements.txt
     ```

3. **Configure the application**
   - Copy `config.example.json` to `config.json`:
     ```
     copy config.example.json config.json
     ```
   - Open `config.json` in a text editor and adjust the values in the first section according to your needs

4. **Verify installation**
   - Check Python: `python --version`
   - Check pip: `pip --version`
   - Check Tesseract: `tesseract --version`

## What It Does
ASA-Log-Bot-NG automates the following tasks:
- Launches ARK: Survival Ascended
- Navigates through the game menus
- Joins your configured game server
- Spawns your character in using configured bed
- Sets its self up and starts logging
- Posts Tribe Logs to discord webhook
- Posts Online Members to discord webhook

## Required ARK Settings
Before running the bot, you must configure ARK with these specific settings:

### Video Settings
- **Resolution**: 1920x1080
- **Graphics Quality**: Low settings
- Reset to default settings first, then apply these changes

### General/UI Settings
- **Hide Floating Player Names**: ON
- **Structure Tooltip Settings**: OFF
- **Item Notification Settings**: Minimal
- **Floating Names**: OFF

### General/Camera Settings
- **Player Camera Mode**: OFF
- **Camera Shake Scale**: 0
- **Camera View Bob**: OFF
- **All Tooltip and Notification Settings**: OFF
- **Toggle Extended HUD Info**: ON *(IMPORTANT - This must be enabled)*

### Advanced Settings
- **Bandwidth**: Low
- **Force Show Item Names**: OFF
- **UI Vibration**: OFF

## Running the Application
Simply double-click `run.cmd` or execute it from the command line:
```
run.cmd
```
