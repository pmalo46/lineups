"""
Main entry point for the Lineups application.
"""

import os
from dotenv import load_dotenv
from ui.app import main as app_main

def main():
    # Load environment variables
    load_dotenv()
    
    # Ensure required environment variables are set
    required_vars = ['TANK01_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Start the Streamlit app
    app_main()

if __name__ == '__main__':
    main() 