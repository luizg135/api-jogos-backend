# config.py
import os

class Config:
    # ‼️‼️‼️ COLE A URL DA SUA NOVA PLANILHA DE JOGOS AQUI ‼️‼️‼️
    GAME_SHEET_URL = os.environ.get(
        'GAME_SHEET_URL',
        "https://docs.google.com/spreadsheets/d/1SwSbLoWGecq-rfTmzgTYjBvmDfqRGF1OV7KX7QxGR_o/edit?usp=sharing"
    )
    CACHE_DURATION_SECONDS = 300  # 5 minutos