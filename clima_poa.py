"""
Alerta Operacional Epavi - Clima POA
-------------------------------------
O que faz:
  1. Busca temperatura máxima e probabilidade de chuva de Porto Alegre
  2. Monta um e-mail formatado
  3. Envia com o assunto "Alerta Operacional Epavi - Clima POA"

Como rodar:
  Modo teste (só imprime, NÃO envia e-mail):
    python clima_poa.py --teste

  Modo real (busca dados e ENVIA e-mail):
    python clima_poa.py
"""

import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

# =============================================================================
# CONFIGURAÇÕES — edite aqui antes de rodar
# =============================================================================

# Remetente e senha do Gmail
# IMPORTANTE: use uma "Senha de App", não a senha normal da sua conta.
# Como gerar: https://myaccount.google.com/apppasswords
EMAIL_REMETENTE = "seuemail@gmail.com"
EMAIL_SENHA     = "xxxx xxxx xxxx xxxx"   # senha de app (16 caracteres sem espaço)

# Destinatário (pode ser o mesmo e-mail para testar)
EMAIL_DESTINO   = "destinatario@email.com"

# =============================================================================
# PASSO 1 — Buscar dados de clima
# =============================================================================

def buscar_clima():
    """
    Consulta a API Open-Meteo (gratuita, sem cadastro).
    Retorna dicionário com os dados do dia para Porto Alegre.
    """
    url = "https://api.open-meteo.com/v1/forecast"

    parametros = {
        "latitude":     -30.0277,           # latitude de Porto Alegre
        "longitude":    -51.2287,           # longitude de Porto Alegre
        "timezone":     "America/Sao_Paulo",
        "forecast_days": 1,                 # só hoje
        "daily": [
            "temperature_2m_max",           # temperatura máxima do dia
            "temperature_2m_min",           # temperatura mínima do dia
            "precipitation_probability_max",# maior probabilidade de chuva do dia (%)
            "precipitation_sum",            # total de chuva prevista (mm)
        ],
    }

    resposta = requests.get(url, params=parametros, timeout=15)
    resposta.raise_for_status()  # lança erro se a API retornar problema

    dados = resposta.json()["daily"]

    return {
        "data":        dados["time"][0],
        "temp_max":    dados["temperature_2m_max"][0],
        "temp_min":    dados["temperature_2m_min"][0],
        "prob_chuva":  dados["precipitation_probability_max"][0],
        "chuva_mm":    dados["precipitation_sum"][0],
    }


# =============================================================================
# PASSO 2 — Montar o conteúdo do e-mail
# =============================================================================

def classificar_risco(prob):
    """Transforma a probabilidade (%) em texto e cor."""
    if prob >= 70:
        return "ALTA ⚠️", "#c0392b"    # vermelho
    if prob >= 40:
        return "MODERADA 🌧️", "#e67e22" # laranja
    return "BAIXA ☀️", "#27ae60"        # verde


