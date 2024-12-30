import os
import shutil
import json
import base64
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import logic
from enum import Enum
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends, FastAPI, Form, File, Response, UploadFile, HTTPException
from logic import generate_project_plan_from_sow  # Assuming you will create this function for processing Excel files
from pathlib import Path
from enum import Enum
from logic import sanitize_csv
import pandas as pd

# Directory for temporary file storage
UPLOAD_DIR = "/tmp/uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()


class ExperienceLevels(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"
    
    def __str__(self):
        return self.value



# Static API key for authentication
STATIC_API_KEY = "0bcf49a90e765ca3d7ea8ba1ae25373142e374c556919aa3e5c41adf8b2ff220"

# OAuth2 password flow (usually for getting tokens from a token endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# For bearer token (commonly used with OAuth2)
bearer_auth = HTTPBearer()

def authenticate(
    token: HTTPAuthorizationCredentials = Depends(bearer_auth)
):
    """
    Dependency to check for either a valid static API key or a valid OAuth2 bearer token.
    
    Args:
        api_key (str): The API key from the request headers.
        token (HTTPAuthorizationCredentials): The bearer token from the Authorization header.
    
    Raises:
        HTTPException: If neither the API key nor the OAuth2 token is valid.
    """
    # Check if the bearer token is valid (this is where you'd validate it properly)
    if token and token.credentials == STATIC_API_KEY:  # Replace with actual token validation
        return

    raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key or token")

@app.post("/upload-file/", dependencies=[Depends(authenticate)])
async def upload_file(file: UploadFile = File(...), experience_level: ExperienceLevels = Form(...)):
    """
    Endpoint to upload a PDF or Excel file directly.
    
    Args:
        file (UploadFile): The uploaded file.
        experience_level (ExperienceLevels): The experience level provided by the user.
    
    Returns:
        JSON response with file path and confirmation message.
    """
    # Check if file is PDF or Excel
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension == "pdf":
        file_type = "pdf"
    elif file_extension in ["xlsx", "xls"]:
        file_type = "excel"
    else:
        raise HTTPException(status_code=400, detail="Only PDF or Excel files are allowed.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # Save the uploaded file to the specified path
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save file to server.")
    
    try:
        if file_type == "pdf":
            # Process the PDF file (existing logic)
            csv_text = generate_project_plan_from_sow(file_path, str(experience_level))
        elif file_type == "excel":
            # Process the Excel file (new logic)
            csv_text = excel_file_path(file_path, str(experience_level))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    # Integrate CSV download logic here
    csv_response = Response(content=sanitize_csv(csv_text), media_type="text/csv")
    csv_response.headers["Content-Disposition"] = f"attachment; filename={file.filename.rsplit('.', 1)[0]}.csv"
    
    return csv_response

# Add a new logic function to handle Excel files
def excel_file_path(file_path: str, experience_level: str) -> str:
    """
    Function to process an Excel file and return CSV formatted text.
    
    Args:
        file_path (str): Path to the uploaded Excel file.
        experience_level (str): The experience level provided by the user.
    
    Returns:
        str: The CSV data extracted from the Excel file.
    """
    # Read the Excel file
    try:
        df = pd.read_excel(file_path)
        # Assuming you want to convert the whole file to CSV format
        csv_text = df.to_csv(index=False)
        return csv_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing Excel file: {str(e)}")



