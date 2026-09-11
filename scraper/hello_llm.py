import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel(os.environ["GEMINI_MODEL"])

response = model.generate_content("Reply with exactly the word: ready")

print(response.text)