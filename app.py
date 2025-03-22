from flask import Flask, render_template, request, jsonify
import json
import pytesseract
from PIL import Image
import os
from werkzeug.utils import secure_filename
import difflib  # For fuzzy matching

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load medicine data from JSON
def load_json():
    with open("data.json", "r") as file:
        return json.load(file)

# Check if uploaded file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Extract text from image using OCR
def extract_text_from_image(image_path):
    image = Image.open(image_path)
    extracted_text = pytesseract.image_to_string(image)
    print("Extracted Text:", extracted_text)  # For debugging
    return extracted_text.strip().lower()

# Fuzzy matching function to find best matching medicine name
def find_best_match(extracted_text, medicines):
    medicine_names = [med["name"].strip().lower() for med in medicines]
    matches = difflib.get_close_matches(extracted_text, medicine_names, n=1, cutoff=0.5)
    return matches[0] if matches else None

# Home route
@app.route("/")
def home():
    return render_template("index.html")

# Upload and process image
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

        # Extract text and match medicine
        extracted_text = extract_text_from_image(filepath)
        print("text",extracted_text)
        medicines = load_json()["medicines"]
        print("medicines",medicines)

        # First try direct substring match
        for medicine in medicines:
            if medicine["name"].strip().lower() in extracted_text:
                return jsonify(medicine)

        # If no exact match, try fuzzy matching
        best_match_name = find_best_match(extracted_text, medicines)
        if best_match_name:
            matched_medicine = next(med for med in medicines if med["name"].strip().lower() == best_match_name)
            return jsonify(matched_medicine)

        return jsonify({"error": "Medicine not found"}), 404

# Display medicine information (if using HTML templates)
@app.route("/medicine/<medicine_name>")
def show_medicine(medicine_name):
    medicines = load_json()["medicines"]
    for medicine in medicines:
        if medicine["name"].strip().lower() == medicine_name:
            return render_template("medicine.html", medicine=medicine)
    return "Medicine not found", 404

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

