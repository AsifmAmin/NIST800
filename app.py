import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template
import os
import re
from flask_cors import CORS
import logging
import json

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global variable to store the controls dictionary
controls_dict = None


def load_excel_file():
    global controls_dict
    try:
        file_path = os.environ.get('EXCEL_FILE_PATH', 'nist_controls.xlsx')
        logger.info(f"Loading Excel file: {file_path}")

        # Load the Excel file
        df = pd.read_excel(file_path)

        # Replace NaN values with None
        df = df.replace({np.nan: None})

        # Create a dictionary for quick lookup, using 'Control Identifier' as the key
        controls_dict = df.set_index('Control Identifier').to_dict('index')

        logger.info(f"Loaded {len(controls_dict)} controls")
        logger.debug(f"Control IDs: {list(controls_dict.keys())[:10]}...")  # Log first 10 control IDs
        return None
    except Exception as e:
        logger.error(f"Error loading Excel file: {str(e)}")
        return f"Error loading Excel file: {str(e)}"

# Custom JSON encoder to handle NaN and None values
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and np.isnan(obj):
            return None
        return super().default(obj)


app.json_encoder = CustomJSONEncoder

# Load the Excel file when the app starts
load_result = load_excel_file()
if load_result:
    logger.error(load_result)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    if controls_dict is None:
        logger.error("Controls dictionary is None")
        return jsonify({'error': 'Excel file not loaded'}), 500

    base_control_id = request.form['control_id']
    logger.info(f"Searching for control: {base_control_id}")

    base_control = controls_dict.get(base_control_id)

    if not base_control:
        logger.warning(f"Control not found: {base_control_id}")
        logger.debug(f"Available controls: {list(controls_dict.keys())[:20]}")  # Log first 20 control IDs
        return jsonify({'error': 'Control not found'}), 404

    # Find all variations for the base control
    variations = [base_control_id] + [
        key for key in controls_dict.keys()
        if str(key).startswith(f"{base_control_id}(") and str(key).endswith(")")
    ]

    logger.info(f"Found variations: {variations}")

    result = {
        'base_control': {
            'id': base_control_id,
            'text': base_control.get('Control Text'),
            'discussion': base_control.get('Discussion')
        },
        'variations': []
    }

    for var_id in variations:
        var_control = controls_dict.get(var_id)
        if var_control:
            result['variations'].append({
                'id': var_id,
                'text': var_control.get('Control Text'),
                'discussion': var_control.get('Discussion')
            })

    # Find related controls and their variations
    related_controls = re.findall(r'\b[A-Z]{2}-\d+\b', str(base_control.get('Related Controls', '')))
    result['related_controls'] = []

    for rc in related_controls:
        if rc in controls_dict:
            rc_variations = [rc] + [
                key for key in controls_dict.keys()
                if str(key).startswith(f"{rc}(") and str(key).endswith(")")
            ]
            rc_data = {
                'id': rc,
                'text': controls_dict[rc].get('Control Text'),
                'discussion': controls_dict[rc].get('Discussion'),
                'variations': []
            }
            for var_id in rc_variations[1:]:  # Skip the base control
                var_control = controls_dict.get(var_id)
                if var_control:
                    rc_data['variations'].append({
                        'id': var_id,
                        'text': var_control.get('Control Text'),
                        'discussion': var_control.get('Discussion')
                    })
            result['related_controls'].append(rc_data)

    logger.info(
        f"Returning result for {base_control_id} with {len(result['variations'])} variations and {len(result['related_controls'])} related controls")
    return jsonify(result)


@app.route('/search_keyword', methods=['POST'])
def search_keyword():
    if controls_dict is None:
        logger.error("Controls dictionary is None")
        return jsonify({'error': 'Excel file not loaded'}), 500

    keyword = request.form['keyword'].lower()
    logger.info(f"Searching for keyword: {keyword}")

    results = []

    for control_id, control_data in controls_dict.items():
        control_text = str(control_data.get('Control Text', '')).lower()
        discussion = str(control_data.get('Discussion', '')).lower()

        if keyword in control_text or keyword in discussion:
            results.append({
                'id': control_id,
                'text': control_data.get('Control Text', ''),
                'discussion': control_data.get('Discussion', '')
            })

    logger.info(f"Found {len(results)} results for keyword: {keyword}")
    return jsonify(results)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)