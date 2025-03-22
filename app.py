from flask import Flask, render_template, request, jsonify
import json
import pytesseract
from PIL import Image
import os
from werkzeug.utils import secure_filename
import difflib  # For fuzzy matching
from googletrans import Translator

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
translator = Translator()

# Load medicine data from JSON
def load_json():
    with open("data.json", "r", encoding="utf-8") as file:
        return json.load(file)

# Check if the uploaded file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Extract text from image using OCR
def extract_text_from_image(image_path):
    image = Image.open(image_path)
    extracted_text = pytesseract.image_to_string(image)
    print("Extracted Text:", extracted_text)  # Debug output
    return extracted_text.strip().lower()

# Fuzzy matching to find the best matching medicine name
def find_best_match(extracted_text, medicines):
    medicine_names = [med["name"].strip().lower() for med in medicines]
    matches = difflib.get_close_matches(extracted_text, medicine_names, n=1, cutoff=0.5)
    return matches[0] if matches else None

# Translate a medicine dictionary to Hindi
def translate_to_hindi(medicine):
    translated = {}
    for key, value in medicine.items():
        if isinstance(value, str):
            translated[key] = translator.translate(value, src='en', dest='hi').text
        elif isinstance(value, list):
            translated[key] = [translator.translate(item, src='en', dest='hi').text for item in value]
        elif isinstance(value, dict):
            translated[key] = {k: translator.translate(v, src='en', dest='hi').text for k, v in value.items()}
        else:
            translated[key] = value
    return translated

# Home route – renders the upload page
@app.route("/")
def home():
    return render_template("index.html")

# Upload and process image; returns English result
@app.route("/upload", methods=["POST"])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract OCR text from the image
        extracted_text = extract_text_from_image(filepath)
        medicines = load_json()["medicines"]

        # Try exact substring match first
        for medicine in medicines:
            if medicine["name"].strip().lower() in extracted_text:
                return jsonify({
                    "ocr_text": extracted_text,
                    "medicine_details": medicine
                })

        # If no exact match, use fuzzy matching
        best_match_name = find_best_match(extracted_text, medicines)
        if best_match_name:
            matched_medicine = next(med for med in medicines if med["name"].strip().lower() == best_match_name)
            return jsonify({
                "ocr_text": extracted_text,
                "medicine_details": matched_medicine
            })

        return jsonify({"error": "Medicine not found", "ocr_text": extracted_text}), 404

# Translation endpoint: translates English medicine details to Hindi
@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json()
    if not data or "medicine_details" not in data:
        return jsonify({"error": "No medicine details provided"}), 400

    english_details = data["medicine_details"]
    hindi_details = translate_to_hindi(english_details)
    return jsonify({
        "translated_medicine_details": hindi_details
    })

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
