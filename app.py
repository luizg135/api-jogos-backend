# app.py
from flask import Flask
from flask_cors import CORS
from routes.game_routes import game_bp # Importa o novo blueprint

app = Flask(__name__)
CORS(app) # Habilita CORS para permitir acesso do frontend

# Registra o blueprint dos jogos com o prefixo /api/games
app.register_blueprint(game_bp, url_prefix='/api/games')

@app.route('/')
def index():
    return "API de Jogos está no ar! Acesse /api/games/data"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)