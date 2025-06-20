import os

def setup_environment():
    """Set up environment variables for testing"""
    
    # Check if credentials file exists
    creds_path = "credentials/walk-logger-463501-55094c52ea3d.json"
    if os.path.exists(creds_path):
        print(f"✅ Found credentials file: {creds_path}")
        os.environ["GOOGLE_CREDENTIALS_JSON_PATH"] = creds_path
    else:
        print(f"❌ Credentials file not found: {creds_path}")
        return False
    
    # Set default values for testing
    if not os.getenv("SPREADSHEET_ID"):
        print("⚠️  SPREADSHEET_ID not set. Please set it manually:")
        print("   export SPREADSHEET_ID='your-spreadsheet-id'")
    
    if not os.getenv("SHEET_NAME"):
        print("ℹ️  SHEET_NAME not set, will use default 'Sheet1'")
        os.environ["SHEET_NAME"] = "Sheet1"
    
    if not os.getenv("PORT"):
        print("ℹ️  PORT not set, will use default 5000")
        os.environ["PORT"] = "5000"
    
    return True

if __name__ == "__main__":
    setup_environment() 