#!/usr/bin/env python3
# build_app.py
# Script to build macOS application using PyInstaller

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_app():
    """Build the macOS application"""
    
    print("Building Stock Tracker macOS Application...")
    print("=" * 50)
    
    # Application details
    app_name = "StockTracker"
    main_script = "main.py"
    
    # Check if main script exists
    if not os.path.exists(main_script):
        print(f"❌ Error: {main_script} not found!")
        return False
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name", app_name,
        "--windowed",  # No console window
        "--onefile",   # Single executable
        "--clean",     # Clean cache
        "--noconfirm", # Overwrite without confirmation
        
        # Icon (if available)
        # "--icon", "icon.ico",  # Uncomment if you have an icon
        
        # Additional data files
        "--add-data", "data:data",  # Include data directory
        
        # Hidden imports (add if needed)
        "--hidden-import", "pandas",
        "--hidden-import", "yfinance",
        "--hidden-import", "schedule",
        "--hidden-import", "tkinter",
        
        # Exclude unnecessary modules to reduce size
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "IPython",
        
        main_script
    ]
    
    try:
        print("Running PyInstaller...")
        print(f"Command: {' '.join(cmd)}")
        print()
        
        # Run PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=False)
        
        print("\n✅ Build successful!")
        
        # Show output location
        dist_path = Path("dist")
        app_path = dist_path / f"{app_name}.app"
        
        if app_path.exists():
            print(f"📱 macOS App created: {app_path}")
        else:
            exe_path = dist_path / app_name
            if exe_path.exists():
                print(f"🖥️  Executable created: {exe_path}")
        
        print(f"📁 Build files in: {dist_path}")
        
        # Show app size
        try:
            if app_path.exists():
                size = get_directory_size(app_path)
                print(f"📦 App size: {size:.1f} MB")
        except:
            pass
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with return code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        return False

def get_directory_size(path):
    """Get directory size in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)  # Convert to MB

def clean_build():
    """Clean build directories"""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["*.spec"]
    
    print("Cleaning build directories...")
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑️  Removed {dir_name}")
    
    # Clean spec files
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"🗑️  Removed {spec_file}")

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def main():
    """Main build script"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "clean":
            clean_build()
            return
        elif sys.argv[1] == "deps":
            install_dependencies()
            return
    
    print("Stock Tracker - Build Script")
    print("=" * 30)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher required")
        return
    
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check if we're in virtual environment (recommended)
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
    else:
        print("⚠️  Not in virtual environment (recommended to use venv)")
    
    # Install dependencies first
    if not install_dependencies():
        return
    
    # Build the app
    if build_app():
        print("\n🎉 Build completed successfully!")
        print("\nYou can now run the app from:")
        print("  - dist/StockTracker.app (double-click to run)")
        print("  - Or drag to Applications folder")
    else:
        print("\n💥 Build failed!")

if __name__ == "__main__":
    main()