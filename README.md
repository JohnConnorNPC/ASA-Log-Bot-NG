# ASA-Log-Bot-NG Installation Guide
### by jc0839
Discord Support: https://discord.com/invite/QjtT94TsBE
![image](https://github.com/user-attachments/assets/ed4f7545-d0ce-4b8e-94aa-304d6877d83c)

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

## Running the Application
Simply double-click `run.cmd` or execute it from the command line:
```
run.cmd
```

## Troubleshooting
- **Python not found**: Make sure Python is added to your PATH environment variable
- **Tesseract not found**: Restart your command prompt after installing Tesseract
- **Module not found errors**: Run `install_requirements.cmd` again
- **Permission errors**: Run command prompt as Administrator
- **Config file errors**: Ensure `config.json` is properly formatted JSON and all required fields are filled
