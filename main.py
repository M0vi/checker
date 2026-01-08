import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import random
import unicodedata

# Webhook mantido conforme solicitado
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

MAX_CONCURRENT_TASKS = 150 

def load_proxies(filename):
    try:
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
        if not proxies:
            return None
        return cycle(proxies)
    except FileNotFoundError:
        return None

def remove_special_characters(username):
    nfkd = unicodedata.normalize('NFKD', username)
    return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])

async def send_to_discord_webhook(session, username):
    data = {"content": f"**{username}** ✅"}
    try:
        async with session.post(DISCORD_WEBHOOK_URL, json=data) as response:
            return response.status == 204
    except:
        return False

async def validate_username(session, semaphore, username, proxy, valid_file):
    async with semaphore:
        username = remove_special_characters(username).strip()
        if not username or len(username) < 3: # Roblox não aceita menos de 3
            return

        url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
        proxy_url = f"http://{proxy}"
        
        try:
            async with session.get(url, proxy=proxy_url, timeout=10) as response:
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
                    elif code == 2:
                        print(f"{Fore.YELLOW}[INAPROPRIADO] {username}{Style.RESET_ALL}")
                elif response.status == 429:
                    pass
        except:
            pass

async def start_checking(usernames, proxies):
    """Lógica central para processar a lista de nomes"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        with open('valid.txt', 'a') as valid_f:
            tasks = []
            print(f"{Fore.CYAN}Processando {len(usernames)} nomes...{Style.RESET_ALL}")
            for name in usernames:
                proxy = next(proxies)
                tasks.append(asyncio.create_task(validate_username(session, semaphore, name, proxy, valid_f)))
            
            await asyncio.gather(*tasks)

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    
    if not proxies:
        print(f"{Fore.RED}Erro: 'proxies.txt' não encontrado na pasta!{Style.RESET_ALL}")
        return

    while True:
        print(f"\n{Fore.MAGENTA}[+]{Fore.RESET} 1. Nome Manual")
        print(f"{Fore.MAGENTA}[+]{Fore.RESET} 2. Checar Lista (.txt ou Link)")
        print(f"{Fore.MAGENTA}[+]{Fore.RESET} 0. Sair")
        
        choice = input(f"{Fore.MAGENTA}>{Fore.RESET} ")
        
        if choice == '1':
            username = input("Nome: ")
            async with aiohttp.ClientSession() as session:
                await validate_username(session, asyncio.Semaphore(1), username, next(proxies), open('valid.txt', 'a'))
        
        elif choice == '2':
            path_or_url = input("Digite o nome do arquivo ou o Link: ").strip()
            
            # Verifica se é um link
            if path_or_url.startswith("http"):
                print(f"{Fore.YELLOW}Baixando lista do link...{Style.RESET_ALL}")
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(path_or_url) as resp:
                            content = await resp.text()
                            usernames = content.splitlines()
                            await start_checking(usernames, proxies)
                except Exception as e:
                    print(f"{Fore.RED}Erro ao baixar link: {e}{Style.RESET_ALL}")
            else:
                # Trata como arquivo local
                try:
                    with open(path_or_url, "r", encoding="utf-8") as f:
                        usernames = f.read().splitlines()
                        await start_checking(usernames, proxies)
                except FileNotFoundError:
                    print(f"{Fore.RED}Arquivo não encontrado.{Style.RESET_ALL}")
        
        elif choice == '0':
            break

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Finalizado.{Style.RESET_ALL}")
