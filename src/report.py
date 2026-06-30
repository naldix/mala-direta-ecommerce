import os 
import logging
from datetime import datetime
from jinja2 import Template

logging.basicConfig(
    filename='logs/pipeline.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

log = logging.getLogger(__name__)

DIR_OUTPUT = 'output/reports'

def fmt_moeda(val):
    try:
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return '-'

def fmt_pct(val):
    try:
        if val is None:
            return '-'
        sinal = '+' if val > 0 else ''
        return f"{sinal}{val:.2f}%"
    except:
        return '-'

def fmt_var_class(val):
    """Retorna classe CSS conforme variação positiva ou negativa."""
    try:
        if val is None:
            return 'neutro'
        return 'positivo' if val > 0 else 'negativo'
    except:
        return 'neutro'
    
TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Vendas — {{ data_geracao }}</title>

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: "Segoe UI", Arial, sans-serif;
            background: #f4f6f9;
            color: #2c3e50;
            padding: 32px;
        }

        .container {
            max-width: 960px;
            margin: 0 auto;
        }

        /* HEADER */

        .header {
            background: #1a1a2e;
            color: #fff;
            padding: 28px 32px;
            border-radius: 10px;
            margin-bottom: 32px;
        }

        .header h1 {
            font-size: 22px;
            font-weight: 600;
            letter-spacing: .5px;
        }

        .header p {
            margin-top: 6px;
            font-size: 13px;
            color: #a0aec0;
        }

        /* PERÍODO */

        .periodo-bloco {
            margin-bottom: 40px;
        }

        .periodo-titulo {
            font-size: 16px;
            font-weight: 700;
            color: #1a1a2e;
            border-left: 4px solid #e94560;
            padding-left: 12px;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: .5px;
        }

        /* TABELA */

        .tabela-wrapper {
            width: 100%;
            overflow-x: auto;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08);
            background: #fff;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        thead tr {
            background: #1a1a2e;
            color: white;
        }

        thead th {
            padding: 12px 14px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: .4px;
            white-space: nowrap;
        }

        tbody tr {
            border-bottom: 1px solid #f0f0f0;
        }

        tbody tr:last-child {
            border-bottom: none;
        }

        tbody tr:hover {
            background: #f8f9ff;
        }

        tbody td {
            padding: 11px 14px;
            white-space: nowrap;
        }

        .canal-nome {
            font-weight: 600;
            color: #1a1a2e;
        }

        .canal-sigla {
            margin-left: 4px;
            font-size: 11px;
            color: #888;
        }

        .positivo {
            color: #27ae60;
            font-weight: 600;
        }

        .negativo {
            color: #e74c3c;
            font-weight: 600;
        }

        .neutro {
            color: #888;
        }

        /* INSIGHTS */

        .insights-bloco {
            width: 100%;
            margin-top: 18px;
        }

        .insight-item {
            width: 100%;
            background: #fff;
            border-left: 3px solid #e94560;
            border-radius: 6px;
            padding: 14px 18px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,.06);
            overflow: hidden;
        }

        .insight-canal {
            font-size: 12px;
            font-weight: 700;
            color: #e94560;
            text-transform: uppercase;
            letter-spacing: .5px;
            margin-bottom: 6px;
        }

        .insight-texto {
            width: 100%;
            font-size: 13px;
            color: #444;
            line-height: 1.7;
            white-space: normal;
            word-break: normal;
            overflow-wrap: break-word;
            word-wrap: break-word;
        }

        /* DIVIDER */

        .divider {
            border: none;
            border-top: 1px solid #e8e8e8;
            margin: 36px 0;
        }

        /* FOOTER */

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e8e8e8;
            text-align: center;
            font-size: 12px;
            color: #aaa;
        }

    </style>

</head>

<body>

