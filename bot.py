from bs4 import BeautifulSoup
from cloudscraper import CloudScraper
import requests
import json
import os
from datetime import datetime
import re

class AlertFatal:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_ID")
        self.site = "https://fatalmodel.com/acompanhantes-tucurui-pa"
        self.db_file = "modelos_conhecidas.json"
        self.AUSENCIAS_MAX = 2

    # -----------------------------
    # Persistência
    # -----------------------------
    def carregar_memoria(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, "r") as f:
                return json.load(f)
        return {}

    def salvar_memoria(self, dados):
        with open(self.db_file, "w") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    # -----------------------------
    # Telegram
    # -----------------------------
    def enviar_telegram(self, texto):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": texto,
            "disable_web_page_preview": True
        }
        requests.post(url, data=payload, timeout=10)

    # -----------------------------
    # Scraping DEFINITIVO
    # -----------------------------
    def buscar_modelos(self):
        scraper = CloudScraper.create_scraper()
        resp = scraper.get(self.site, timeout=30)

        soup = BeautifulSoup(resp.text, "html.parser")

        modelos = {}

        for a in soup.find_all("a", href=True):
            href = a["href"]

            if "/acompanhante/" in href:
                link = href
                if link.startswith("/"):
                    link = "https://fatalmodel.com" + link

                # extrai nome do slug
                slug = link.rstrip("/").split("/")[-1]
                nome = slug.replace("-", " ").title()

                modelos[nome] = {
                    "link": link
                }

        return modelos

    # -----------------------------
    # Execução
    # -----------------------------
    def executar(self):
        agora = datetime.now().strftime("%d/%m %H:%M")
        self.enviar_telegram(f"🟢 Monitor Fatal ativo\n⏰ {agora}")

        memoria = self.carregar_memoria()
        modelos_atuais = self.buscar_modelos()

        print(f"MODELOS CAPTURADAS: {len(modelos_atuais)}")

        # 🔹 envia lista completa
        lista = "\n".join(f"• {n}" for n in sorted(modelos_atuais))
        self.enviar_telegram(
            f"📋 MODELOS EM TUCURUÍ ({len(modelos_atuais)})\n\n{lista}"
        )

        nova_memoria = {}

        # novas / retornos
        for nome in modelos_atuais:
            if nome not in memoria:
                self.enviar_telegram(f"✅ NOVA MODELO\n👤 {nome}")
                nova_memoria[nome] = {"ausencias": 0, "ativa": True}
            else:
                if not memoria[nome]["ativa"]:
                    self.enviar_telegram(f"🔄 MODELO DE VOLTA\n👤 {nome}")
                nova_memoria[nome] = {"ausencias": 0, "ativa": True}

        # ausentes
        for nome, estado in memoria.items():
            if nome not in modelos_atuais:
                faltas = estado["ausencias"] + 1
                if estado["ativa"] and faltas >= self.AUSENCIAS_MAX:
                    self.enviar_telegram(f"❌ MODELO AUSENTE\n👤 {nome}")
                    nova_memoria[nome] = {"ausencias": faltas, "ativa": False}
                else:
                    nova_memoria[nome] = {
                        "ausencias": faltas,
                        "ativa": estado["ativa"]
                    }

        self.salvar_memoria(nova_memoria)
        print("Execução concluída.")

# -----------------------------
if __name__ == "__main__":
    AlertFatal().executar()
