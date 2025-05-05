import os
from flask import Flask, request, jsonify, render_template
import requests
from typing import Dict, Text, Any, List
from langchain.llms import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import TextLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory

app = Flask(__name__)

# Configuration
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"  # Default Rasa URL.  Change if needed.
LLM_API_KEY = "YOUR_OPENAI_API_KEY"  # Replace with your actual OpenAI API key
DATA_PATH = "./library_data"  # Path to your library data files

# Global chatbot instance
chatbot = None

def create_library_chatbot(data_path: str, api_key: str) -> ConversationalRetrievalChain:
    """
    Creates a library chatbot using an LLM.

    Args:
        data_path: Path to the directory containing library data (e.g., .txt files).
        api_key: API key for the LLM provider (e.g., OpenAI).

    Returns:
        A ConversationalRetrievalChain instance.
    """
    os.environ["OPENAI_API_KEY"] = api_key

    # 1. Load and Process Data
    documents = []
    for file in os.listdir(data_path):
        if file.endswith(".txt"):  # Example: Load from text files
            file_path = os.path.join(data_path, file)
            loader = TextLoader(file_path)
            documents.extend(loader.load())

    # 2. Create Embeddings and Vectorstore
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(documents, embeddings)

    # 3. Initialize LLM and Memory
    llm = OpenAI(temperature=0.7)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    # 4. Create the Retrieval Chain
    qa = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
        chain_type="stuff",
    )
    return qa


def get_llm_response(query: str) -> str:
    """
    Gets a response from the LLM-powered chatbot.

    Args:
        query: The user's query.

    Returns:
        The chatbot's response.
    """
    global chatbot  # Use the global chatbot instance
    if chatbot is None:
        return "Chatbot is not initialized."
    try:
        response = chatbot({"question": query})
        return response["answer"]
    except Exception as e:
        return f"An error occurred: {e}"
    
def send_message_to_rasa(message: str) -> List[Dict[Text, Any]]:
    """
    Sends a message to the Rasa chatbot and returns the response.

    Args:
        message: The user's message.

    Returns:
        A list of responses from Rasa.
    """
    payload = {"sender": "user", "message": message}
    try:
        response = requests.post(RASA_URL, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Rasa: {e}")
        return [{"text": "Sorry, I'm having trouble connecting to the chatbot."}]
    except ValueError:
        print("Error: Rasa response was not valid JSON")
        return [{"text": "Sorry, I'm having trouble understanding the response."}]

def get_combined_response(user_message: str) -> str:
    """
    Gets a combined response from Rasa and the LLM.

    Args:
        user_message: The user's message.

    Returns:
        A combined response string.
    """
    rasa_response = send_message_to_rasa(user_message)
    llm_response = get_llm_response(user_message)
    combined_response = ""
    for r in rasa_response:
      if "text" in r:
        combined_response += r["text"] + " "
    combined_response += llm_response
    return combined_response

@app.route("/")
def index() -> str:
    """
    Renders the main chat interface.
    """
    return render_template("index.html") 

@app.route("/chat", methods=["POST"])
def chat() -> jsonify:
    """
    Handles user messages, sends them to Rasa and the LLM, and returns the combined response.
    """
    message = request.json["message"]
    response = get_combined_response(message)
    return jsonify({"response": response})

@app.route("/init_llm")
def init_llm() -> jsonify:
    """
    Initializes the LLM chatbot.  This is a separate endpoint, so you can initialize
    the LLM when the server starts, or later on demand.
    """
    global chatbot
    try:
      
        if not os.path.exists(DATA_PATH):
            os.makedirs(DATA_PATH)
            with open(os.path.join(DATA_PATH, "book1.txt"), "w") as f:
                f.write(
                    "Title: The Art of Programming\nAuthor: John Smith\nKeywords: programming, algorithms, data structures"
                )
            with open(os.path.join(DATA_PATH, "book2.txt"), "w") as f:
                f.write(
                    "Title: Introduction to Databases\nAuthor: Jane Doe\nKeywords: databases, SQL, data modeling"
                )
        chatbot = create_library_chatbot(DATA_PATH, LLM_API_KEY)
        return jsonify({"status": "LLM Chatbot Initialized"})
    except Exception as e:
        return jsonify({"status": "LLM Chatbot Initialization Failed", "error": str(e)})
    
if __name__ == "__main__":
    # Initialize the LLM when the app starts
    init_llm() # Initialize the LLM.
    app.run(debug=True)
  
