#!/usr/bin/env python3
"""
Setup Verification Script
Run this before starting the application to ensure everything is configured correctly.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11+"""
    version = sys.version_info
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ ERROR: Python 3.11+ is required")
        return False
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ ERROR: .env file not found")
        print("   Create one with: cp .env.example .env")
        print("   Or manually create .env with required variables")
        return False
    
    print("✓ .env file exists")
    
    # Check for required environment variables
    required_vars = ["GOOGLE_API_KEY"]
    missing_vars = []
    
    with open(env_path, 'r') as f:
        content = f.read()
        for var in required_vars:
            if var not in content or f'{var}="your-' in content:
                missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ ERROR: Missing or unconfigured variables: {', '.join(missing_vars)}")
        print("   Update your .env file with valid values")
        return False
    
    print("✓ Required environment variables configured")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "langchain",
        "langchain_google_genai",
        "pydantic_settings"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} not installed")
    
    if missing_packages:
        print("\n❌ ERROR: Missing required packages")
        print("   Install with: poetry install")
        print("   Or: pip install -r requirements.txt")
        return False
    
    return True

def check_directories():
    """Check if required directories exist"""
    required_dirs = [
        "data/feedback",
        "logs",
        "app/agents",
        "app/api",
        "app/core",
        "app/learning",
        "app/orchestration"
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            print(f"⚠️  Creating directory: {dir_path}")
            path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"✓ Directory exists: {dir_path}")
    
    return True

def check_google_api():
    """Test if Google API key is valid"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            print("❌ ERROR: GOOGLE_API_KEY not found in environment")
            return False
        
        if api_key.startswith("your-"):
            print("❌ ERROR: GOOGLE_API_KEY still has placeholder value")
            return False
        
        print("✓ GOOGLE_API_KEY is set")
        
        # Try to import and initialize the LLM
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                google_api_key=api_key,
                temperature=0.7
            )
            
            # Try a simple invocation
            result = llm.invoke("Say 'OK' if you can read this")
            print("✓ Google Gemini API connection successful")
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Failed to connect to Google Gemini API: {str(e)}")
            print("   Please check your API key at: https://aistudio.google.com/")
            return False
            
    except ImportError:
        print("⚠️  Cannot test API key (langchain not installed)")
        return True  # Don't fail if packages not installed yet

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Agentic Observability Backend - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Required Directories", check_directories),
        ("Dependencies", check_dependencies),
        ("Google API Configuration", check_google_api),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n📋 Checking: {check_name}")
        print("-" * 60)
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ ERROR during {check_name}: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 60)
    
    if all(results):
        print("✅ All checks passed! You're ready to run the application.")
        print("\nStart the server with:")
        print("  poetry run uvicorn app.main:app --reload")
        print("  or")
        print("  uvicorn app.main:app --reload")
        print("\nThen visit: http://localhost:8000/docs")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

