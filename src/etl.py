import pandas as pd
import sqlite3
import os
import shutil
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    filename='logs/pipeline.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
log = logging.getLogger(__name__)

DB_PATH      = 'data/database/vendas.db'
DIR_INCOMING = 'data/incoming'
DIR_PROCESSED = 'data/processed'
ARQUIVO_HISTORICO = 'vendas_historico.xlsx'

COLUNAS_ESPERADAS = [
    'pedido_numero',
    'pedido_data',
    'canal',
    'sku',
    'categoria',
    'produto_nome',
    'item_qtde',
    'item_valor_unitario',
    'item_custo_unitario',
    'item_valor_liquido',
    'markup',
    'margem_contribuicao',
    'pedido_status'
]

CANAIS_VALIDOS = ['CT', 'ML', 'DF', 'NT', 'AZ', 'RN', 'SN']


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def criar_tabelas():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_numero TEXT,
                pedido_data TEXT,
                canal TEXT,
                sku TEXT,
                categoria TEXT,
                produto_nome TEXT,
                item_qtde INTEGER,
                item_valor_unitario REAL,
                item_custo_unitario REAL,
                item_valor_liquido REAL,
                markup REAL,
                margem_contribuicao REAL,
                pedido_status TEXT,
                inserido_em TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS carga_controle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_arquivo TEXT UNIQUE,
                data_referencia TEXT,
                processado_em TEXT,
                total_registros INTEGER
            )
        ''')
    log.info("Tabelas verificadas/criadas.")

def ja_carregado(nome_arquivo):
    with get_connection() as conn:
        cursor = conn.execute(
            'SELECT 1 FROM carga_controle WHERE nome_arquivo = ?',
            (nome_arquivo,)
        )
        return cursor.fetchone() is not None

def registrar_carga(nome_arquivo, data_referencia, total):
    with get_connection() as conn:
        conn.execute(
            '''INSERT INTO carga_controle (nome_arquivo, data_referencia, processado_em, total_registros)
               VALUES (?, ?, ?, ?)''',
            (nome_arquivo, data_referencia, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), total)
        )

def validar(df, nome_arquivo):
    erros = []

    faltando = [c for c in COLUNAS_ESPERADAS if c not in df.columns]
    if faltando:
        erros.append(f"Colunas faltando: {faltando}")

    canais_invalidos = df[~df['canal'].isin(CANAIS_VALIDOS)]['canal'].unique().tolist()
    if canais_invalidos:
        erros.append(f"Canais inválidos: {canais_invalidos}")

    for col in ['pedido_numero', 'pedido_data', 'canal', 'item_valor_liquido']:
        if col in df.columns and df[col].isnull().any():
            erros.append(f"Nulos na coluna: {col}")

    for col in ['item_valor_liquido', 'item_qtde', 'item_valor_unitario']:
        if col in df.columns and (df[col] < 0).any():
            erros.append(f"Valores negativos na coluna: {col}")

    if erros:
        for e in erros:
            log.error(f"[{nome_arquivo}] {e}")
        return False

    return True

def limpar(df):
    df['pedido_data'] = pd.to_datetime(df['pedido_data']).dt.strftime('%Y-%m-%d')
    df['canal'] = df['canal'].str.strip().str.upper()
    df['categoria'] = df['categoria'].str.strip()
    df['produto_nome'] = df['produto_nome'].str.strip()
    df['pedido_status'] = df['pedido_status'].str.strip().str.upper()

    antes = len(df)
    df = df.drop_duplicates(subset=['pedido_numero', 'sku', 'pedido_data'])
    if len(df) != antes:
        log.warning(f"Removidas {antes - len(df)} linhas duplicadas.")

    df = df[df['pedido_status'] == 'FATURADO'].copy()
    df['inserido_em'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return df

def carregar(df):
    colunas = [c for c in COLUNAS_ESPERADAS if c in df.columns] + ['inserido_em']
    with get_connection() as conn:
        df[colunas].to_sql('vendas', conn, if_exists='append', index=False)
    log.info(f"{len(df)} registros inseridos.")

def mover_para_processed(caminho):
    os.makedirs(DIR_PROCESSED, exist_ok=True)
    nome = os.path.basename(caminho)
    destino = os.path.join(DIR_PROCESSED, nome)
    shutil.move(caminho, destino)
    log.info(f"Arquivo movido para: {destino}")

def carga_inicial():
    caminho = os.path.join(DIR_INCOMING, ARQUIVO_HISTORICO)

    if not os.path.exists(caminho):
        print("[ERRO] vendas_historico.xlsx não encontrado em data/incoming/")
        log.error("vendas_historico.xlsx não encontrado.")
        return False

    criar_tabelas()

    if ja_carregado(ARQUIVO_HISTORICO):
        log.warning("Histórico já carregado. Ignorando.")
        print("[AVISO] Histórico já carregado. Nada a fazer.")
        return True

    print("Lendo arquivo histórico...")
    try:
        df = pd.read_excel(caminho)
        log.info(f"Arquivo lido: {len(df)} registros.")
    except Exception as e:
        log.error(f"Erro ao ler arquivo: {e}")
        print(f"[ERRO] {e}")
        return False

    if not validar(df, ARQUIVO_HISTORICO):
        print("[ERRO] Validação falhou. Verifique logs/pipeline.log")
        return False

    df = limpar(df)
    carregar(df)

    for data in df['pedido_data'].unique():
        nome_data = f"vendas_{data}.xlsx"
        if not ja_carregado(nome_data):
            registrar_carga(nome_data, data, len(df[df['pedido_data'] == data]))

    registrar_carga(ARQUIVO_HISTORICO, 'historico', len(df))

    print(f"[OK] {len(df)} registros carregados no banco com sucesso.")
    log.info("Carga inicial concluída.")
    return True

def carga_diaria():
    criar_tabelas()

    d1 = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    nome_arquivo = f"vendas_{d1}.xlsx"
    caminho = os.path.join(DIR_INCOMING, nome_arquivo)

    if not os.path.exists(caminho):
        log.warning(f"Arquivo D-1 não encontrado: {nome_arquivo}")
        print(f"[AVISO] Nenhum arquivo encontrado para D-1 ({d1}). Verifique a pasta {DIR_INCOMING}.")
        return False

    if ja_carregado(nome_arquivo):
        log.warning(f"Arquivo já processado: {nome_arquivo}")
        print(f"[AVISO] Arquivo {nome_arquivo} já foi processado anteriormente.")
        return True

    print(f"Processando arquivo diário: {nome_arquivo}...")
    try:
        df = pd.read_excel(caminho)
        log.info(f"Arquivo lido: {len(df)} registros.")
    except Exception as e:
        log.error(f"Erro ao ler arquivo: {e}")
        print(f"[ERRO] {e}")
        return False

    if not validar(df, nome_arquivo):
        print("[ERRO] Validação falhou. Verifique logs/pipeline.log")
        return False

    df = limpar(df)
    carregar(df)
    registrar_carga(nome_arquivo, d1, len(df))
    mover_para_processed(caminho)

    print(f"[OK] {len(df)} registros de {d1} carregados com sucesso.")
    log.info(f"Carga diária concluída: {nome_arquivo}")
    return True

def rodar_etl(modo='diario'):
    if modo == 'inicial':
        return carga_inicial()
    else:
        return carga_diaria()


if __name__ == '__main__':
    import sys
    modo = sys.argv[1] if len(sys.argv) > 1 else 'diario'
    rodar_etl(modo)