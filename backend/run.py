import uvicorn
import argparse
import os
from app.config import settings

# Command line is as follows:
# python run.py --entity "Banco ABC1"

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Start the Swap Snipper application.')
    
    # Add only the two required arguments
    parser.add_argument('--entity', required=True)
    args = parser.parse_args()

    # Store arguments in environment variables for access in the app
    os.environ['MY_ENTITY'] = args.entity

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.DEBUG
    )