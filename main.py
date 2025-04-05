import openai
import base64
import json
from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv("OPEN_API_KEY")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Read and encode the image
image_path = "WhatsApp Image 2025-04-05 at 13.19.46_a48c2e13.jpeg"
base64_image = encode_image(image_path)

# Define the JSON schema as a Python dict
json_schema = {
    "type": "object",
    "properties": {
        "keywords": {
            "type": "array",
            "description": "List of keywords that describe the content of the image.",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5
        }
    },
    "required": ["keywords"],
    "additionalProperties": False
}

# Create the prompt instructing the model what to do
prompt = (
    "I am sending an image of an incident. Find out whether the image indicates an emergency or not and "
    "provide exactly five keywords describing the situation. Choose exclusively from keywords such as "
    "'accident', 'not accident', 'emergency', 'fire', 'flood', etc. Return only a JSON object following "
    "the schema provided."
)

client = openai.OpenAI(api_key=key)

# Send the image and prompt to the model using the OpenAI Output API
response = client.responses.create(
    model="gpt-4o",  # Adjust the model name if needed
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"}
            ]
        }
    ],
    text={
        "format": {
            "name":"keywords",
            "type": "json_schema",
            "schema": {
                "type": "object",
                "strict": True,
                "name": "keywords",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["keywords"],
                "additionalProperties": False
            }
        }
    }
)

print(response)