def montar_email(dados):
    """
    Recebe o dicionário de clima e devolve o texto do e-mail
    em dois formatos: HTML (bonito) e texto puro (fallback).
    """
    data_formatada  = datetime.strptime(dados["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
    hora_agora      = datetime.now().strftime("%H:%M")
    risco, cor      = classificar_risco(dados["prob_chuva"])

    # --- Versão HTML ---
    html = f"""
<html>
<body style="font-family:Arial,sans-serif; background:#f0f0f0; padding:20px;">
  <div style="max-width:480px; margin:auto; background:#fff;
              border-radius:8px; padding:28px; box-shadow:0 2px 8px rgba(0,0,0,.1);">

    <h2 style="margin-top:0; color:#2c3e50;">
      🌦️ Clima Porto Alegre/RS
    </h2>
    <p style="color:#888; font-size:13px;">
      📅 {data_formatada} &nbsp;|&nbsp; 🕐 Coletado às {hora_agora}
    </p>

    <!-- Temperatura máxima -->
    <div style="background:#f9f9f9; border-left:4px solid #2c3e50;
                border-radius:4px; padding:14px 18px; margin:16px 0;">
      <p style="margin:0 0 4px; color:#555; font-size:13px;">🌡️ Temperatura Máxima</p>
      <p style="margin:0; font-size:30px; font-weight:bold; color:#2c3e50;">
        {dados["temp_max"]:.1f} °C
      </p>
      <p style="margin:4px 0 0; font-size:12px; color:#999;">
        Mínima: {dados["temp_min"]:.1f} °C
      </p>
    </div>

    <!-- Probabilidade de chuva -->
    <div style="background:#f9f9f9; border-left:4px solid {cor};
                border-radius:4px; padding:14px 18px; margin:16px 0;">
      <p style="margin:0 0 4px; color:#555; font-size:13px;">🌧️ Probabilidade de Chuva</p>
      <p style="margin:0; font-size:30px; font-weight:bold; color:{cor};">
        {dados["prob_chuva"]} %
      </p>
      <p style="margin:4px 0 0; font-size:12px; color:{cor};">
        Risco: {risco} &nbsp;|&nbsp; Acumulado previsto: {dados["chuva_mm"]:.1f} mm
      </p>
    </div>

    <p style="font-size:11px; color:#bbb; margin-bottom:0;">
      Fonte: Open-Meteo.com &nbsp;|&nbsp; Gerado por clima_poa.py
    </p>
  </div>
</body>
</html>
"""

    # --- Versão texto puro (exibida em clientes sem suporte a HTML) ---
    texto = f"""Alerta Operacional Epavi - Clima POA
Porto Alegre/RS — {data_formatada} — coletado às {hora_agora}

Temperatura Máxima : {dados["temp_max"]:.1f} °C
Temperatura Mínima : {dados["temp_min"]:.1f} °C
Prob. de Chuva     : {dados["prob_chuva"]} % — {risco}
Chuva Acumulada    : {dados["chuva_mm"]:.1f} mm

Fonte: Open-Meteo.com
"""

    return html, texto


# =============================================================================
# PASSO 3 — Enviar o e-mail
# =============================================================================

def enviar_email(html, texto):
    """Monta a mensagem MIME e envia via Gmail SMTP."""

    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = "Alerta Operacional Epavi - Clima POA"
    mensagem["From"]    = EMAIL_REMETENTE
    mensagem["To"]      = EMAIL_DESTINO

    # Anexa primeiro o texto puro, depois o HTML
    # O cliente de e-mail escolhe o melhor formato automaticamente
    mensagem.attach(MIMEText(texto, "plain", "utf-8"))
    mensagem.attach(MIMEText(html,  "html",  "utf-8"))

    # Conecta ao Gmail, faz login e envia
    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()                              # ativa criptografia
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
        servidor.sendmail(EMAIL_REMETENTE, EMAIL_DESTINO, mensagem.as_string())


# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================

def main():
    modo_teste = "--teste" in sys.argv

    # --- Busca os dados ---
    if modo_teste:
        print("⚙️  MODO TESTE — usando dados fictícios (nenhum e-mail será enviado)\n")
        dados = {
            "data":       "2025-06-17",
            "temp_max":   24.5,
            "temp_min":   14.2,
            "prob_chuva": 80,
            "chuva_mm":   12.4,
        }
    else:
        print("🔍 Buscando dados de clima para Porto Alegre...")
        try:
            dados = buscar_clima()
        except requests.RequestException as e:
            print(f"❌ Erro ao buscar clima: {e}")
            sys.exit(1)

    # --- Exibe no terminal ---
    print(f"📅 Data         : {dados['data']}")
    print(f"🌡️  Temp. Máxima : {dados['temp_max']} °C")
    print(f"🌡️  Temp. Mínima : {dados['temp_min']} °C")
    print(f"🌧️  Prob. Chuva  : {dados['prob_chuva']} %")
    print(f"💧 Acumulado    : {dados['chuva_mm']} mm")

    # --- Monta o e-mail ---
    html, texto = montar_email(dados)

    if modo_teste:
        # Só imprime o conteúdo — não envia nada
        print("\n" + "="*50)
        print("PRÉVIA DO E-MAIL (texto puro):")
        print("="*50)
        print(texto)
        print("="*50)
        print("✅ Teste concluído. Nenhum e-mail foi enviado.")
        return

    # --- Envia ---
    print("\n📤 Enviando e-mail...")
    try:
        enviar_email(html, texto)
        print(f"✅ E-mail enviado para {EMAIL_DESTINO}")
    except smtplib.SMTPAuthenticationError:
        print("❌ Senha incorreta ou não é uma Senha de App.")
        print("   Gere em: https://myaccount.google.com/apppasswords")
        sys.exit(1)
    except smtplib.SMTPException as e:
        print(f"❌ Erro ao enviar: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
