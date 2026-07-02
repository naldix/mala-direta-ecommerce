import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
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

EMAIL_REMETENTE = os.environ.get('EMAIL_REMETENTE')
EMAIL_SENHA = os.environ.get('EMAIL_SENHA')
EMAIL_SMTP = os.environ.get('EMAIL_SMTP', 'smtp.gmail.com')
EMAIL_PORTA = int(os.environ.get('EMAIL_PORTA', 587))

EMAIL_DESTINATARIOS = [
    e.strip()
    for e in os.environ.get('EMAIL_DESTINATARIOS', '').split(',')
    if e.strip()
]
def ler_relatorio_html(caminho_relatorio):
    with open(caminho_relatorio, 'r', encoding='utf-8') as f:
        return f.read()

def montar_email(caminho_relatorio, referencia):
    data_geracao = datetime.now().strftime('%d/%m/%Y')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📊 Relatório de Vendas — {referencia} ({data_geracao})"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = ', '.join(EMAIL_DESTINATARIOS)

    # 📌 corpo do email = HTML do relatório gerado
    html_relatorio = ler_relatorio_html(caminho_relatorio)
    msg.attach(MIMEText(html_relatorio, 'html'))

    return msg

def enviar_email(caminho_relatorio, referencia):
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        log.error("Credenciais de e-mail não configuradas no .env")
        print("[ERRO] Configure EMAIL_REMETENTE e EMAIL_SENHA no .env")
        return False

    if not EMAIL_DESTINATARIOS:
        log.error("Nenhum destinatário configurado no .env")
        print("[ERRO] Configure EMAIL_DESTINATARIOS no .env")
        return False

    if not os.path.exists(caminho_relatorio):
        log.error(f"Relatório não encontrado: {caminho_relatorio}")
        print(f"[ERRO] Relatório não encontrado: {caminho_relatorio}")
        return False

    try:
        msg = montar_email(caminho_relatorio, referencia)

        with smtplib.SMTP(EMAIL_SMTP, EMAIL_PORTA) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_REMETENTE, EMAIL_SENHA)
            server.sendmail(
                EMAIL_REMETENTE,
                EMAIL_DESTINATARIOS,
                msg.as_string()
            )

        log.info(f"E-mail enviado para: {EMAIL_DESTINATARIOS}")
        print(f"[OK] E-mail enviado para: {EMAIL_DESTINATARIOS}")
        return True

    except smtplib.SMTPAuthenticationError:
        log.error("Erro de autenticação SMTP — verifique e-mail e senha no .env")
        print("[ERRO] Autenticação falhou. Se usar Gmail, use uma senha de app.")
        return False

    except Exception as e:
        log.error(f"Erro ao enviar e-mail: {e}")
        print(f"[ERRO] {e}")
        return False

if __name__ == '__main__':
    from analysis import rodar_analise
    from ai_insights import gerar_insights
    from report import gerar_relatorio

    resultados = rodar_analise()
    resultados = gerar_insights(resultados)
    caminho = gerar_relatorio(resultados)
    referencia = ', '.join([r['label'] for r in resultados])
    enviar_email(caminho, referencia)