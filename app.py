from flask import Flask, request, jsonify, render_template
import pytesseract
from PIL import Image
import os
import re
import spacy

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Function to extract info using regex and spaCy
def extract_medicine_info(ocr_text):
    # regex-based extraction
    names = re.findall(r'\b[A-Z][A-Za-z]{2,}\b', ocr_text)
    dosage = re.findall(r'\b\d{1,4}\s?(mg|ml|MG|ML|Mg|Ml)\b', ocr_text)
    expiry = re.findall(r'(EXP|Exp|exp|Expiry|EXPIRY)[:\s]*([0-9]{2}/[0-9]{2,4})', ocr_text)

    # NLP-based entity recognition
    doc = nlp(ocr_text)
    usage = [ent.text for ent in doc.ents if ent.label_ in ['ORG', 'PRODUCT', 'WORK_OF_ART', 'FAC', 'GPE']]

    return {
        "medicine_names": list(set(names)),
        "dosage": list(set(dosage)),
        "expiry_dates": [f'{e[0]}: {e[1]}' for e in expiry],
        "usage_info": list(set(usage))
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

    # OCR
    ocr_text = pytesseract.image_to_string(Image.open(filepath))

    # NLP + regex-based extraction
    extracted_data = extract_medicine_info(ocr_text)

    return jsonify({
        "ocr_text": ocr_text,
        "medicine_details": extracted_data
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
