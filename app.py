import pandas as pd
from flask import Flask, request, jsonify, render_template
import os
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variable to store the controls dictionary
controls_dict = None

def load_excel_file():
    global controls_dict
    try:
        # For Heroku, we'll use an environment variable to specify the file path
        file_path = os.environ.get('EXCEL_FILE_PATH', 'nist_controls.xlsx')
        print(f"Loading Excel file: {file_path}")

        # Load the Excel file
        df = pd.read_excel(file_path)

        # Create a dictionary for quick lookup
        controls_dict = df.set_index('Control Identifier').to_dict('index')

        print(f"Loaded {len(controls_dict)} controls")
        return None
    except Exception as e:
        return f"Error loading Excel file: {str(e)}"

# Load the Excel file when the app starts
load_excel_file()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    if controls_dict is None:
        return jsonify({'error': 'Excel file not loaded'}), 500

    control_id = request.form['control_id']
    if control_id in controls_dict:
        control = controls_dict[control_id]
        related_controls = re.findall(r'\b[A-Z]{2}-\d+\b', control.get('Related Controls', ''))
        related_info = []
        for rc in related_controls:
            if rc in controls_dict:
                related_info.append({
                    'id': rc,
                    'text': controls_dict[rc].get('Control Text', ''),
                    'discussion': controls_dict[rc].get('Discussion', '')
                })
        return jsonify({
            'control_text': control.get('Control Text', ''),
            'discussion': control.get('Discussion', ''),
            'related_controls': related_info
        })
    else:
        return jsonify({'error': 'Control not found'}), 404

if __name__ == '__main__':
    # This is used when running locally. Gunicorn uses the app variable directly
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)