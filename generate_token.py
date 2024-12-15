import jwt
import datetime

# Secret key for JWT signing
SECRET_KEY = "your_secret_key"  # Replace with the same key used in server.py

# Function to generate a token
def generate_token(user_id: int):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # Expires in 1 hour
        "iat": datetime.datetime.utcnow(),  # Issued at
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

if __name__ == "__main__":
    # Replace with your desired user ID
    user_id = 1
    token = generate_token(user_id)
    print(f"Generated Token: {token}")
