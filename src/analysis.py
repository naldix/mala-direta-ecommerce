import _sqlite3
import pandas as pd
from datetime import datetime, timedelta   
import logging
import os

logging.basicConfig(
    filename='logs/pipeline.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

log = logging.getLogger(__name__)

DB_PATH = 'data/database/vendas.db'

CANAIS_NOMES = {
    'CT': 'Centauro',
    'ML': 'Mercado Livre',
    'DF': 'Dafiti',
    'NT': 'Netshoes',
    'AZ': 'Amazon',
    'RN': 'Renner',
    'SN': 'Shein'
}

def get_connection():
    return _sqlite3.connect(DB_PATH)

def definir_periodos():
    hoje = datetime.today()
    dia_semana = hoje.weekday()

    periodos = []

    if dia_semana == 0:
        sexta = hoje - timedelta(days=3)
        sabado = hoje - timedelta(days=2)
        domingo = hoje - timedelta(days=1)

        periodos = [
            {
                'label': 'Sexta-feira',
                'data': sexta.strftime('%Y-%m-%d'),
                'data_anterior': (sexta - timedelta(days=7)).strftime('%Y-%m-%d')
            },
            {
                'label': 'Sábado',
                'data': sabado.strftime('%Y-%m-%d'),
                'data_anterior': (sabado - timedelta(days=7)).strftime('%Y-%m-%d')
            },
            {
                'label': 'Domingo',
                'data': domingo.strftime('%Y-%m-%d'),
                'data_anterior': (domingo - timedelta(days=7)).strftime('%Y-%m-%d')
            },
            {
                'label': 'Final de Semana',
                'data': [sabado.strftime('%Y-%m-%d'), domingo.strftime('%Y-%m-%d')],
                'data_anterior': [
                    (sabado - timedelta(days=7)).strftime('%Y-%m-%d'),
                    (domingo - timedelta(days=7)).strftime('%Y-%m-%d')
                ],
                'is_fds': True
            }
        ]
    else:
        d1 = hoje - timedelta(days=1)
        d1_anterior = d1 - timedelta(days=7)

        periodos = [
            {
                'label': d1.strftime('%d/%m/%Y'),
                'data': d1.strftime('%Y-%m-%d'),
                'data_anterior': d1_anterior.strftime('%Y-%m-%d')
            }
        ]

    return periodos

def buscar_vendas(datas):

    if isinstance(datas, str):
        datas = [datas]

    placeholders = ','.join(['?' for _ in datas])
    query = f"SELECT * FROM vendas WHERE pedido_data IN ({placeholders})"

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=datas)

    return df

def calcular_kpis(df):

    if df.empty:
        return pd.DataFrame()

    kpis = []

    for canal in sorted(df['canal'].unique()):
        dc = df[df['canal'] == canal].copy()

        faturamento = round(dc['item_valor_liquido'].sum(), 2)
        qtd_pedidos = dc['pedido_numero'].nunique()
        ticket_medio = round(faturamento / qtd_pedidos, 2) if qtd_pedidos > 0 else 0
        markup_medio = round(dc['markup'].mean(), 2)
        margem_media = round(dc['margem_contribuicao'].mean(), 2)

        top_produto = (
            dc.groupby('produto_nome')['item_qtde']
            .sum()
            .idxmax()
        )

        kpis.append({
            'canal': canal,
            'canal_nome': CANAIS_NOMES.get(canal, canal),
            'faturamento': faturamento,
            'qtd_pedidos': qtd_pedidos,
            'ticket_medio': ticket_medio,
            'markup_medio': markup_medio,
            'margem_contribuicao': margem_media,
            'top_produto': top_produto
        })

    return pd.DataFrame(kpis)

def calcular_variacao(kpis_atual, kpis_anterior):

    if kpis_anterior.empty:
        kpis_atual['var_faturamento'] = None
        kpis_atual['var_qtd_pedidos'] = None
        return kpis_atual

    merged = kpis_atual.merge(
        kpis_anterior[['canal', 'faturamento', 'qtd_pedidos']],
        on='canal',
        how='left',
        suffixes=('', '_ant')
    )

    def variacao(atual, anterior):
        if anterior and anterior != 0:
            return round(((atual - anterior) / anterior) * 100, 2)
        return None

    merged['var_faturamento'] = merged.apply(
        lambda r: variacao(r['faturamento'], r.get('faturamento_ant')), axis=1
    )
    merged['var_qtd_pedidos'] = merged.apply(
        lambda r: variacao(r['qtd_pedidos'], r.get('qtd_pedidos_ant')), axis=1
    )

    merged.drop(columns=['faturamento_ant', 'qtd_pedidos_ant'], inplace=True)

    return merged

def rodar_analise():
  
    log.info("Iniciando análise...")
    periodos = definir_periodos()
    resultado = []

    for periodo in periodos:
        label = periodo['label']
        data = periodo['data']
        data_ant = periodo['data_anterior']
        is_fds = periodo.get('is_fds', False)

        datas_busca = data if isinstance(data, list) else [data]
        datas_ant = data_ant if isinstance(data_ant, list) else [data_ant]

        df_atual = buscar_vendas(datas_busca)
        df_anterior = buscar_vendas(datas_ant)

        if df_atual.empty:
            log.warning(f"Sem dados para o período: {label} ({data})")
            print(f"[AVISO] Sem dados para: {label}")
            continue

        kpis_atual = calcular_kpis(df_atual)
        kpis_anterior = calcular_kpis(df_anterior)
        kpis_final = calcular_variacao(kpis_atual, kpis_anterior)

        resultado.append({
            'label': label,
            'data': data,
            'is_fds': is_fds,
            'kpis': kpis_final
        })

        log.info(f"Período analisado: {label} — {len(kpis_final)} canais.")

    log.info("Análise concluída.")
    return resultado

if __name__ == '__main__':
    resultados = rodar_analise()

    for r in resultados:
        print(f"\n{'='*60}")
        print(f"Período: {r['label']}")
        print(f"{'='*60}")
        print(r['kpis'].to_string(index=False))