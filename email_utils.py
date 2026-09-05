import os
from dotenv import load_dotenv
load_dotenv()

def send_otp(to_email, code, purpose):
    """
    MOCK EMAIL SENDER FOR FREE TIER RENDER.
    Instead of hitting port 587 (which Render blocks), this prints the OTP 
    directly to the Render server logs.
    """
    print("\n" + "="*50, flush=True)
    print(f"🚨 MOCK EMAIL SENT 🚨", flush=True)
    print(f"To: {to_email}", flush=True)
    print(f"Purpose: {purpose}", flush=True)
    print(f"OTP CODE: {code}", flush=True)
    print("="*50 + "\n", flush=True)
    
    # Return success so the frontend thinks the email was sent
    return True, "sent"