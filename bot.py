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
        self.site = 'https://fatalmodel.com/acompanhantes-tucurui-pa'
        self.db_file = 'modelos_conhecidas.json'
        self.AUSENCIAS_MAX = 2  # confirma saída após 2 execuções

    # -----------------------------
    # Persistência
    # -----------------------------
    def carregar_memoria(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def salvar_memoria(self, dados):
        with open(self.db_file, 'w') as f:
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
    # Scraping ROBUSTO
    # -----------------------------
    def buscar_modelos(self):
        scraper = CloudScraper.create_scraper()
        req = scraper.get(self.site, timeout=30)

        if req.status_code != 200:
            raise Exception(f"Erro HTTP {req.status_code}")

        soup = BeautifulSoup(req.text, 'html.parser')

        modelos = {}

        # pega TODOS os links de acompanhantes
        links = soup.select('a[href^="/acompanhante/"]')

        for a in links:
            h2 = a.find('h2')
            if not h2:
                continue

            nome = h2.get_text(strip=True)
            if not nome:
                continue

            link = a.get('href')
            if link.startswith('/'):
                link = 'https://fatalmodel.com' + link

            # tenta pegar preço (se existir)
            card = a.find_parent('div', class_='shadow-listing-cards')
            preco = "S/V"
            if card:
                preco_div = card.select_one('.price-list__value')
                if preco_div:
                    preco = preco_div.get_text(strip=True)

            modelos[nome] = {
                'link': link,
                'preco': preco
            }

        return modelos

    # -----------------------------
    # Execução principal
    # -----------------------------
    def executar(self):
        agora = datetime.now().strftime('%d/%m %H:%M')
        self.enviar_telegram(f"🟢 *Monitor Fatal Tucuruí ativo*\n⏰ {agora}")

        memoria = self.carregar_memoria()
        modelos_atuais = self.buscar_modelos()

        # 🔍 ENVIA LISTA COMPLETA
        lista = sorted(modelos_atuais.keys())
        lista_msg = "📋 *MODELOS ENCONTRADAS EM TUCURUÍ*\n\n"
        lista_msg += f"Total: *{len(lista)}*\n\n"
        for nome in lista:
            lista_msg += f"• {nome}\n"

        self.enviar_telegram(lista_msg)

        nova_memoria = {}

        # -----------------------------
        # Modelos presentes
        # -----------------------------
        for nome, dados in modelos_atuais.items():
            if nome not in memoria:
                self.enviar_telegram(
                    f"✅ *NOVA MODELO EM TUCURUÍ*\n\n"
                    f"👤 {nome}\n"
                    f"💰 {dados['preco']}\n"
                    f"🔗 {dados['link']}"
                )
                nova_memoria[nome] = {"ausencias": 0, "ativa": True}
                continue

            if not memoria[nome]["ativa"]:
                self.enviar_telegram(
                    f"🔄 *MODELO DE VOLTA*\n\n"
                    f"👤 {nome}\n"
                    f"💰 {dados['preco']}\n"
                    f"🔗 {dados['link']}"
                )

            nova_memoria[nome] = {"ausencias": 0, "ativa": True}

        # -----------------------------
        # Modelos ausentes
        # -----------------------------
        for nome, estado in memoria.items():
            if nome not in modelos_atuais:
                faltas = estado["ausencias"] + 1

                if estado["ativa"] and faltas >= self.AUSENCIAS_MAX:
                    self.enviar_telegram(
                        f"❌ *MODELO AUSENTE (confirmado)*\n\n"
                        f"👤 {nome}\n"
                        f"⏳ Ausente há ~{faltas * 50} minutos"
                    )
                    nova_memoria[nome] = {"ausencias": faltas, "ativa": False}
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
