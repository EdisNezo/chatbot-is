import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

# Import the main ELearningCourseGenerator class
from modules.elearning_generator import ELearningCourseGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add command-line argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description='E-Learning Course Generator for Information Security')
    parser.add_argument('--reindex', action='store_true', help='Reindex all documents in the documents directory')
    return parser.parse_args()

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'elearning-generator-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Create the ELearningCourseGenerator instance
generator = ELearningCourseGenerator(config_path="./config.json")

# Store active conversations
active_conversations = {}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/start-conversation', methods=['POST'])
def start_conversation():
    """API endpoint to start a new conversation"""
    session_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(hash(request.remote_addr))[:5]
    
    try:
        # Initialize the generator if not already done
        if not hasattr(generator, 'dialog_manager') or generator.dialog_manager is None:
            generator.setup()
        
        # Start the conversation
        first_question = generator.start_conversation()
        
        # Store the session
        active_conversations[session_id] = {
            'messages': [{"role": "assistant", "content": first_question}],
            'script_generated': False
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': first_question
        })
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """API endpoint to send a message in an existing conversation"""
    data = request.json
    session_id = data.get('session_id')
    user_input = data.get('message')
    
    if not session_id or session_id not in active_conversations:
        return jsonify({
            'success': False,
            'error': 'Invalid session ID'
        }), 400
    
    if not user_input:
        return jsonify({
            'success': False,
            'error': 'Message cannot be empty'
        }), 400
    
    try:
        # Add user message to conversation history
        active_conversations[session_id]['messages'].append({"role": "user", "content": user_input})
        
        # Process user input with detailed error handling
        try:
            bot_response = generator.process_user_input(user_input)
            
            # Ensure bot_response is a string
            if not isinstance(bot_response, str):
                logger.error(f"Bot response is not a string: {type(bot_response)}")
                bot_response = f"Es ist ein Fehler aufgetreten. Die Antwort hat ein unerwartetes Format: {type(bot_response)}"
                
        except Exception as inner_e:
            logger.error(f"Error in process_user_input: {inner_e}")
            bot_response = "Entschuldigung, bei der Verarbeitung Ihrer Nachricht ist ein Fehler aufgetreten."
        
        # Add bot response to conversation history
        active_conversations[session_id]['messages'].append({"role": "assistant", "content": bot_response})
        
        # Check if script was generated
        if "Hier ist der entworfene E-Learning-Kurs" in bot_response:
            active_conversations[session_id]['script_generated'] = True
        
        return jsonify({
            'success': True,
            'message': bot_response,
            'script_generated': active_conversations[session_id]['script_generated']
        })
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/save-script', methods=['POST'])
def save_script():
    """API endpoint to save the generated script"""
    data = request.json
    session_id = data.get('session_id')
    format_type = data.get('format', 'txt')
    
    if not session_id or session_id not in active_conversations:
        return jsonify({
            'success': False,
            'error': 'Invalid session ID'
        }), 400
    
    if not active_conversations[session_id]['script_generated']:
        return jsonify({
            'success': False,
            'error': 'No script has been generated for this session'
        }), 400
    
    try:
        # Save the script
        script_path = generator.save_generated_script(format=format_type)
        filename = os.path.basename(script_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': f'/api/download/{filename}'
        })
    except Exception as e:
        logger.error(f"Error saving script: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """API endpoint to download a generated script"""
    return send_from_directory(os.path.abspath(generator.config["output_dir"]), filename, as_attachment=True)

@app.route('/result/<session_id>')
def view_result(session_id):
    """Render the result page with the full generated script"""
    if session_id not in active_conversations or not active_conversations[session_id]['script_generated']:
        return render_template('index.html')
    
    try:
        # Get format preference from query parameters, default to txt
        format_type = request.args.get('format', 'txt')
        
        script = generator.dialog_manager.generate_script()
        
        # Get script metadata
        script_title = script.get('title', 'E-Learning-Kurs zur Informationssicherheit')
        script_description = script.get('description', '')
        
        # Get organization and audience from context info
        organization = generator.dialog_manager.conversation_state["context_info"].get(
            "Für welche Art von Organisation erstellen wir den E-Learning-Kurs (z.B. Krankenhaus, Bank, Behörde)?", "")
        audience = generator.dialog_manager.conversation_state["context_info"].get(
            "Welche Mitarbeitergruppen sollen geschult werden?", "")
        
        # Get current date
        created_date = datetime.now().strftime("%d.%m.%Y")
        
        # Save the script to make it available for download
        script_path = generator.save_generated_script(format=format_type)
        filename = os.path.basename(script_path)
        download_url = f'/api/download/{filename}'
        
        # Return the rendered template
        return render_template(
            'result.html',
            script_title=script_title,
            script_description=script_description,
            organization=organization,
            audience=audience,
            created_date=created_date,
            sections=script['sections'],
            format=format_type,
            download_url=download_url
        )
        
    except Exception as e:
        logger.error(f"Error generating result page: {e}")
        return render_template('index.html')

@app.route('/api/preview-script', methods=['POST'])
def preview_script():
    """API endpoint to preview the generated script"""
    data = request.json
    session_id = data.get('session_id')
    format_type = data.get('format', 'txt')
    
    if not session_id or session_id not in active_conversations:
        return jsonify({
            'success': False,
            'error': 'Invalid session ID'
        }), 400
    
    if not active_conversations[session_id]['script_generated']:
        return jsonify({
            'success': False,
            'error': 'No script has been generated for this session'
        }), 400
    
    try:
        # Get script preview based on format
        if format_type == 'html':
            script_content = generator.dialog_manager.generate_html_script()
            content_type = 'html'
        else:
            script_content = generator.dialog_manager.get_script_summary()
            content_type = 'text'
        
        return jsonify({
            'success': True,
            'content': script_content,
            'content_type': content_type
        })
    except Exception as e:
        logger.error(f"Error generating script preview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reindex-documents', methods=['POST'])
def reindex_documents():
    """API endpoint to reindex documents"""
    try:
        doc_count = generator.reindex_documents()
        return jsonify({
            'success': True,
            'message': f"{doc_count} documents successfully reindexed!"
        })
    except Exception as e:
        logger.error(f"Error reindexing documents: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reset-conversation', methods=['POST'])
def reset_conversation():
    """API endpoint to reset the conversation"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in active_conversations:
        return jsonify({
            'success': False,
            'error': 'Invalid session ID'
        }), 400
    
    try:
        # Reset the conversation
        generator.reset_conversation()
        
        # Start a new conversation
        first_question = generator.start_conversation()
        
        # Update the session
        active_conversations[session_id] = {
            'messages': [{"role": "assistant", "content": first_question}],
            'script_generated': False
        }
        
        return jsonify({
            'success': True,
            'message': first_question
        })
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """API endpoint to get generator statistics"""
    try:
        return jsonify({
            'success': True,
            'generated_scripts_count': generator.generated_scripts_count
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@app.route('/api/vectordb-stats', methods=['GET'])
def get_vectordb_stats():
    """API endpoint to get vector database statistics"""
    try:
        # Check if vectorstore exists
        if not hasattr(generator, 'vector_store_manager') or generator.vector_store_manager.vectorstore is None:
            return jsonify({
                'success': False,
                'error': 'Vector database not initialized'
            }), 400
            
        # Get collection info
        collection = generator.vector_store_manager.vectorstore._collection
        
        # Get count of items
        count = collection.count()
        
        # Try to get additional metadata
        try:
            # Get schema information
            schema = collection.schema
            embedding_size = getattr(schema, 'embedding_size', 'Unknown')
            
            # Get some sample document IDs
            sample_ids = []
            if count > 0:
                sample_ids = collection.get(limit=5)['ids']
        except Exception as e:
            schema = None
            embedding_size = 'Error retrieving'
            sample_ids = []
            
        return jsonify({
            'success': True,
            'stats': {
                'document_count': count,
                'embedding_size': embedding_size,
                'sample_ids': sample_ids,
                'database_path': generator.config["vectorstore_dir"]
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving vector database stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@app.route('/api/llm-status', methods=['GET'])
def get_llm_status():
    """API endpoint to check if the LLM is accessible"""
    try:
        # Check if the LLM manager exists
        if not hasattr(generator, 'llm_manager'):
            return jsonify({
                'success': False,
                'error': 'LLM Manager not initialized',
                'status': 'unavailable'
            })
            
        # Try a simple generation with the LLM
        test_prompt = "Gib mir nur das Wort 'Funktioniert' zurück, nicht mehr."
        try:
            start_time = datetime.now()
            response = generator.llm_manager.llm(test_prompt)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Check if the response contains expected text
            if 'funktioniert' in response.lower():
                return jsonify({
                    'success': True,
                    'status': 'available',
                    'model': generator.config["model_name"],
                    'response_time': response_time,
                    'response': response[:50]  # Just return the first 50 chars as sample
                })
            else:
                # If response doesn't contain expected text, LLM might be responding but incorrectly
                return jsonify({
                    'success': True,
                    'status': 'degraded',
                    'model': generator.config["model_name"],
                    'response_time': response_time,
                    'response': response[:50]
                })
        except Exception as e:
            # LLM is unavailable
            return jsonify({
                'success': False,
                'error': str(e),
                'status': 'unavailable',
                'model': generator.config["model_name"]
            })
    
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'error'
        }), 500    

# WebSocket for real-time updates
@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

def create_default_config():
    """Create a default configuration file if it doesn't exist"""
    config_path = "./config.json"
    
    if not os.path.exists(config_path):
        default_config = {
            "documents_dir": "./data/documents",
            "vectorstore_dir": "./data/vectorstore",
            "output_dir": "./data/output",
            "model_name": "llama3.1",  # Changed from llama3:8b to llama3.1
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        
        # Create directories
        for dir_path in [default_config["documents_dir"], 
                        default_config["vectorstore_dir"], 
                        default_config["output_dir"]]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Write config file
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default configuration at {config_path}")

if __name__ == '__main__':
    # Parse command-line arguments
    args = parse_arguments()
    
    # Create default config if not exists
    create_default_config()
    
    # Handle reindexing command if specified
    if args.reindex:
        try:
            # Make sure the generator is set up
            if not hasattr(generator, 'dialog_manager') or generator.dialog_manager is None:
                generator.setup()
            
            # Perform reindexing
            print("Starting document reindexing...")
            doc_count = generator.reindex_documents()
            print(f"Reindexing completed successfully. {doc_count} documents indexed.")
            
            # Exit after reindexing completes
            import sys
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error during reindexing: {e}")
            print(f"Error during reindexing: {e}")
            import sys
            sys.exit(1)
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 8000))
    
    # Start the server (only if not reindexing)
    socketio.run(app, host='0.0.0.0', port=port, debug=False)