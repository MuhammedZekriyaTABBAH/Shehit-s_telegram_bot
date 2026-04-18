from flask import Flask
import threading
import os
import subprocess

app = Flask(__name__)

@app.route('/')
def home():
    return "البوت شغال! ✅"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    """تشغيل البوت في خلفية"""
    os.system("python bot.py")

if __name__ == '__main__':
    # تشغيل البوت في thread منفصل
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # تشغيل خادم Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)