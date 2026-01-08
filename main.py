import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import unicodedata
from lxml import html

# Webhook mantido conforme solicitado
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

# --- CONFIGURAÇÕES DE VELOCIDADE TURBO ---
MAX_CONCURRENT_TASKS = 300  # Quantas checagens de nomes ao mesmo tempo
EXTRACTION_WORKERS = 15     # Quantos "braços" pegando palavras do site simultaneamente
# -----------------------------------------

def load_proxies(filename):
    try:
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
        return cycle(proxies) if proxies else None
    except FileNotFoundError:
        return None

def remove_special_characters(username):
    nfkd = unicodedata.normalize('NFKD', username)
    return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])

async def fetch_random_word(session):
    """Pega uma palavra aleatória do site"""
    url = "http://www.palabrasaleatorias.com/palavras-aleatorias.php?fs=1"
    try:
        async with session.get(url, timeout=5) as response:
            content = await response.read()
            elemento = html.fromstring(content)
            palavra = elemento.xpath('//div[@style="font-size:3em; color:#6200C5;"]/text()')
            if palavra:
                return remove_special_characters(palavra[0].strip().replace(" ", ""))
    except:
        return None

async def validate_username(session, semaphore, username, proxy, valid_file):
    """Valida o nome no Roblox"""
    async with semaphore:
        if not username or len(username) < 3 or len(username) > 20:
            return

        url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
        try:
            async with session.get(url, proxy=f"http://{proxy}", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == 0:
                        print(f"{Fore.GREEN}[DISPONÍVEL] {username}{Style.RESET_ALL}")
                        valid_file.write(username + '\n')
                        valid_file.flush()
                        # Webhook em background para não travar a checagem
                        asyncio.create_task(session.post(DISCORD_WEBHOOK_URL, json={"content": f"**{username}** ✅"}))
                    elif data.get('code') == 1:
                        print(f"{Fore.RED}[EM USO] {username}{Style.RESET_ALL}")
        except:
            pass

async def word_extractor_worker(session, semaphore, proxies, valid_file):
    """Worker que fica em loop infinito pegando e mandando checar"""
    while True:
        palavra = await fetch_random_word(session)
        if palavra:
            proxy = next(proxies)
            # Manda para validação sem esperar ela terminar
            asyncio.create_task(validate_username(session, semaphore, palavra, proxy, valid_file))
        # Sem delay para velocidade máxima, apenas um yield para o loop
        await asyncio.sleep(0)

async def mining_mode(proxies):
    """Inicia múltiplos workers de extração ao mesmo tempo"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    # Connector otimizado para alto volume
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS, ttl_dns_cache=300)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        print(f"{Fore.CYAN}ATIVANDO MINERAÇÃO TURBO COM {EXTRACTION_WORKERS} WORKERS...{Style.RESET_ALL}")
        
        with open('valid.txt', 'a') as valid_f:
            # Cria a "equipe" de extração
            workers = []
            for _ in range(EXTRACTION_WORKERS):
                workers.append(asyncio.create_task(word_extractor_worker(session, semaphore, proxies, valid_f)))
            
            # Mantém os workers rodando
            await asyncio.gather(*workers)

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    if not proxies:
        print(f"{Fore.RED}Erro: 'proxies.txt' não encontrado!{Style.RESET_ALL}")
        return

    while True:
        print(f"\n{Fore.MAGENTA}1. Manual | 2. Lista/Link | 3. Qtd Específica | 4. MINERAR TURBO | 0. Sair")
        choice = input(f"{Fore.MAGENTA}>{Style.RESET_ALL} ")

        if choice == '1':
            username = input("Nome: ")
            async with aiohttp.ClientSession() as session:
                await validate_username(session, asyncio.Semaphore(1), username, next(proxies), open('valid.txt', 'a'))
        elif choice == '4':
            await mining_mode(proxies)
        elif choice == '0': break
        # (Outras opções 2 e 3 permanecem as mesmas do código anterior)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Parando minerador...{Style.RESET_ALL}")
