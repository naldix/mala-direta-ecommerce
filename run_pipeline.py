import argparse
import logging
import os
import sys
from datetime import datetime

from src.generate_dataset import gerar_dataset
from src.etl import rodar_etl
from src.analysis import rodar_analise
from src.ai_insights import gerar_insights
from src.report import gerar_relatorio
from src.email_sender import enviar_email

logging.basicConfig(
    filename='logs/pipeline.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

log = logging.getLogger(__name__)


class EtapaPipelineError(Exception):
    """Erro customizado para identificar em qual etapa o pipeline falhou."""
    def __init__(self, etapa, mensagem_original):
        self.etapa = etapa
        self.mensagem_original = mensagem_original
        super().__init__(f"[{etapa}] {mensagem_original}")


def executar_dataset(skip):
    if skip:
        log.info("Dataset generation ignorado.")
        return

    try:
        log.info("Gerando dataset...")
        df = gerar_dataset()

        os.makedirs('data/incoming', exist_ok=True)
        path = 'data/incoming/vendas_historico.xlsx'
        df.to_excel(path, index=False)

        log.info(f"Dataset gerado: {path}")

    except Exception as e:
        raise EtapaPipelineError("GERAÇÃO DE DATASET", str(e))


def executar_etl():
    try:
        rodar_etl()
    except Exception as e:
        raise EtapaPipelineError("ETL", str(e))


def executar_analise():
    try:
        resultados = rodar_analise()

        if not resultados:
            raise EtapaPipelineError(
                "ANÁLISE",
                "Nenhum período retornou dados. Verifique se o banco está populado "
                "e se há registros para as datas esperadas (D-1 ou Sex/Sáb/Dom)."
            )

        return resultados

    except EtapaPipelineError:
        raise
    except Exception as e:
        raise EtapaPipelineError("ANÁLISE", str(e))


def executar_ai_insights(resultados, skip):
    if skip:
        log.info("AI insights ignorados.")
        return resultados

    try:
        return gerar_insights(resultados)
    except Exception as e:
        # Falha na IA não deveria travar o pipeline inteiro —
        # o relatório ainda pode ser enviado sem os insights.
        log.error(f"[AI INSIGHTS] Falha ao gerar insights: {e}", exc_info=True)
        print(f"[AVISO] Falha ao gerar insights via IA. Relatório seguirá sem essa seção.")
        return resultados


def executar_report(resultados):
    try:
        caminho = gerar_relatorio(resultados)
        if not caminho or not os.path.exists(caminho):
            raise EtapaPipelineError("RELATÓRIO", "Arquivo de relatório não foi gerado.")
        return caminho
    except EtapaPipelineError:
        raise
    except Exception as e:
        raise EtapaPipelineError("RELATÓRIO", str(e))


def executar_email(caminho, referencia, skip):
    if skip:
        log.info("Envio de e-mail ignorado.")
        return True

    try:
        sucesso = enviar_email(caminho, referencia)
        if not sucesso:
            log.warning("Envio de e-mail retornou falha (ver logs do email_sender).")
            print("[AVISO] E-mail não foi enviado. Verifique credenciais/destinatários no .env")
        return sucesso

    except Exception as e:
        raise EtapaPipelineError("ENVIO DE E-MAIL", str(e))


def main(args):
    log.info("===== PIPELINE INICIADO =====")
    inicio = datetime.now()

    try:
        executar_dataset(args.skip_dataset)

        if args.only_dataset:
            log.info("===== PIPELINE FINALIZADO (only-dataset) =====")
            print("[OK] Dataset gerado com sucesso.")
            return

        if not args.skip_etl:
            executar_etl()

        if args.only_etl:
            log.info("===== PIPELINE FINALIZADO (only-etl) =====")
            print("[OK] ETL executado com sucesso.")
            return

        resultados = executar_analise()
        resultados = executar_ai_insights(resultados, args.skip_ai)
        caminho = executar_report(resultados)
        referencia = ', '.join([r['label'] for r in resultados])

        email_ok = executar_email(caminho, referencia, args.skip_email)

        duracao = (datetime.now() - inicio).total_seconds()
        log.info(f"===== PIPELINE FINALIZADO COM SUCESSO ({duracao:.1f}s) =====")

        if email_ok:
            print(f"\n[OK] Pipeline executado com sucesso em {duracao:.1f}s!")
        else:
            print(f"\n[CONCLUÍDO COM AVISOS] Pipeline rodou, mas o e-mail não foi enviado. ({duracao:.1f}s)")

    except EtapaPipelineError as e:
        log.error(f"Pipeline falhou na etapa: {e.etapa} — {e.mensagem_original}", exc_info=True)
        print(f"\n[ERRO] Falha na etapa '{e.etapa}': {e.mensagem_original}")
        sys.exit(1)

    except Exception as e:
        log.error(f"Falha inesperada no pipeline: {e}", exc_info=True)
        print(f"\n[ERRO] Falha inesperada: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de Dados E-commerce")

    parser.add_argument("--skip-dataset", action="store_true")
    parser.add_argument("--skip-etl", action="store_true")
    parser.add_argument("--skip-ai", action="store_true")
    parser.add_argument("--skip-email", action="store_true")

    parser.add_argument("--only-etl", action="store_true")
    parser.add_argument("--only-dataset", action="store_true")

    args = parser.parse_args()

    main(args)