#!/bin/bash
echo "Initializing E-Learning Course Generator on RunPod"

# Install required packages 
pip install -r requirements.txt

# Create necessary directories with proper permissions
mkdir -p ./data/documents
mkdir -p ./data/vectorstore
mkdir -p ./data/output

chmod -R 777 ./data

# Create the fix files
cat > fix_dialog_manager.py << 'EOL'
def fix_dialog_manager():
    """
    Update the generate_retrieval_queries function in dialog_manager.py
    """
    file_path = "modules/dialog_manager.py"
    
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Fix the missing return statement in generate_retrieval_queries
    if "def generate_retrieval_queries" in content and "return queries" not in content:
        # Find the function definition
        import re
        pattern = r"(def generate_retrieval_queries.*?queries\.extend\(specific_queries\)\s*)(    \n|$)"
        replacement = r"\1\n    return queries\n\2"
        
        # Apply the fix
        fixed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Write the fixed content
        with open(file_path, 'w') as file:
            file.write(fixed_content)
        
        print("Fixed dialog_manager.py - added missing return statement")
    else:
        print("No fix needed for dialog_manager.py or fix already applied")
EOL

cat > fix_llm_manager.py << 'EOL'
def fix_llm_manager():
    """
    Add better error handling to LLM Manager
    """
    file_path = "modules/llm_manager.py"
    
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Add a DummyLLM class for fallback
    if "class DummyLLM" not in content:
        dummy_llm_code = """
# Fallback model for when Ollama is not available
class DummyLLM:
    \"\"\"A simple fallback LLM that returns predefined responses\"\"\"
    
    def __init__(self):
        logger.warning("Using DummyLLM due to initialization error with real LLM")
    
    def __call__(self, prompt):
        \"\"\"Simple implementation that returns a predefined response\"\"\"
        if "frage" in prompt.lower() or "question" in prompt.lower():
            return "Können Sie mir mehr über Ihre Organisation und Ihre Informationssicherheitsanforderungen erzählen?"
        elif "inhalt" in prompt.lower() or "content" in prompt.lower():
            return "Dies ist ein Beispielinhalt für den E-Learning-Kurs zur Informationssicherheit."
        else:
            return "Ich bin ein Hilfeassistent für Informationssicherheit. Wie kann ich Ihnen helfen?"
"""
        
        # Insert the dummy class before the LLMManager class
        if "class LLMManager" in content:
            fixed_content = content.replace("class LLMManager", dummy_llm_code + "\nclass LLMManager")
            
            # Also fix the __init__ method to use the DummyLLM fallback
            if "def __init__(self, model_name" in fixed_content:
                init_pattern = r"(def __init__.*?self\.llm = Ollama\(.*?\))(.*?)(# Define standard prompts)"
                init_replacement = r"\1\n        # Test the LLM connection\n        try:\n            test_result = self.llm('Test')\n            logger.info(f'LLM initialized successfully with model {model_name}')\n        except Exception as e:\n            logger.error(f'Error connecting to Ollama: {e}')\n            logger.warning('Falling back to dummy LLM. Check if Ollama is running.')\n            self.llm = DummyLLM()\2\3"
                
                import re
                fixed_content = re.sub(init_pattern, init_replacement, fixed_content, flags=re.DOTALL)
            
            # Write the fixed content
            with open(file_path, 'w') as file:
                file.write(fixed_content)
            
            print("Fixed llm_manager.py - added DummyLLM for fallback")
        else:
            print("Could not find LLMManager class in llm_manager.py")
    else:
        print("No fix needed for llm_manager.py or fix already applied")
EOL

echo "Initialization completed. Run ./startup.sh to start the application."