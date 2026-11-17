import os
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Google Gemini İstemcisi (Anahtarı Render Environment'tan okur)
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

PROJECT_NAME = "İdeAI"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_bot():
    if not client:
        return jsonify({"reply": "Sistem Hatası: GEMINI_API_KEY Render paneline eklenmemiş!"}), 500

    data = request.json
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "Mesaj boş olamaz"}), 400

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=f"Senin adın {PROJECT_NAME}. HTML/CSS/JS arayüzüne sahip, kullanıcılara en ideal çözümleri sunan karizmatik bir yapay zekasın. Yanıtlarını çok uzun tutma, net ve anlaşılır ol.",
                max_output_tokens=1000,
            ),
        )
        
        ai_response = response.text.strip()
        return jsonify({"reply": ai_response})
    except Exception as e:
        return jsonify({"reply": f"Hata oluştu: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
