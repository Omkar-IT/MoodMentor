import os
import requests
from dotenv import load_dotenv

load_dotenv()

# PASTE YOUR NEW API KEY HERE
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
# PUT YOUR GMAIL ADDRESS HERE
SENDER_EMAIL = os.getenv("SMTP_EMAIL", "teamcinfosys@gmail.com")

def send_otp(to_email, code, purpose):
    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    
    subject = "Your Verification Code" if purpose == "signup" else "Your Password Reset Code"
    body = f"Your code is: {code}\nExpires in 10 minutes."
    
    payload = {
        "sender": {"name": "MoodMentor", "email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code in (200, 201, 202):
            return True, "sent"
        else:
            return False, f"API Error: {response.text}"
            
    except Exception as e:
        return False, str(e)