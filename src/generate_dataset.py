import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import datetime, timedelta
import os

fake = Faker('pt_BR')

DIAS_HISTORICO = 90
DATA_FIM = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
DATA_INICIO = DATA_FIM - timedelta(days=DIAS_HISTORICO)

CANAIS = {
    'CT': 'Centauro',
    'ML': 'Mercado Livre',
    'DF': 'Dafiti',
    'NT': 'Netshoes',
    'AZ': 'Amazon',
    'RN': 'Renner',
    'SN': 'Shein'
}

CANAL_PESOS = {
    'CT': 0.25,
    'ML': 0.25,
    'DF': 0.15,
    'NT': 0.15,
    'AZ': 0.10,
    'RN': 0.05,
    'SN': 0.05
}

PRODUTOS = {
    'Calçados': [
        'Tênis Corrida',
        'Tênis Futsal',
        'Chuteira',
        'Tênis Casual'
    ],

    'Confecções': [
        'Camiseta Dry-Fit',
        'Short Esportivo',
        'Legging',
        'Agasalho',
        'Meião Esportivo',
        'Regata'
    ],

    'Acessórios': [
        'Mochila Esportiva',
        'Squeeze',
        'Boné'
    ]
}

FAIXA_PRECO = {
    'Calçados': (150.00, 800.0),
    'Confecções': (50.0, 300.0),
    'Acessórios': (30.0, 200.0)
}

FAIXA_MARKUP = {
    'Calçados': (40.0, 120.0),
    'Confecções': (60.0, 150.0),
    'Acessórios': (50.0, 130.0)
}

PEDIDOS_DIA = {
    'CT': (15, 50),
    'ML': (15, 50),
    'DF': (8, 30),
    'NT': (8, 30),
    'AZ': (5, 20),
    'RN': (3, 12),
    'SN': (3, 12)
}

FATOR_DIA_SEMANA = {
    0: 0.85,
    1: 0.90,
    2: 0.95,
    3: 1.00,
    4: 1.15,
    5: 1.25,
    6: 1.10
}

def gerar_sku():
    return f"{random.randint(1000,9999)}-{random.randint(1,99):02d}-{random.randint(1,99):02d}-{random.randint(30,46)}"

def gerar_numero_pedido(canal):
    sufixo = random.randint(100000000, 999999999)
    return f"{canal}-{sufixo}"

def gerar_item(canal, data):
    categoria = random.choices(list(PRODUTOS.keys()),weights=[0.40, 0.40, 0.20])[0]
    produto = random.choice(PRODUTOS[categoria])

    preco_min, preco_max = FAIXA_PRECO[categoria]

    valor_unitario = round(random.uniform(preco_min, preco_max), 2)
    custo_unitario = round(random.uniform(valor_unitario * 0.4, valor_unitario * 0.8), 2)
    markup = round(valor_unitario / custo_unitario, 2)
    qtde = random.randint(1, 3)
    valor_liquido = round(valor_unitario * qtde, 2)
    custo_total = round(custo_unitario * qtde, 2)
    margem_contribuicao = round((valor_liquido - custo_total) / valor_liquido * 100, 2)

    return {
        'pedido_numero': gerar_numero_pedido(canal),
        'pedido_data': data.strftime('%Y-%m-%d'),
        'canal': canal,
        'sku': gerar_sku(),
        'categoria': categoria,
        'produto_nome': produto,
        'item_qtde': qtde,
        'item_valor_unitario': valor_unitario,
        'item_custo_unitario': custo_unitario,
        'item_valor_liquido': valor_liquido,
        'markup': markup,
        'margem_contribuicao': margem_contribuicao,
        'pedido_status': 'FATURADO'
    }


def gerar_dataset():
    registros = []
    data_atual = DATA_INICIO

    while data_atual <= DATA_FIM:
        fator = FATOR_DIA_SEMANA[data_atual.weekday()]

        for canal in CANAIS:
            pedidos_min, pedidos_max = PEDIDOS_DIA[canal]
            qtd_pedidos = int(random.randint(pedidos_min, pedidos_max) * fator)

            for _ in range(qtd_pedidos):
                registros.append(gerar_item(canal, data_atual))

        data_atual += timedelta(days=1)

    return pd.DataFrame(registros)


if __name__ == '__main__':
    print("Gerando dataset...")
    df = gerar_dataset()

    print(f"Total de registros: {len(df)}")
    print(f"Período: {df['pedido_data'].min()} até {df['pedido_data'].max()}")
    print(f"\nDistribuição por canal:\n{df.groupby('canal')['pedido_numero'].count()}")

    os.makedirs('data/incoming', exist_ok=True)
    caminho = 'data/incoming/vendas_historico.xlsx'
    df.to_excel(caminho, index=False)
    print(f"\nArquivo gerado: {caminho}")