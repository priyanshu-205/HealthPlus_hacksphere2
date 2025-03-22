from flask import Flask, request, jsonify, render_template
import pytesseract
from PIL import Image
import os
import re
import spacy
import cv2
import numpy as np

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load spaCy model (prefer medical model if available)
try:
    nlp = spacy.load("en_core_sci_md")  # Best accuracy for medicine
except:
    try:
        nlp = spacy.load("en_core_sci_sm")  # Smaller fallback
    except:
        nlp = spacy.load("en_core_web_sm")  # Generic fallback

# Optional: Blacklist common noisy words
blacklist = {
    "store", "keep", "avoid", "facts", "for", "shake", "active",
    "inc", "consult", "information", "warnings", "ingredients",
    "reorder", "leaf", "fast", "will", "safetec", "usp", "drug", "america"
}

# Preprocess image to improve OCR accuracy
def preprocess_image_for_ocr(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh = cv2.adaptiveThreshold(blur, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    processed_path = image_path.replace('.png', '_processed.png')
    cv2.imwrite(processed_path, thresh)
    return processed_path

# Extract medicine-related information from OCR text
def extract_medicine_info(ocr_text):
    # Regex-based name and dosage extraction
    names = re.findall(r'\b[A-Z][A-Za-z]{2,}\b', ocr_text)
    names = [n for n in names if n.lower() not in blacklist and len(n) > 2]

    dosage = re.findall(r'\b\d{1,4}\s?(mg|ml|g|mcg|MG|ML|IU|G|Mcg)\b', ocr_text)
    expiry = re.findall(r'(EXP|Exp|exp|Expiry|EXPIRY)[:\s]*([0-9]{2}/[0-9]{2,4})', ocr_text)

    # NLP-based entity extraction (medical-focused labels)
    doc = nlp(ocr_text)
    usage = [ent.text.strip() for ent in doc.ents if ent.label_ in [
        'PRODUCT', 'CHEMICAL', 'DRUG', 'GENE_OR_GENE_PRODUCT', 'ORG', 'GPE']]
    usage = [u for u in usage if u.lower() not in blacklist and len(u) > 2]

    return {
        "medicine_names": sorted(set(names + usage)),
        "dosage": sorted(set(dosage)),
        "expiry_dates": [f'{e[0]}: {e[1]}' for e in expiry],
        "usage_info": sorted(set(usage))
    }

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/api/extract', methods=['POST'])
def extract():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # Preprocess and run OCR
    processed_path = preprocess_image_for_ocr(filepath)
    ocr_text = pytesseract.image_to_string(Image.open(processed_path), config='--oem 3 --psm 6')

    # Extract structured medicine information
    extracted_data = extract_medicine_info(ocr_text)

    return jsonify({
        "ocr_text": ocr_text,
        "medicine_details": extracted_data
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
