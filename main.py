import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import unicodedata
from lxml import html

# Webhook mantido conforme solicitado
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

MAX_CONCURRENT_TASKS = 150 

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
                # Remove espaços e caracteres especiais para o Roblox
                return remove_special_characters(palavra[0].strip().replace(" ", ""))
            return None
    except:
        return None

async def send_to_discord_webhook(session, username):
    data = {"content": f"**{username}** ✅"}
    try:
        async with session.post(DISCORD_WEBHOOK_URL, json=data) as response:
            return response.status == 204
    except:
        return False

async def validate_username(session, semaphore, username, proxy, valid_file):
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
                        await send_to_discord_webhook(session, username)
                    elif code == 1:
                        print(f"{Fore.RED}[EM USO] {username}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}[FILTRO] {username}{Style.RESET_ALL}")
                elif response.status == 429:
                    # Rate limit no Roblox
                    await asyncio.sleep(2)
        except:
            pass

async def start_checking(usernames, proxies):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS)
    async with aiohttp.ClientSession(connector=connector) as session:
        with open('valid.txt', 'a') as valid_f:
            tasks = [asyncio.create_task(validate_username(session, semaphore, name, next(proxies), valid_f)) for name in usernames]
            await asyncio.gather(*tasks)

async def mining_mode(proxies):
    """Loop infinito de busca e validação"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    print(f"{Fore.CYAN}Iniciando Mineração Infinita... (CTRL+C para parar){Style.RESET_ALL}")
    
    async with aiohttp.ClientSession() as session:
        with open('valid.txt', 'a') as valid_f:
            while True:
                # Busca uma palavra
                palavra = await fetch_random_word(session)
                if palavra:
                    # Valida imediatamente
                    proxy = next(proxies)
                    asyncio.create_task(validate_username(session, semaphore, palavra, proxy, valid_f))
                
                # Pequena pausa para não travar o processador do celular
                await asyncio.sleep(0.1)

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    if not proxies:
        print(f"{Fore.RED}Erro: 'proxies.txt' não encontrado!{Style.RESET_ALL}")
        return

    while True:
        print(f"\n{Fore.MAGENTA}1. Nome Manual")
        print(f"2. Lista Local ou Link (.txt)")
        print(f"3. Gerar Qtd Específica de Palavras")
        print(f"4. MINERAR INFINITO (Loop de Palavras)")
        print(f"0. Sair")
        choice = input(f"{Fore.MAGENTA}>{Style.RESET_ALL} ")

        if choice == '1':
            username = input("Nome: ")
            async with aiohttp.ClientSession() as session:
                await validate_username(session, asyncio.Semaphore(1), username, next(proxies), open('valid.txt', 'a'))
        
        elif choice == '2':
            path_or_url = input("Arquivo ou Link: ").strip()
            if path_or_url.startswith("http"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(path_or_url) as r:
                        await start_checking((await r.text()).splitlines(), proxies)
            else:
                with open(path_or_url, "r", encoding="utf-8") as f:
                    await start_checking(f.read().splitlines(), proxies)

        elif choice == '3':
            qtd = int(input("Quantas palavras? "))
            async with aiohttp.ClientSession() as session:
                palavras = []
                for _ in range(qtd):
                    p = await fetch_random_word(session)
                    if p: palavras.append(p)
                await start_checking(palavras, proxies)

        elif choice == '4':
            await mining_mode(proxies)

        elif choice == '0': break

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Finalizado.{Style.RESET_ALL}")
