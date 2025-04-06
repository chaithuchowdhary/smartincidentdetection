from flask import Flask, request, jsonify, Response
from functools import wraps
import bcrypt
import openai
import base64
import json
from dotenv import load_dotenv
import os
from pushbullet import Pushbullet
from pymongo import MongoClient
from flask_socketio import SocketIO, emit
from flask_cors import CORS, cross_origin
import tempfile 

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["smartincidentdetection"]
collection = db["incidents"]
users_collection = db["user"]

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['CORS_HEADERS'] = 'Content-Type'
CORS(app, origins="*", methods=["GET", "POST"], supports_credentials=True)

key = os.getenv("OPEN_API_KEY")
openai.api_key = key

API_KEY = os.getenv("PUSH_BULLET_KEY")
pb = Pushbullet(API_KEY)

def require_basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return Response(
                "Missing credentials", 
                401, 
                {"WWW-Authenticate": 'Basic realm="Login Required"'}
            )
        user = users_collection.find_one({"username": auth.username})
        if not user:
            return Response(
                "Unauthorized", 
                401, 
                {"WWW-Authenticate": "Login Required"}
            )
        stored_password = user.get("password")
        if isinstance(stored_password, bytes):

            if not bcrypt.checkpw(auth.password.encode('utf-8'), stored_password):
                return Response(
                    "Unauthorized", 
                    401, 
                    {"WWW-Authenticate": "Login Required"}
                )
        else:
            
            if auth.password != stored_password:
                return Response(
                    "Unauthorized", 
                    401, 
                    {"WWW-Authenticate": "Login Required"}
                )
        return f(*args, **kwargs)
    return decorated


def send_push_to_channel(title, message, base64_image):
    print("Connecting to pushbullet...")

    channels = pb.channels
    
    channel = next((ch for ch in channels if ch.channel_tag == "untdemoalert"), None)

    if channel:
        print(f"Found channel: {channel.name}")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(base64.b64decode(base64_image))
                temp_file_path = temp_file.name

            # Upload the file to get the file_url and other details.
            with open(temp_file_path, "rb") as f:
                file_data = pb.upload_file(f, "incident.jpg", "image/jpeg")

            # Use the returned file_data in push_file; note there's no 'file' parameter.
            push = pb.push_file(
                file_name=file_data["file_name"],
                file_type=file_data["file_type"],
                file_url=file_data["file_url"],
                title=title,
                body=message,
                channel=channel
            )
            print("Push sent! Response:")
            print(push)
        except Exception as e:
            print(f"Failed to send push: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    else:
        print("Channel not found. Make sure this API key is linked to a user subscribed to @untdemoalert.")


def encode_image(file_obj):
    return base64.b64encode(file_obj.read()).decode("utf-8")
    
@app.route('/analyze', methods=['POST'])
@cross_origin()
@require_basic_auth
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    if 'location' not in request.form:
        return jsonify({"error": "No location provided"}), 400

    image_file = request.files['image']
    base64_image = encode_image(image_file)

    prompt = (
        "I am sending an image of an incident. Find out whether the image indicates an emergency or not and "
        "provide exactly five keywords describing the situation. Choose exclusively from keywords such as "
        "'accident', 'not accident', 'emergency', 'fire', 'flood', etc. Return only a JSON object following "
        "the schema provided."
    )
    
    client = openai.OpenAI(api_key=key)
    
    response = client.responses.create(
        model="gpt-4o",
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
                        },
                        "decision":{
                            "type": "string",
                            "enum": ["emergency", "not emergency"],
                            "description": "Decision on whether the image indicates an emergency or not."
                        }
                    },
                    "required": ["keywords","decision"],
                    "additionalProperties": False
                }
            }
        }
    )

    try:
        result = json.loads(response.output_text)
    except Exception as e:
        return jsonify({"error": "Failed to parse response", "details": str(e)}), 500
    
    

    collection.insert_one({
        "emergency": result.get("decision", None),
        "location": request.form['location'],
        "keywords": result.get("keywords", []),
        "decision": result.get("decision", None),
        "image": base64_image
    })

    if result.get("decision") == "emergency":
        send_push_to_channel("Emergency Alert",f"Emergency detected at {request.form['location']}! Keywords: {', '.join(result.get('keywords', []))}",base64_image)
        payload = {
            "event": "emergency_detected",
            "keywords": result.get("keywords", []),
            "location": request.form['location']
        }
        incident = {
            "emergency": result.get("decision", None),
            "location": request.form['location'],
            "keywords": result.get("keywords", []),
            "decision": result.get("decision", None),
            "image": base64_image
        }
        socketio.emit("new_incident",incident)
        return jsonify(payload), 200
    else:
        return jsonify({"message": "No emergency detected", "keywords": result.get("keywords", [])}), 200
    
@app.route('/incidents', methods=['GET'])
@cross_origin()
@require_basic_auth
def get_incidents():
    incidents = list(collection.find({}))
    for inc in incidents:
        inc["_id"] = str(inc["_id"])
    return jsonify(incidents)

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True, port=5000)