<div class="container">

    <!-- HEADER -->

    <div class="header">
        <h1>📊 Relatório de Vendas por Canal</h1>
        <p>
            Gerado em {{ data_geracao }}
            &nbsp;|&nbsp;
            Referência: {{ referencia }}
        </p>
    </div>

    <!-- PERÍODOS -->

    {% for periodo in periodos %}

    <div class="periodo-bloco">

        <div class="periodo-titulo">
            {{ periodo.label }}
        </div>

        <!-- TABELA -->

        <div class="tabela-wrapper">

            <table>

                <thead>
                    <tr>
                        <th>Canal</th>
                        <th>Faturamento</th>
                        <th>Var% Fat. Semana Passada</th>
                        <th>Qtd. Pedidos</th>
                        <th>Var% Pedidos Semana Passada</th>
                        <th>Ticket Médio</th>
                        <th>Markup Médio</th>
                        <th>Margem Contrib.</th>
                        <th>Top Produto</th>
                    </tr>
                </thead>

                <tbody>

                    {% for row in periodo.rows %}

                    <tr>

                        <td>
                            <span class="canal-nome">{{ row.canal_nome }}</span>
                            <span class="canal-sigla">({{ row.canal }})</span>
                        </td>

                        <td>{{ row.faturamento }}</td>

                        <td class="{{ row.var_fat_class }}">
                            {{ row.var_faturamento }}
                        </td>

                        <td>{{ row.qtd_pedidos }}</td>

                        <td class="{{ row.var_ped_class }}">
                            {{ row.var_qtd_pedidos }}
                        </td>

                        <td>{{ row.ticket_medio }}</td>

                        <td>{{ row.markup_medio }}</td>

                        <td>{{ row.margem_contribuicao }}</td>

                        <td>{{ row.top_produto }}</td>

                    </tr>

                    {% endfor %}

                </tbody>

            </table>

        </div>

        <!-- INSIGHTS -->

        <div class="insights-bloco">

            {% for row in periodo.rows %}

            <div class="insight-item">

                <div class="insight-canal">
                    {{ row.canal_nome }}
                </div>

                <div class="insight-texto">
                    {{ row.insight }}
                </div>

            </div>

            {% endfor %}

        </div>

    </div>

    {% if not loop.last %}
        <hr class="divider">
    {% endif %}

    {% endfor %}

    <!-- FOOTER -->

    <div class="footer">
        Relatório gerado automaticamente &nbsp;|&nbsp; Mala Direta E-commerce
    </div>

</div>

</body>
</html>
"""

def preparar_periodos(resultados):
    periodos = []

    for r in resultados:
        rows = []
        for _, row in r['kpis'].iterrows():
            rows.append({
                'canal': row['canal'],
                'canal_nome': row['canal_nome'],
                'faturamento': fmt_moeda(row['faturamento']),
                'qtd_pedidos': int(row['qtd_pedidos']),
                'ticket_medio': fmt_moeda(row['ticket_medio']),
                'markup_medio': f"{row['markup_medio']:.2f}%",
                'margem_contribuicao': f"{row['margem_contribuicao']:.2f}%",
                'top_produto': row['top_produto'],
                'var_faturamento': fmt_pct(row.get('var_faturamento')),
                'var_qtd_pedidos': fmt_pct(row.get('var_qtd_pedidos')),
                'var_fat_class': fmt_var_class(row.get('var_faturamento')),
                'var_ped_class': fmt_var_class(row.get('var_qtd_pedidos')),
                'insight': row.get('insight', '')
            })

        periodos.append({
            'label': r['label'],
            'rows': rows
        })

    return periodos

def gerar_relatorio(resultados):
    os.makedirs(DIR_OUTPUT, exist_ok=True)

    data_geracao = datetime.now().strftime('%d/%m/%Y %H:%M')
    referencia = ', '.join([r['label'] for r in resultados])
    periodos = preparar_periodos(resultados)

    template = Template(TEMPLATE_HTML)
    html = template.render(
        data_geracao=data_geracao,
        referencia=referencia,
        periodos=periodos
    )

    nome_arquivo = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    caminho = os.path.join(DIR_OUTPUT, nome_arquivo)

    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(html)

    log.info(f"Relatório gerado: {caminho}")
    print(f"[OK] Relatório gerado: {caminho}")
    return caminho

if __name__ == '__main__':
    from analysis import rodar_analise
    from ai_insights import gerar_insights

    resultados = rodar_analise()
    resultados = gerar_insights(resultados)
    gerar_relatorio(resultados)