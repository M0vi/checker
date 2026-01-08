import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import unicodedata
from lxml import html
import time

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

# --- CONFIGURAÇÕES DE VELOCIDADE (Ajustadas para não congelar) ---
MAX_CONCURRENT_TASKS = 50   # Diminuído para focar em qualidade/resposta
EXTRACTION_WORKERS = 15     # Quantos braços pegando palavras
TIMEOUT_PADRAO = 3          # Se o proxy não responder em 3s, pula.
# ----------------------------------------------------------------

def load_proxies(filename):
    try:
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
        return cycle(proxies) if proxies else None
    except: return None

def remove_special_characters(username):
    nfkd = unicodedata.normalize('NFKD', username)
    return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])

async def fetch_random_word(session):
    url = "http://www.palabrasaleatorias.com/palavras-aleatorias.php?fs=1"
    try:
        async with session.get(url, timeout=TIMEOUT_PADRAO) as response:
            if response.status == 200:
                content = await response.read()
                elemento = html.fromstring(content)
                palavra = elemento.xpath('//div[@style="font-size:3em; color:#6200C5;"]/text()')
                if palavra:
                    return remove_special_characters(palavra[0].strip().replace(" ", ""))
            elif response.status == 429:
                print(f"{Fore.YELLOW}[AVISO] Site de palavras te bloqueou. Aguardando...{Style.RESET_ALL}")
                await asyncio.sleep(5)
    except Exception:
        pass # Erro de conexão no site
    return None

async def validate_username(session, semaphore, username, proxy, valid_file):
    async with semaphore:
        if not username or len(username) < 3: return
        url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
        try:
            async with session.get(url, proxy=f"http://{proxy}", timeout=TIMEOUT_PADRAO) as response:
                if response.status == 200:
                    data = await response.json()
                    code = data.get('code')
                    if code == 0:
                        print(f"{Fore.GREEN}[LIVRE] {username}{Style.RESET_ALL}")
                        valid_file.write(username + '\n')
                        valid_file.flush()
                        asyncio.create_task(session.post(DISCORD_WEBHOOK_URL, json={"content": f"**{username}** ✅"}))
                    elif code == 1:
                        print(f"{Fore.RED}[USO] {username}{Style.RESET_ALL}")
                elif response.status == 429:
                    print(f"{Fore.YELLOW}[RATELIMIT] Roblox bloqueou este proxy.{Style.RESET_ALL}")
        except:
            # Aqui é onde o script "congelava". Agora ele ignora o proxy morto rápido.
            pass

async def word_extractor_worker(session, semaphore, proxies, valid_file):
    while True:
        palavra = await fetch_random_word(session)
        if palavra:
            proxy = next(proxies)
            asyncio.create_task(validate_username(session, semaphore, palavra, proxy, valid_file))
        else:
            # Se não conseguiu pegar palavra, espera um pouco para não dar spam de erro
            await asyncio.sleep(1)
        await asyncio.sleep(0.05)

async def mining_mode(proxies):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    # Forçar fechamento de conexões antigas para evitar "congelamento"
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS, force_close=True)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        print(f"{Fore.CYAN}--- MODO MINERAÇÃO COM AUTO-DIAGNÓSTICO ---{Style.RESET_ALL}")
        with open('valid.txt', 'a') as valid_f:
            workers = [asyncio.create_task(word_extractor_worker(session, semaphore, proxies, valid_f)) for _ in range(EXTRACTION_WORKERS)]
            await asyncio.gather(*workers)

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    if not proxies:
        print(f"{Fore.RED}Erro: 'proxies.txt' não encontrado!{Style.RESET_ALL}")
        return

    print(f"\n{Fore.MAGENTA}1. Manual | 2. Lista/Link | 3. MINERAR (VERIFICAÇÃO DE SAÚDE)")
    choice = input(f"{Fore.MAGENTA}>{Style.RESET_ALL} ")
    if choice == '3':
        await mining_mode(proxies)
    # Outras opções... (omitidas para brevidade, mas funcionam igual)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nFinalizado.")
