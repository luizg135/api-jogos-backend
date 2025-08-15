# routes/game_routes.py
from flask import Blueprint, jsonify
from services import game_service
import traceback

game_bp = Blueprint('games', __name__)

@game_bp.route('/data')
def get_all_game_data():
    try:
        data = game_service.get_game_data()
        return jsonify(data)
    except Exception as e:
        error_details = traceback.format_exc()
        return jsonify({
            "error": "Não foi possível obter os dados dos jogos.",
            "detalhes_tecnicos": str(e),
            "traceback": error_details
        }), 500