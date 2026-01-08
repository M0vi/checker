import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import unicodedata
from lxml import html

# Webhook mantido conforme solicitado
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

# --- CONFIGURAÇÕES DE VELOCIDADE ---
# No Termux, valores muito altos podem travar a rede do celular.
MAX_CONCURRENT_TASKS = 80   # Checagens simultâneas no Roblox
EXTRACTION_WORKERS = 10      # Trabalhadores pegando palavras do site
# -----------------------------------

def load_proxies(filename):
    try:
        if not os.path.exists(filename):
            return None
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
        return cycle(proxies) if proxies else None
    except Exception:
        return None

def remove_special_characters(username):
    nfkd = unicodedata.normalize('NFKD', username)
    return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])

async def fetch_random_word(session):
    """Pega uma palavra aleatória do site com tratamento de erro"""
    url = "http://www.palabrasaleatorias.com/palavras-aleatorias.php?fs=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'}
    try:
        async with session.get(url, timeout=5, headers=headers) as response:
            if response.status == 200:
                content = await response.read()
                elemento = html.fromstring(content)
                palavra = elemento.xpath('//div[@style="font-size:3em; color:#6200C5;"]/text()')
                if palavra:
                    # Limpa a palavra para o padrão Roblox
                    clean_name = remove_special_characters(palavra[0].strip().replace(" ", ""))
                    return clean_name
            elif response.status == 429:
                await asyncio.sleep(5) # Rate limit no site das palavras
    except:
        pass
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
                    code = data.get('code')
                    if code == 0:
                        print(f"{Fore.GREEN}[DISPONÍVEL] {username}{Style.RESET_ALL}")
                        valid_file.write(username + '\n')
                        valid_file.flush()
                        # Envia para o Discord em segundo plano
                        asyncio.create_task(session.post(DISCORD_WEBHOOK_URL, json={"content": f"**{username}** ✅"}))
                    elif code == 1:
                        print(f"{Fore.RED}[EM USO] {username}{Style.RESET_ALL}")
                    elif code == 2:
                        print(f"{Fore.YELLOW}[FILTRO] {username}{Style.RESET_ALL}")
                elif response.status == 429:
                    await asyncio.sleep(2) # Rate limit no Roblox
        except:
            pass

async def word_extractor_worker(session, semaphore, proxies, valid_file):
    """Loop de cada worker para minerar e checar"""
    while True:
        palavra = await fetch_random_word(session)
        if palavra:
            proxy = next(proxies)
            # Cria a tarefa de checagem e continua minerando
            asyncio.create_task(validate_username(session, semaphore, palavra, proxy, valid_file))
        await asyncio.sleep(0.1) # Pequena pausa para estabilidade

async def start_checking_list(usernames, proxies):
    """Checa uma lista pré-definida (arquivo ou link)"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS)
    async with aiohttp.ClientSession(connector=connector) as session:
        with open('valid.txt', 'a') as valid_f:
            tasks = []
            for name in usernames:
                tasks.append(asyncio.create_task(validate_username(session, semaphore, name, next(proxies), valid_f)))
            await asyncio.gather(*tasks)

async def mining_mode(proxies):
    """Modo de mineração infinita"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS)
    async with aiohttp.ClientSession(connector=connector) as session:
        print(f"{Fore.CYAN}--- MINERAÇÃO TURBO ATIVADA ---{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Workers ativos: {EXTRACTION_WORKERS}{Style.RESET_ALL}")
        with open('valid.txt', 'a') as valid_f:
            workers = []
            for _ in range(EXTRACTION_WORKERS):
                workers.append(asyncio.create_task(word_extractor_worker(session, semaphore, proxies, valid_f)))
            await asyncio.gather(*workers)

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    
    if not proxies:
        print(f"{Fore.RED}Erro: 'proxies.txt' não encontrado ou vazio!{Style.RESET_ALL}")
        return

    while True:
        print(f"\n{Fore.MAGENTA}[+]{Fore.RESET} 1. Nome Manual")
        print(f"{Fore.MAGENTA}[+]{Fore.RESET} 2. Checar Lista ou Link (.txt)")
        print(f"{Fore.MAGENTA}[+]{Fore.RESET} 3. Minerador Turbo (Loop)")
        print(f"{Fore.MAGENTA}[+]{Fore.RESET} 0. Sair")
        
        choice = input(f"{Fore.MAGENTA}>{Fore.RESET} ")
        
        if choice == '1':
            name = input("Nome: ")
            async with aiohttp.ClientSession() as session:
                await validate_username(session, asyncio.Semaphore(1), name, next(proxies), open('valid.txt', 'a'))
        
        elif choice == '2':
            path = input("Arquivo ou Link: ").strip()
            if path.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(path) as r:
                        content = await r.text()
                        await start_checking_list(content.splitlines(), proxies)
            else:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        await start_checking_list(f.read().splitlines(), proxies)
                else:
                    print(f"{Fore.RED}Arquivo não encontrado.{Style.RESET_ALL}")

        elif choice == '3':
            await mining_mode(proxies)
            
        elif choice == '0':
            break

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Script finalizado pelo usuário.{Style.RESET_ALL}")
