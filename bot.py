from bs4 import BeautifulSoup
from cloudscraper import CloudScraper
import requests
import json
import os
from datetime import datetime


class AlertFatal:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_ID")

        self.site = "https://fatalmodel.com/acompanhantes-tucurui-pa"
        self.db_file = "modelos_conhecidas.json"

        # Quantas execuções seguidas para confirmar saída
        self.AUSENCIAS_MAX = 2

    # -------------------------------------------------
    # Persistência
    # -------------------------------------------------
    def carregar_memoria(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def salvar_memoria(self, dados):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    # -------------------------------------------------
    # Telegram
    # -------------------------------------------------
    def enviar_telegram(self, texto):
        if not self.token or not self.chat_id:
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": texto,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            requests.post(url, data=payload, timeout=10)
        except:
            pass

    # -------------------------------------------------
    # Scraping ROBUSTO
    # -------------------------------------------------
    def buscar_modelos(self):
        scraper = CloudScraper.create_scraper()
        req = scraper.get(self.site, timeout=30)

        if req.status_code != 200:
            raise Exception(f"Erro HTTP {req.status_code}")

        soup = BeautifulSoup(req.text, "html.parser")
        modelos = {}

        # Padrão REAL: link de perfil
        links = soup.find_all("a", href=True)

        for a in links:
            href = a["href"]

            if not href.startswith("/model/"):
                continue

            # tenta achar o card pai
            card = a.find_parent("div")
            if not card:
                continue

            nome_tag = card.find("h2")
            if not nome_tag:
                continue

            nome = nome_tag.get_text(strip=True)

            local_div = card.find("div", class_="truncate")
            local = local_div.get_text(strip=True) if local_div else ""

            # filtra cidade
            if "Tucuruí" not in local:
                continue

            preco_div = card.find("div", class_="price-list__value")
            preco = preco_div.get_text(strip=True) if preco_div else "S/V"

            link = "https://fatalmodel.com" + href

            modelos[nome] = {
                "preco": preco,
                "link": link,
            }

        return modelos

    # -------------------------------------------------
    # Execução principal
    # -------------------------------------------------
    def executar(self):
        agora = datetime.now().strftime("%d/%m %H:%M")
        self.enviar_telegram(f"🟢 *Monitor Fatal Tucuruí ativo*\n⏰ {agora}")

        memoria = self.carregar_memoria()
        modelos_atuais = self.buscar_modelos()

        nova_memoria = {}

        # -----------------------------
        # Modelos presentes
        # -----------------------------
        for nome, dados in modelos_atuais.items():

            if nome not in memoria:
                # NOVA
                msg = (
                    f"✅ *NOVA MODELO EM TUCURUÍ*\n\n"
                    f"👤 {nome}\n"
                    f"💰 {dados['preco']}\n"
                    f"🔗 {dados['link']}"
                )
                self.enviar_telegram(msg)

                nova_memoria[nome] = {
                    "ausencias": 0,
                    "ativa": True
                }
                continue

            estado_antigo = memoria[nome]

            if not estado_antigo["ativa"]:
                # VOLTOU
                msg = (
                    f"🔄 *MODELO DE VOLTA*\n\n"
                    f"👤 {nome}\n"
                    f"💰 {dados['preco']}\n"
                    f"🔗 {dados['link']}"
                )
                self.enviar_telegram(msg)

            nova_memoria[nome] = {
                "ausencias": 0,
                "ativa": True
            }

        # -----------------------------
        # Modelos ausentes
        # -----------------------------
        for nome, estado in memoria.items():
            if nome not in modelos_atuais:
                faltas = estado["ausencias"] + 1

                if estado["ativa"] and faltas >= self.AUSENCIAS_MAX:
                    msg = (
                        f"❌ *MODELO AUSENTE (confirmado)*\n\n"
                        f"👤 {nome}\n"
                        f"⏳ Ausente há ~{faltas * 50} minutos"
                    )
                    self.enviar_telegram(msg)

                    nova_memoria[nome] = {
                        "ausencias": faltas,
                        "ativa": False
                    }
                else:
                    nova_memoria[nome] = {
                        "ausencias": faltas,
                        "ativa": estado["ativa"]
                    }

        self.salvar_memoria(nova_memoria)
        print("Execução concluída com sucesso.")


# -------------------------------------------------
# Start
# -------------------------------------------------
if __name__ == "__main__":
    bot = AlertFatal()
    bot.executar()
