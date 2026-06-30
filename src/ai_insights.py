import os
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    filename='logs/pipeline.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
log = logging.getLogger(__name__)

MODELO = 'llama-3.1-8b-instant'

CANAIS_NOMES = {
    'CT': 'Centauro',
    'ML': 'Mercado Livre',
    'DF': 'Dafiti',
    'NT': 'Netshoes',
    'AZ': 'Amazon',
    'RN': 'Renner',
    'SN': 'Shein'
}
def formatar_kpis_para_prompt(canal_row):
    def fmt_var(val):
        if val is None:
            return 'sem dado anterior'
        sinal = '+' if val > 0 else ''
        return f"{sinal}{val:.2f}%"

    return f"""
Canal: {canal_row['canal_nome']} ({canal_row['canal']})
- Faturamento: R$ {canal_row['faturamento']:,.2f} ({fmt_var(canal_row.get('var_faturamento'))})
- Qtd. Pedidos: {canal_row['qtd_pedidos']} ({fmt_var(canal_row.get('var_qtd_pedidos'))})
- Ticket Médio: R$ {canal_row['ticket_medio']:,.2f}
- Markup Médio: {canal_row['markup_medio']:.2f}%
- Margem de Contribuição: {canal_row['margem_contribuicao']:.2f}%
- Produto Mais Vendido: {canal_row['top_produto']}
""".strip()

def gerar_insight_canal(canal_row, label_periodo):
    kpis_texto = formatar_kpis_para_prompt(canal_row)

    prompt = f"""Você é um analista comercial sênior especializado em e-commerce de artigos esportivos.

Analise os dados abaixo referentes ao período de {label_periodo} e gere um insight executivo curto.

{kpis_texto}

Instruções obrigatórias:
- Máximo de 3 frases. Não ultrapasse esse limite.
- Vá direto ao ponto mais relevante (maior variação ou destaque), sem introdução genérica.
- Não comece com "A análise indica", "O desempenho apresenta" ou frases similares — comece direto pelo fato.
- Se a variação for relevante (acima de +20% ou abaixo de -20%), aponte uma possível causa ou recomendação prática em poucas palavras.
- Não repita os números já presentes na tabela — interprete-os.
- Não mencione o nome do canal/marketplace no texto (ele já aparece como título acima do insight).
- Responda em português do Brasil, tom executivo e direto.
- Não use bullet points nem markdown."""

    try:
        client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        response = client.chat.completions.create(
            model=MODELO,
            messages=[
                {
                    'role': 'system',
                    'content': 'Você é um analista comercial sênior de e-commerce. Responda sempre em português do Brasil, de forma objetiva, executiva e extremamente concisa.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            max_tokens=150,
            temperature=0.6
        )
        insight = response.choices[0].message.content.strip()
        log.info(f"Insight gerado: {canal_row['canal']} — {label_periodo}")
        return insight

    except Exception as e:
        log.error(f"Erro ao gerar insight para {canal_row['canal']}: {e}")
        return "Não foi possível gerar o insight automático para este canal."

def gerar_insights(resultados_analise):
    log.info("Iniciando geração de insights via IA...")

    for periodo in resultados_analise:
        label = periodo['label']
        df    = periodo['kpis']

        print(f"Gerando insights: {label}...")
        insights = []

        for _, row in df.iterrows():
            insight = gerar_insight_canal(row, label)
            insights.append(insight)

        df['insight'] = insights
        periodo['kpis'] = df

    log.info("Insights gerados com sucesso.")
    return resultados_analise

if __name__ == '__main__':
    from analysis import rodar_analise

    resultados = rodar_analise()
    resultados = gerar_insights(resultados)

    for r in resultados:
        print(f"\n{'='*60}")
        print(f"Período: {r['label']}")
        print(f"{'='*60}")
        for _, row in r['kpis'].iterrows():
            print(f"\n[{row['canal_nome']}]")
            print(f"Insight: {row['insight']}")