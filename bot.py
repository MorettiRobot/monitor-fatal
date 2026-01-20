import cloudscraper
from bs4 import BeautifulSoup
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
        self.flag_iniciado = "script_iniciado.flag"

        self.AUSENCIAS_MAX = 2
        self.hoje = datetime.now().strftime("%Y-%m-%d")

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
    # Controle de inicialização
    # -----------------------------
    def ja_iniciado(self):
        return os.path.exists(self.flag_iniciado)

    def marcar_iniciado(self):
        with open(self.flag_iniciado, "w") as f:
            f.write("ok")

    # -----------------------------
    # Telegram
    # -----------------------------
    def enviar_telegram(self, texto):
        if not self.token or not self.chat_id:
            return

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": texto,
                "disable_web_page_preview": True
            }
            requests.post(url, data=payload, timeout=10)
        except Exception as e:
            print("Erro Telegram:", e)

    # -----------------------------
    # Scraping
    # -----------------------------
    def buscar_modelos(self):
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(self.site, timeout=30)

        if resp.status_code != 200:
            print("Erro HTTP:", resp.status_code)
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        modelos = {}

        cards = soup.find_all("div", class_="shadow-listing-cards")

        for card in cards:
            texto = card.get_text(" ", strip=True)

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

            modelos[slug] = {
                "nome": nome,
                "link": link
            }

        return modelos

    # -----------------------------
    # Execução principal
    # -----------------------------
    def executar(self):
        memoria = self.carregar_memoria()
        primeira_execucao = not self.ja_iniciado()

        modelos_atuais = self.buscar_modelos()

        novas = []
        retornos = []
        saidas = []

        nova_memoria = {}

        # Entradas e retornos
        for slug, dados in modelos_atuais.items():
            if slug not in memoria:
                novas.append(dados["nome"])
                nova_memoria[slug] = {
                    "nome": dados["nome"],
                    "ativa": True,
                    "ausencias": 0,
                    "primeira_vez": self.hoje,
                    "ultima_aparicao": self.hoje
                }
            else:
                if not memoria[slug]["ativa"]:
                    retornos.append(dados["nome"])

                nova_memoria[slug] = {
                    **memoria[slug],
                    "ativa": True,
                    "ausencias": 0,
                    "ultima_aparicao": self.hoje
                }

        # Ausências e saídas
        for slug, estado in memoria.items():
            if slug not in modelos_atuais:
                faltas = estado.get("ausencias", 0) + 1

                if estado["ativa"] and faltas >= self.AUSENCIAS_MAX:
                    saidas.append(estado["nome"])
                    nova_memoria[slug] = {
                        **estado,
                        "ativa": False,
                        "ausencias": faltas
                    }
                else:
                    nova_memoria[slug] = {
                        **estado,
                        "ausencias": faltas
                    }

        # Telegram
        if primeira_execucao:
            self.enviar_telegram("🟢 Monitor FatalModel iniciado e ativo.")
            self.marcar_iniciado()
        else:
            mensagens = []

            if novas:
                mensagens.append(
                    "✅ NOVATAS:\n" +
                    "\n".join(f"• {n}" for n in novas)
                )

            if retornos:
                mensagens.append(
                    "🔄 DE VOLTA:\n" +
                    "\n".join(f"• {n}" for n in retornos)
                )

            if saidas:
                mensagens.append(
                    "❌ SAÍRAM:\n" +
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