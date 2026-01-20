from bs4 import BeautifulSoup
from cloudscraper import CloudScraper
import requests
import json
import os
from datetime import datetime


class AlertFatal:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_ID')

        # Página já filtrada por Tucuruí
        self.site = 'https://fatalmodel.com/acompanhantes-tucurui-pa'

        self.db_file = 'modelos_conhecidas.json'
        self.AUSENCIAS_MAX = 2  # confirma saída após 2 execuções

    # -----------------------------
    # Persistência
    # -----------------------------
    def carregar_memoria(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def salvar_memoria(self, dados):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    # -----------------------------
    # Telegram
    # -----------------------------
    def enviar_telegram(self, texto):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': texto,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        requests.post(url, data=payload, timeout=10)

    # -----------------------------
    # Scraping
    # -----------------------------
    def buscar_modelos(self):
        scraper = CloudScraper.create_scraper()
        response = scraper.get(self.site, timeout=20)

        if response.status_code != 200:
            raise Exception(f"Erro HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Cada modelo está dentro desse card
        cards = soup.find_all('div', class_='shadow-listing-cards')

        modelos = {}

        for card in cards:
            # Nome
            nome_tag = card.find('h2')
            if not nome_tag:
                continue
            nome = nome_tag.get_text(strip=True)

            # Localização (confirma Tucuruí)
            local_tag = card.find('div', class_='truncate')
            local = local_tag.get_text(strip=True) if local_tag else ""

            if "Tucuruí" not in local:
                continue

            # Preço
            preco_tag = card.find('div', class_='price-list__value')
            preco = preco_tag.get_text(strip=True) if preco_tag else "S/V"

            # Link
            link_tag = card.find('a', href=True)
            link = link_tag['href'] if link_tag else ""

            if link.startswith('/'):
                link = "https://fatalmodel.com" + link

            modelos[nome] = {
                "preco": preco,
                "link": link
            }

        return modelos

    # -----------------------------
    # Execução principal
    # -----------------------------
    def executar(self):
        agora = datetime.now().strftime('%d/%m %H:%M')
        self.enviar_telegram(
            f"🟢 *Bot Fatal Tucuruí rodando*\n⏰ {agora}"
        )

        memoria = self.carregar_memoria()
        modelos_atuais = self.buscar_modelos()

        nova_memoria = {}

        # -----------------------------
        # Modelos presentes
        # -----------------------------
        for nome, dados in modelos_atuais.items():

            if nome not in memoria:
                msg = (
                    f"✅ *NOVA MODELO EM TUCURUÍ*\n\n"
                    f"👤 {nome}\n"
                    f"💰 {dados['preco']}\n"
                    f"🔗 {dados['link']}"
                )
                self.enviar_telegram(msg)

                nova_memoria[nome] = {"ausencias": 0, "ativa": True}
                continue

            estado_antigo = memoria[nome]

            if not estado_antigo["ativa"]:
                msg = (
                    f"🔄 *MODELO DE VOLTA*\n\n"
                    f"👤 {nome}\n"
                    f"💰 {dados['preco']}\n"
                    f"🔗 {dados['link']}"
                )
                self.enviar_telegram(msg)

            nova_memoria[nome] = {"ausencias": 0, "ativa": True}

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


# -----------------------------
# Start
# -----------------------------
if __name__ == "__main__":
    bot = AlertFatal()
    bot.executar()
