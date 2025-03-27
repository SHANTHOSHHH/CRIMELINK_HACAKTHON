from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import openai
from neo4j import GraphDatabase 
import requests
from werkzeug.utils import secure_filename



app = Flask(__name__)
CORS(app)  # Allow frontend interactiaons

db_uri = "bolt://localhost:7687"
db_user = "neo4j"
db_password = "Sandy@61"
database_name = "structured"
driver = GraphDatabase.driver(db_uri, auth =(db_user, db_password))

UPLOAD_FOLDER = "case_images"  # Folder for images
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/test_db', methods=['GET'])
def test_db():
    with driver.session(database=database_name) as session:
        result = session.run("RETURN 'Neo4j connected ' AS message")
        return jsonify({"status": result.single()["message"]})
    


@app.route('/Home')
def home():
    """Serve the main UI page."""
    return render_template('index.html')

@app.route('/Search', methods=['GET'])
def search_cases():
    """Search cases based on a query."""
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({"error": "Empty search query"}), 400

    conn = sqlite3.connect('crime_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE LOWER(case_title) LIKE ?", ('%' + query + '%',))
    results = cursor.fetchall()
    conn.close()

    if results:
        cases = [{"id": r[0], "title": r[1], "description": r[2], "status": r[3]} for r in results]
        return jsonify({"cases": cases})
    else:
        return jsonify({"message": "No cases found"}), 404

def create_constraints():
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.FIR_number IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Suspect) REQUIRE s.name IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (o:Officer) REQUIRE o.name IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ct:CrimeType) REQUIRE ct.name IS UNIQUE;")

create_constraints()
def execute_query(query, params={}):
    with driver.session() as session:
        return session.run(query, params)

### 1️⃣ API: Add Case Text Data to Neo4j ###
@app.route("/add_case", methods=["POST"])
def add_case():
    try:
        data = request.json  # Get JSON data from frontend
        case_id = str(hash(data["caseTitle"]))  # Generate Unique Case ID

        # Add case details to Neo4j
        
        query = """
            CREATE (c:Case {
                id: $id, suspectName: $suspectName, fatherName: $fatherName, motherName: $motherName, 
                suspectAge: $suspectAge, suspectGender: $suspectGender, suspectDOB: $suspectDOB,
                AadhaarNumber: $AadhaarNumber, PhoneNumber: $PhoneNumber, modusOperandi: $modusOperandi,
                caseTitle: $caseTitle, BailDetails: $BailDetails, Firnumber: $Firnumber,
                caseDetails: $caseDetails, familyTies: $familyTies, evidenceCollected: $evidenceCollected,
                crimeType: $crimeType, wantedLevel: $wantedLevel, officerName: $officerName,
                caseStatus: $caseStatus, suspectPhoto: '', evidencePhoto: '', crimeScenePhoto: ''
            })
            """
        execute_query(query, {"id": case_id, **data})


        return jsonify({"message": "Case added successfully!", "case_id": case_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


### 2️⃣ API: Upload Images & Store Paths ###
@app.route("/upload_case_images", methods=["POST"])
def upload_case_images():
    try:
        case_id = request.form["id"]  # Get Case ID
        file = request.files["image"]  # Get Image File
        image_type = request.form["image_type"]  # Ensure this is correctly received

        if not file or not image_type:
            return jsonify({"error": "No image uploaded or invalid image type"}), 400

        # Secure filename and save image
        filename = f"{case_id}_{secure_filename(file.filename)}"
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(image_path)

        # Ensure `image_type` matches exactly
        valid_types = {"suspectPhoto", "evidencePhoto", "crimeScenePhoto"}
        if image_type not in valid_types:
            return jsonify({"error": "Invalid image type"}), 400

        # Store relative path in Neo4j
        db_image_path = f"{UPLOAD_FOLDER}/{filename}"
        query = f"""
        MATCH (c:Case {{id: $id}})
        SET c.{image_type} = $image_path
        """
        execute_query(query, {"id": case_id, "image_path": db_image_path})

        return jsonify({"message": f"{image_type} uploaded successfully!", "image_path": db_image_path}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



### 3️⃣ API: Get Case Details by ID ###
@app.route("/get_case/<case_id>", methods=["GET"])
def get_case(case_id):
    try:
        with driver.session() as session:
            query = "MATCH (c:Case {id: $id}) RETURN c"
            result = session.run(query, id=case_id)
            case_data = result.single()

            if not case_data:
                return jsonify({"error": "Case not found"}), 404

            return jsonify(case_data["c"]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Close Neo4j driver when the app stops
@app.teardown_appcontext
def close_driver(error):
    if driver:
        driver.close()


    
@app.route('/chat', methods=['POST'])
def chat():
    """Process user message and return chatbot response."""
    data = request.get_json()
    user_message = data.get("message", "").lower()

    # Simple rule-based responses
    responses = {
        "hello": "Hello! How can I assist you today?",
        "how are you": "I'm just a bot, but I'm here to help!",
        "case details": "Please provide the case ID to fetch details.",
        "search case": "Enter the suspect's name or case title to search.",
        "goodbye": "Goodbye! Stay safe.",
    }

    # Default response if no keyword matches
    bot_response = responses.get(user_message, "I'm not sure how to answer that. Try asking something else.")

    return jsonify({"response": bot_response})


@app.route('/history')
def history():
    """Serve the search history page."""
    return render_template('history.html')

@app.route('/reports')
def reports():
    """Serve the reports page."""
    return render_template('reports.html')

@app.route('/analytics')
def analytics():
    """Serve the crime analytics page."""
    return render_template('analytics.html')


# ----------------- RUN THE APP -----------------
if __name__ == '__main__':
    app.run(debug=True)


