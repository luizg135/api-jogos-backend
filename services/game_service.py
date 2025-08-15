import pandas as pd
import requests
import re
import json
from io import BytesIO
from datetime import datetime, timedelta
from config import Config
import numpy as np

_cache = { "data": None, "last_fetched": None }

# --- Funções de Limpeza de Dados ---

def clean_currency(value):
    """Limpa e converte valores monetários."""
    if pd.isna(value): return 0.0
    try:
        # Remove "R$", espaços, e troca a vírgula decimal por ponto
        value_str = str(value).replace('R$', '').strip().replace(',', '.')
        return float(value_str)
    except (ValueError, TypeError):
        return 0.0

def clean_hours(value):
    """Extrai o número de horas de uma string."""
    if pd.isna(value): return 0
    try:
        # Extrai apenas os números da string (ex: "1000 horas" -> 1000)
        value_str = str(value)
        numbers = re.findall(r'\d+', value_str)
        return int(numbers[0]) if numbers else 0
    except (ValueError, TypeError, IndexError):
        return 0

def clean_rating(value):
    """Limpa e converte a nota para um número."""
    if pd.isna(value): return None # Mantém nulo se não houver nota
    try:
        # Troca vírgula por ponto e converte para float
        return float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        return None

def derive_status(row):
    """Define o status do jogo baseado em outras colunas, com prioridade para Platina."""
    if pd.notna(row['Abandonado?']) and 'Sim' in str(row['Abandonado?']):
        return 'Abandonado'
    # --- CORREÇÃO DE LÓGICA ---
    # A verificação de Platina agora vem ANTES de Finalizado.
    if pd.notna(row['Platinado?']) and 'Sim' in str(row['Platinado?']):
        return 'Platinado'
    if pd.notna(row['Terminado em']) or (pd.notna(row['Conclusão']) and '100' in str(row['Conclusão'])):
        return 'Finalizado'
    # --- FIM DA CORREÇÃO ---
    if pd.notna(row['Início em']):
        return 'Jogando'
    return 'Na Fila' # Backlog

def _fetch_and_process_data():
    """Busca e processa os dados da planilha de jogos."""
    print(f"Buscando dados da planilha de jogos... ({datetime.now()})")
    try:
        sheet_id = Config.GAME_SHEET_URL.split('/d/')[1].split('/')[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
        
        response = requests.get(csv_url, timeout=15)
        response.raise_for_status()

        df = pd.read_csv(BytesIO(response.content), header=1, encoding='utf-8')
        
        # Define os nomes das colunas conforme sua planilha (13 colunas de B a N)
        colunas = [
            'Nome', 'Plataforma', 'Nota', 'Preço', 'Estilo', 'Adquirido em', 
            'Início em', 'Terminado em', 'Conclusão', 'Tempo de Jogo', 
            'Conquistas Obtidas', 'Platinado?', 'Abandonado?'
        ]
        # Pega as colunas de B em diante
        df = df.iloc[:, 1:14]
        df.columns = colunas

        # Limpeza e transformação dos dados
        df.dropna(subset=['Nome'], inplace=True) # Remove linhas sem nome de jogo
        df['Preço'] = df['Preço'].apply(clean_currency)
        df['Tempo de Jogo'] = df['Tempo de Jogo'].apply(clean_hours)
        df['Nota'] = df['Nota'].apply(clean_rating)
        
        # Converte datas, tratando erros
        for col in ['Adquirido em', 'Início em', 'Terminado em']:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')

        # Deriva a coluna "Status" com base na nossa lógica
        df['Status'] = df.apply(derive_status, axis=1)

        # --- Cálculos das Estatísticas ---
stats = {
    'total_jogos': len(df),
    'total_horas_jogadas': int(df['Tempo de Jogo'].sum()),
    'custo_total_biblioteca': float(df['Preço'].sum()),
    'media_notas': round(df['Nota'].mean(), 2) if df['Nota'].notna().any() else 0,
    'total_finalizados': int((df['Status'] == 'Finalizado').sum()),
    'total_platinados': int(df[df['Platinado?'] == 'Sim']['Platinado?'].count()),
    'total_na_fila': int((df['Status'] == 'Na Fila').sum()) 
}     
        
        # --- Lógica para Múltiplos Estilos ---
        # 1. Cria um dataframe temporário apenas com a coluna de Estilo e remove linhas vazias
        df_estilos = df[['Estilo']].copy().dropna(subset=['Estilo'])
        
        # 2. Separa a string de estilos em uma lista, removendo espaços extras
        # Ex: "Metroidvania, Soulslike" -> ['Metroidvania', 'Soulslike']
        df_estilos['Estilo'] = df_estilos['Estilo'].str.split(',').apply(lambda x: [i.strip() for i in x])
        
        # 3. "Explode" o dataframe: cria uma nova linha para cada estilo na lista
        df_estilos = df_estilos.explode('Estilo')
        
        # 4. Agora, faz a contagem dos valores individuais
        jogos_por_estilo = df_estilos['Estilo'].value_counts().to_dict()
        # --- Fim da Lógica de Estilos ---

        charts_data = {
            'jogos_por_status': df['Status'].value_counts().to_dict(),
            'jogos_por_plataforma': df['Plataforma'].value_counts().to_dict(),
            'jogos_por_estilo': jogos_por_estilo # <-- Adiciona o novo cálculo
        }

        # Converte o DataFrame para um formato JSON amigável
        jogos_list = json.loads(df.to_json(orient='records', date_format='iso'))

        dados_finais = {
            'estatisticas': stats,
            'graficos': charts_data,
            'biblioteca': jogos_list
        }
        
        _cache["data"] = dados_finais
        _cache["last_fetched"] = datetime.now()
        return dados_finais

    except Exception as e:
        print(f"ERRO CRÍTICO ao processar planilha de jogos: {e}")
        import traceback
        traceback.print_exc()
        raise

def get_game_data():
    """Ponto de entrada que gerencia o cache."""
    # O cache está desativado para vermos as mudanças mais rápido durante o desenvolvimento
    # Para reativar, descomente as 3 linhas abaixo e comente a última
    # if _is_cache_valid():
    #     return _cache["data"]
    return _fetch_and_process_data()
