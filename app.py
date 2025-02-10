from flask import Flask, request, jsonify, render_template
import google.genai as genai
from google.genai import types
import os
import json
from dotenv import load_dotenv
from flask_cors import CORS

# Load API key from .env file
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini API Client
client = genai.Client(api_key=GENAI_API_KEY)

app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS) to allow requests from any domain
CORS(app, resources={r"/*": {"origins": "*"}})

# Load hospital data from JSON file
def load_nrh_data():
    """Load hospital information from a JSON file."""
    try:
        with open("nrh_data.json", "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return {}

nrh_data = load_nrh_data()

# Function to retrieve relevant hospital information based on user query
def fetch_hospital_info(user_query):
    """Extracts relevant hospital information based on user input."""
    response = []
    query_lower = user_query.lower()
    response = []

    # Define mapping of query keywords to their respective data extraction logic
    query_map = {
        "service": lambda: {service for dept in nrh_data.get("departments", {}).values() for service in dept.get("services", [])},
        "phone": lambda: nrh_data.get("hospital_info", {}).get("contact", {}),
        "contact": lambda: nrh_data.get("hospital_info", {}).get("contact", {}),
        "location": lambda: nrh_data.get("hospital_info", {}).get("location", "Not available"),
        "values": lambda: nrh_data.get("hospital_info", {}).get("values", ["Not available"]),
        "mission": lambda: nrh_data.get("hospital_info", {}).get("values", ["Not available"]),
        "insurance": lambda: nrh_data.get("insurance_partners", ["Not available"]),
        "NHIF": lambda: nrh_data.get("insurance_partners", ["Not available"]),
        "payment": lambda: nrh_data.get("payment_methods", ["Not available"]),
        "facility": lambda: nrh_data.get("facilities", {}),
        "facilities": lambda: nrh_data.get("facilities", {}),
        "visiting": lambda: nrh_data.get("visiting_hours", {}),
        "visiting hours": lambda: nrh_data.get("visiting_hours", {}),
    }

    # Check for general queries in user input
    for keyword, data_extractor in query_map.items():
        if keyword in query_lower:
            data = data_extractor()
            if isinstance(data, dict):
                response.extend([f"{key.capitalize()}: {value}" for key, value in data.items()])
            elif isinstance(data, list):
                response.append(", ".join(data))
            else:
                response.append(str(data))

    # Department-Specific Queries
    for department, details in nrh_data.get("departments", {}).items():
        if department.lower() in query_lower:
            response.append(f"Department of {department.capitalize()}: {details.get('description', 'No description available')}.")
            response.append(f"Services offered: {', '.join(details.get('services', ['No services listed']))}.")

    # General Hospital Information Queries
    if "phone" in query_lower or "contact" in query_lower:
        contacts = nrh_data.get("hospital_info", {}).get("contact", {})
        response.append(f"📞 General Contact: {contacts.get('general', 'Not available')}")
        response.append(f"🚑 Emergency: {contacts.get('emergency', 'Not available')}")
        response.append(f"🚗 Ambulance: {contacts.get('ambulance', 'Not available')}")

    if "location" in query_lower:
        response.append(f"📍 Hospital Location: {nrh_data.get('hospital_info', {}).get('location', 'Not available')}")

    if "values" in query_lower or "mission" in query_lower:
        response.append(f"🏥 Core Values: {', '.join(nrh_data.get('hospital_info', {}).get('values', ['Not available']))}")

    if "insurance" in query_lower or "NHIF" in query_lower:
        response.append(f"✅ Accepted Insurance: {', '.join(nrh_data.get('insurance_partners', ['Not available']))}")

    if "payment" in query_lower:
        response.append(f"💳 Payment Methods: {', '.join(nrh_data.get('payment_methods', ['Not available']))}")

    if "facility" in query_lower or "facilities" in query_lower:
        facilities = nrh_data.get("facilities", {})
        response.append(f"🛏 Beds: {facilitieys.get('beds', 'Not available')}")
        response.append(f"🚑 Ambulances: {facilities.get('ambulances', 'Not available')}")
        response.append(f"💊 Pharmacy: {facilities.get('pharmacy', 'Not available')}")
        response.append(f"📡 Radiology: {', '.join(facilities.get('radiology', []))}")

    if "visiting" in query_lower or "visiting hours" in query_lower:
        visiting = nrh_data.get("visiting_hours", {})
        response.append(f"⏰ Visiting Hours: Morning - {visiting.get('morning', 'Not available')}, Evening - {visiting.get('evening', 'Not available')}.")
        response.append(f"📝 Rules: {', '.join(visiting.get('rules', []))}")

    return "\n".join(response) if response else "I'm sorry, I couldn't find that information."

# Function to generate AI chatbot prompt
def hospital_assistant_prompt(user_input):
    """Constructs a structured prompt for the AI chatbot."""
    hospital_info = fetch_hospital_info(user_input)
    return (
        "You are a virtual assistant for Nakuru Referral Hospital. "
        "Keep responses clear, concise, and helpful. "
        "Avoid formatting responses. no markdown, no asterisks. "
        "Do not provide contact details unless explicitly asked.\n\n"
        f"Hospital Data: {hospital_info}\n"
        f"User: {user_input}\n"
        "Assistant:"
    )

@app.route("/")
def index():
    """Render the index page (frontend interface)."""
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Handles user chat requests and returns AI-generated responses."""
    data = request.json
    user_input = data.get("message")

    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    try:
        # AI Response Generation Configuration
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # Select the model to use
            contents=[hospital_assistant_prompt(user_input)],  # Pass user input as part of the prompt
            config=types.GenerateContentConfig(
                temperature=0.5,  # Controls randomness: lower = more deterministic, higher = more creative
                top_k=30,  # Limits choices per step to top-k likely words
                top_p=0.9,  # Nucleus sampling: selects from top-p probability words
                max_output_tokens=150,  # Restricts response length to 150 tokens
                frequency_penalty=0.3,  # Discourages repetition of frequently used phrases
                presence_penalty=0.1  # Encourages AI to introduce new words
            )
        )

        # Extract AI-generated response
        reply = response.text if response.text else "I'm sorry, I couldn't understand that."

        return jsonify({"response": reply})

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
