from bs4 import BeautifulSoup
from cloudscraper import CloudScraper
import requests
import json
import os

class AlertFatal:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_ID")

        self.site = "https://fatalmodel.com/acompanhantes-tucurui-pa"
        self.db_file = "modelos_conhecidas.json"

        # confirma saída após N execuções ausente
        self.AUSENCIAS_MAX = 2

    # -----------------------------
    # Persistência
    # -----------------------------
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
    # Scraping (somente Tucuruí)
    # -----------------------------
    def buscar_modelos(self):
        scraper = CloudScraper.create_scraper()
        resp = scraper.get(self.site, timeout=30)

        soup = BeautifulSoup(resp.text, "html.parser")

        modelos = {}

        cards = soup.find_all("div", class_="shadow-listing-cards")

        for card in cards:
            texto = card.get_text(" ", strip=True)

            # garante Tucuruí
            if "Tucuruí" not in texto:
                continue

            a = card.find("a", href=True)
            if not a:
                continue

            href = a["href"]
            if "/acompanhante/" not in href:
                continue

            link = href
            if link.startswith("/"):
                link = "https://fatalmodel.com" + link

            slug = link.rstrip("/").split("/")[-1]
            nome = slug.replace("-", " ").title()

            modelos[nome] = {"link": link}

        return modelos

    # -----------------------------
    # Execução principal
    # -----------------------------
    def executar(self):
        memoria = self.carregar_memoria()
        modelos_atuais = self.buscar_modelos()

        novas = []
        retornos = []
        saidas = []

        nova_memoria = {}

        # 🔹 Entradas (novas ou retorno)
        for nome in modelos_atuais:
            if nome not in memoria:
                novas.append(nome)
                nova_memoria[nome] = {"ausencias": 0, "ativa": True}
            else:
                if not memoria[nome]["ativa"]:
                    retornos.append(nome)
                nova_memoria[nome] = {"ausencias": 0, "ativa": True}

        # 🔻 Saídas
        for nome, estado in memoria.items():
            if nome not in modelos_atuais:
                faltas = estado["ausencias"] + 1

                if estado["ativa"] and faltas >= self.AUSENCIAS_MAX:
                    saidas.append(nome)
                    nova_memoria[nome] = {
                        "ausencias": faltas,
                        "ativa": False
                    }
                else:
                    nova_memoria[nome] = {
                        "ausencias": faltas,
                        "ativa": estado["ativa"]
                    }

        # 📤 Envia SOMENTE se houve mudança
        mensagens = []

        if novas:
            mensagens.append(
                "✅ NOVAS MODELOS:\n" +
                "\n".join(f"• {n}" for n in novas)
            )

        if retornos:
            mensagens.append(
                "🔄 MODELOS DE VOLTA:\n" +
                "\n".join(f"• {n}" for n in retornos)
            )

        if saidas:
            mensagens.append(
                "❌ MODELOS AUSENTES:\n" +
                "\n".join(f"• {n}" for n in saidas)
            )

        if mensagens:
            self.enviar_telegram("\n\n".join(mensagens))

        self.salvar_memoria(nova_memoria)


# -----------------------------
# Start
# -----------------------------
if __name__ == "__main__":
    AlertFatal().executar()
