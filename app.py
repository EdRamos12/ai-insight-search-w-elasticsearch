from elasticsearch import Elasticsearch
from flask import Flask, jsonify, make_response, render_template, request, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from groq import Groq
load_dotenv()

app = Flask(__name__)

CORS(app)

GROQ_API_KEY=os.environ.get("GROQ_API_KEY")

client_el = Elasticsearch(os.environ.get('ELASTICSEARCH_URI'), 
    basic_auth=(os.environ.get('ELASTICSEARCH_USER'), 
        os.environ.get('ELASTICSEARCH_PASSWORD'))
)

client_llm = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def get_completion(prompt, docs): 
    query = f"""
    TOP DOCUMENTS FOR USERS QUESTION: 
    
    {docs}
    
    ORIGINAL USER'S QUESITON: {prompt}
    """
    
    print(f"Token amount: {len(query)}")
    
    message = client_llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            { "role": "system", "content": """Your objective is to answer 
                the user's question based on the documents retrieved from 
                the prompt. If you don't know the answer or it's missing 
                from the documents, CLARIFY it to the user and don't make
                up any inexistent information outside of the documents 
                provided, and don't mention it. 
                Only prompt your answer, and on the end of your
                answer, ALWAYS provide the _id from the document(s) that most fits the
                user's question and your answer (example: "_id:12345", 
                "_id:12345,678891,234567"). 
                There can be multiple answers to the user's question. 
                Don't include [...] on your answers. Detail the
                items (example: including the director, synopsys, writter, 
                main plot, etc.) on what's written on the documents. Don't use 
                italics or bold text.
                
                PROMPT EXAMPLE:
                
                TOP DOCUMENTS FOR USERS QUESTION: 
                
                {
                    "content_model": "wikitext",
                    "opening_text": "Before Sunset is a 2004 sequel to the 1995 romantic drama film Before Sunrise. Directed by Richard Linklater. Written by Richard Linklater, Ethan Hawke, Julie Delpy, and Kim Krizan. What if you had a second chance with the one that got away? (taglines)",
                    "wiki": "enwikiquote",
                    "auxiliary_text": [
                        "Wikipedia"
                    ],
                }
                {
                    "content_model": "wikitext",
                    "opening_text": "Dedication is a 2007 romantic dramedy about a misogynistic children's book author who is forced to work closely with a female illustrator instead of his long-time collaborator and only friend. Directed by Justin Theroux. Written by David Bromberg. With each moment we write our story.",
                    "wiki": "enwikiquote",
                    "auxiliary_text": [
                        "Wikipedia",
                        "This film article is a stub. You can help out with Wikiquote by expanding it!"
                    ],
                }
                
                ORIGINAL USER'S QUESITON: Are there any romantic drama written before 2006?
                
                YOUR ANSWER:
                
                There is Before Sunset, a 2004 sequel to the 1995 romantic drama film called Before Sunrise. Written by [...]
                
                _id:100090
                """ },
            {
                "role": "user",
                "content": query
            }
        ]
    )
        
    return {"message": message.choices[0].message.content, "docs": docs}

@app.route("/", methods=['POST', 'GET']) 
def query_view(): 
    if request.method == 'POST': 
        prompt = request.json['prompt'] 
        
        el_resp = client_el.search(index='enwikiquote_vectorized', source={
            "excludes": [ "source_text", "text", "text_embedding" ]
        }, query={
            "sparse_vector": {
                "field": "text_embedding",
                "inference_id": "my-elser-model",
                "query": prompt
            }
        })
        
        response = get_completion(prompt, el_resp["hits"]["hits"]) 
  
        return jsonify({'response': response["message"], "docs": response["docs"]}) 
    return make_response(send_from_directory(".", path="index.html"))

if __name__ == "__main__":
  port = int(os.environ.get('PORT', 5000))
  app.run(host="0.0.0.0", port=port)