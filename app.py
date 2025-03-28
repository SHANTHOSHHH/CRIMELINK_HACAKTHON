import os
import sqlite3
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase 
from werkzeug.utils import secure_filename
from llama_cpp import Llama
import sys
import torch
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Function Definitions
def load_mistral_model(model_path):
    """
    Comprehensive Mistral model loading with advanced error handling
    
    Args:
        model_path (str): Full path to the Mistral model file
    
    Returns:
        Llama model or None if loading fails
    """
    try:
        # Validate model file exists and is readable
        if not os.path.exists(model_path):
            logging.error(f"Model file not found: {model_path}")
            return None
        
        if not os.access(model_path, os.R_OK):
            logging.error(f"Model file is not readable: {model_path}")
            return None
        
        # System diagnostics
        logging.info(f"Python Version: {sys.version}")
        logging.info(f"Platform: {sys.platform}")
        logging.info(f"Torch Version: {torch.__version__}")
        logging.info(f"CUDA Available: {torch.cuda.is_available()}")
        
        # Advanced model loading with comprehensive parameters
        model = Llama(
            model_path=model_path,
            n_ctx=2048,          # Context window size
            n_batch=512,          # Batch size
            n_gpu_layers=-1,      # Use all GPU layers if available
            verbose=True          # Detailed logging
        )
        
        logging.info("Mistral model loaded successfully")
        return model
    
    except Exception as e:
        logging.error(f"Detailed Model Loading Error: {e}")
        logging.error(f"Error Type: {type(e)}")
        logging.error(f"Error Args: {e.args}")
        
        # Additional system information for debugging
        logging.info(f"OS: {platform.platform()}")
        logging.info(f"Processor: {platform.processor()}")
        
        return None

def initialize_neo4j_driver():
    """Initialize Neo4j driver with comprehensive error handling."""
    global neo4j_driver
    try:
        neo4j_driver = GraphDatabase.driver(
            DB_CONFIG['neo4j']['uri'], 
            auth=(DB_CONFIG['neo4j']['user'], DB_CONFIG['neo4j']['password'])
        )
        logger.info("Neo4j driver initialized successfully")
        return neo4j_driver
    except Exception as e:
        logger.error(f"Neo4j driver initialization failed: {e}")
        return None

def create_neo4j_constraints(driver):
    """Create database constraints in Neo4j."""
    try:
        with driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.FIR_number IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Suspect) REQUIRE s.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Officer) REQUIRE o.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (ct:CrimeType) REQUIRE ct.name IS UNIQUE"
            ]
            for constraint in constraints:
                session.run(constraint)
        logger.info("Neo4j constraints created successfully")
    except Exception as e:
        logger.error(f"Constraint creation failed: {e}")

def execute_neo4j_query(driver, query, params=None):
    """Execute Neo4j query with robust error handling."""
    try:
        with driver.session() as session:
            result = session.run(query, params or {})
            return result
    except Exception as e:
        logger.error(f"Neo4j query execution failed: {e}")
        return None

# Create Flask application
app = Flask(__name__)
CORS(app)  # Allow frontend interactions

# Configuration Constants
DB_CONFIG = {
    'neo4j': {
        'uri': "bolt://localhost:7687",
        'user': "neo4j",
        'password': "Sandy@61",
        'database': "structured"
    }
}

# Model and Upload Configuration
MODEL_PATH = os.path.normpath("D:\\mistral\\models\\mistral-7b-instruct-v0.2.Q3_K_M.gguf")
UPLOAD_FOLDER = "case_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Global variables for database and language model
neo4j_driver = None
global_llm = None

def initialize_application():
    """Initialize all required resources."""
    global neo4j_driver, global_llm
    
    # Initialize Neo4j Driver
    neo4j_driver = initialize_neo4j_driver()
    
    # Load Language Model
    global_llm = load_mistral_model(MODEL_PATH)
    
    # Create Constraints
    if neo4j_driver:
        create_neo4j_constraints(neo4j_driver)

# Call initialization on import
initialize_application()

# Flask Routes
@app.route('/')
def home():
    """Serve the main UI page."""
    return render_template('index.html')

@app.route('/test_db', methods=['GET'])
def test_database_connection():
    """Test Neo4j database connection."""
    try:
        result = execute_neo4j_query(neo4j_driver, "RETURN 'Neo4j connected' AS message")
        if result:
            return jsonify({"status": result.single()["message"]})
        return jsonify({"error": "Connection test failed"}), 500
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/add_case', methods=["POST"])
def add_case():
    """Add case to Neo4j database."""
    try:
        data = request.json
        case_id = str(hash(data.get("caseTitle", "")))
        
        query = """
        CREATE (c:Case {
            id: $id, 
            suspectName: $suspectName, 
            fatherName: $fatherName, 
            motherName: $motherName, 
            suspectAge: $suspectAge, 
            suspectGender: $suspectGender, 
            suspectDOB: $suspectDOB,
            AadhaarNumber: $AadhaarNumber, 
            PhoneNumber: $PhoneNumber, 
            modusOperandi: $modusOperandi, 
            caseTitle: $caseTitle, 
            BailDetails: $BailDetails, 
            Firnumber: $Firnumber,
            caseDetails: $caseDetails, 
            familyTies: $familyTies, 
            evidenceCollected: $evidenceCollected, 
            crimeType: $crimeType, 
            wantedLevel: $wantedLevel, 
            officerName: $officerName,
            caseStatus: $caseStatus, 
            suspectPhoto: '', 
            evidencePhoto: '', 
            crimeScenePhoto: ''
        })
        """
        
        result = execute_neo4j_query(neo4j_driver, query, {
            "id": case_id, 
            **data
        })
        
        return jsonify({
            "message": "Case added successfully!", 
            "case_id": case_id
        }), 200
    
    except Exception as e:
        logger.error(f"Case addition failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def process_chat():
    """Process user message and generate response."""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip().lower()
        
        if not user_message:
            return jsonify({"response": "Empty message received."}), 400
        
        # Validate language model is loaded
        if not global_llm:
            return jsonify({
                "response": "Language model unavailable. Please contact support."
            }), 500
        
        # Generate response
        response = global_llm(f"Extract intent: {user_message}")
        response_text = response["choices"][0]["text"]
        
        return jsonify({"response": response_text})
    
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        return jsonify({
            "response": "An error occurred processing your request."
        }), 500

# Application Cleanup
@app.teardown_appcontext
def close_database_connection(exception):
    """Close Neo4j driver when application ends."""
    if neo4j_driver:
        neo4j_driver.close()
        logger.info("Neo4j driver closed successfully")

# Main Execution Block
if __name__ == '__main__':
    try:
        app.run(
            host="0.0.0.0", 
            port=5000, 
            debug=True, 
            threaded=True
        )
    except Exception as e:
        logger.critical(f"Application startup failed: {e}")