
import requests

def get_character_profiles():
    """Return a list of available characters with images and descriptions."""
    return [
        {"name": "Barış Terkoğlu", "description": "A critical thinker and columnist.", "image": "assets/baris_terkoglu.png"},
        {"name": "Ahmet Hakan", "description": "An insightful journalist with bold opinions.", "image": "assets/ahmet_hakan.png"},
        {"name": "Can Dündar", "description": "A passionate journalist with a strong voice.", "image": "assets/can_dundar.png"}
    ]

def get_response_from_llm(user_input, character_name):
    """Send the user input and character to the LLM and get the response."""
    try:
        api_url = "http://127.0.0.1:5000/get_response"
        payload = {"message": user_input, "persona": character_name}
        response = requests.post(api_url, json=payload)
        if response.status_code == 200:
            return response.json().get("response", "No response from model.")
        else:
            return "Error: Unable to get a response from the LLM."
    except Exception as e:
        return f"Error: {str(e)}"
