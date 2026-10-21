import os
from dotenv import load_dotenv
from google import genai

# 1. Load environment variables from the .env file
load_dotenv()

# 2. Initialize the official Google GenAI client
# It automatically looks for the GEMINI_API_KEY environment variable
client = genai.Client()

def test_gemini_ping():
    try:
        print("Connecting to Gemini API...")
        
        # 3. Send a simple prompt using a fast, high-limit flash model
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents="Hello! Confirm you are online and ready to help audit manufacturing invoices.",
        )
        
        print("\n--- Success! Response from Gemini ---")
        print(response.text)
        print("--------------------------------------")
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")

if __name__ == "__main__":
    test_gemini_ping()