import os
import json
import sqlite3
import base64
import traceback
from pathlib import Path
from io import BytesIO
from PIL import Image
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

API_KEY = os.getenv("AI_MODEL_API_KEY")
PORT = int(os.getenv("PORT", 5000))
DB_PATH = Path(__file__).resolve().parent / "ecosync.db"

model = None
if API_KEY and API_KEY != "your_gemini_api_key_here":
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-3.5-flash')
        print("✅ Gemini AI Model initialized successfully.")
    except Exception as e:
        print(f"❌ Error configuring Gemini API: {e}")
else:
    print(f"⚠️ Warning: AI_MODEL_API_KEY missing or unconfigured in {env_path}")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS impact_stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  action_type TEXT, 
                  co2_saved REAL, 
                  items_sorted INTEGER,
                  eco_points INTEGER,
                  category TEXT)''')
    conn.commit()
    conn.close()

init_db()

def log_impact(action_type, co2=0.0, items=0, points=10, category="General"):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO impact_stats (action_type, co2_saved, items_sorted, eco_points, category) VALUES (?, ?, ?, ?, ?)", 
                  (action_type, co2, items, points, category))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database logging error: {e}")


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT SUM(co2_saved), SUM(items_sorted), SUM(eco_points) FROM impact_stats")
        total_row = c.fetchone()
        
        c.execute("SELECT category, COUNT(*) FROM impact_stats WHERE action_type='waste_sorted' GROUP BY category")
        breakdown_rows = c.fetchall()
        
        conn.close()
        
        categories = {row[0]: row[1] for row in breakdown_rows if row[0]}
        
        return jsonify({
            "total_co2_saved_kg": round(total_row[0] or 0.0, 2),
            "total_items_sorted": total_row[1] or 0,
            "total_eco_points": total_row[2] or 0,
            "category_breakdown": categories
        }), 200
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({"total_co2_saved_kg": 0.0, "total_items_sorted": 0, "total_eco_points": 0, "category_breakdown": {}}), 200


@app.route('/api/analyze-waste', methods=['POST'])
def analyze_waste():
    if not model:
        return jsonify({"error": "Gemini API key is missing on backend."}), 500

    try:
        data = request.get_json() or {}
        image_data = data.get('image_b64', '')
        item_text = data.get('item', '')

        prompt = """
        You are an expert environmental waste intelligence engine.
        Analyze the provided image or text description and extract deep sustainability data.
        Respond STRICTLY in valid JSON with these keys:
        - "item_name": (String - specific item identified)
        - "category": (String - Recyclable, Compostable, E-Waste, Hazardous, or Landfill Trash)
        - "materials": (Array of Strings - e.g. ["PET Plastic #1", "Aluminum Cap"])
        - "decomposition_years": (String - e.g. "450 Years in Landfill" or "2-6 Weeks")
        - "steps": (Array of 2-3 concise Strings - step-by-step preparation e.g. ["Rinse residue", "Separate cap from bottle", "Place in yellow bin"])
        - "upcycle_idea": (String - creative DIY reuse idea for this item)
        - "environmental_impact": (String - detailed eco statement on saving resources)
        - "estimated_co2_saved_kg": (Number - e.g. 0.45)
        - "eco_points": (Integer - e.g. 50)
        """

        contents = [prompt]
        if image_data:
            header, encoded = image_data.split(',', 1) if ',' in image_data else ('', image_data)
            image_bytes = base64.b64decode(encoded)
            img = Image.open(BytesIO(image_bytes))
            contents.append(img)
        elif item_text:
            contents.append(f"Item description: {item_text}")
        else:
            return jsonify({"error": "Please provide an image or text description."}), 400

        response = model.generate_content(contents)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(clean_json)
        
        co2_saved = float(result.get("estimated_co2_saved_kg", 0.3))
        points = int(result.get("eco_points", 50))
        category = result.get("category", "General")
        
        log_impact("waste_sorted", co2=co2_saved, items=1, points=points, category=category)
        return jsonify(result), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to analyze item: {str(e)}"}), 500


@app.route('/api/carbon-footprint', methods=['POST'])
def calculate_carbon():
    if not model:
        return jsonify({"error": "Gemini API key is missing on backend."}), 500

    try:
        data = request.get_json() or {}
        activity = data.get('activity', '')

        if not activity:
            return jsonify({"error": "Activity description required."}), 400

        # Note: Curly braces {{ and }} are doubled to escape Python f-string formatting
        prompt = f"""
        Analyze the carbon footprint for this activity: '{activity}'.
        Respond STRICTLY in valid JSON format with these exact keys:
        - "activity_type": (String - Travel, Home Energy, Diet, Shopping, Digital)
        - "estimated_kg_co2": (Number - total CO2 produced in kg)
        - "equivalents": {{
            "trees_needed": (Number - trees needed for 1 day to absorb this CO2),
            "car_miles": (Number - equivalent driving miles in average gas car),
            "smartphones_charged": (Number - equivalent smartphone full charges)
          }}
        - "immediate_action": (String - 1 quick thing to do today to lower this)
        - "long_term_habit": (String - 1 long-term sustainable lifestyle replacement)
        - "potential_savings_kg": (Number - CO2 saved if habit is changed)
        - "eco_points": (Integer - e.g. 35)
        """

        response = model.generate_content(prompt)
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(clean_json)
        
        potential_co2 = float(result.get("potential_savings_kg", 0.5))
        points = int(result.get("eco_points", 35))
        
        log_impact("carbon_logged", co2=potential_co2, items=0, points=points, category="Footprint")
        return jsonify(result), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to calculate footprint: {str(e)}"}), 500


if __name__ == '__main__':
    print(f"🚀 EcoSync Backend starting at http://127.0.0.1:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)