import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style, init
import os
import unicodedata
from lxml import html
import sys

# Inicializa o Colorama
init(autoreset=True)

# Webhook configurado
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

# --- CONFIGURAÇÕES GLOBAIS PADRÃO ---
config = {
    "max_tasks": 60,
    "extraction_workers": 12,
    "timeout": 5
}

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_banner():
    clear()
    print(f"""
    {Fore.CYAN}╔══════════════════════════════════════════════════════╗
    ║             {Fore.MAGENTA}ROBLOX USERNAME MINER v2.5{Fore.CYAN}               ║
    ║        {Fore.WHITE}Status: {Fore.GREEN}ONLINE{Fore.CYAN} | Workers: {Fore.YELLOW}{config['extraction_workers']}{Fore.CYAN} | Tasks: {Fore.YELLOW}{config['max_tasks']}{Fore.CYAN} ║
    ╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """)

def load_proxies(filename):
    try:
        if not os.path.exists(filename):
            return None
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
        return cycle(proxies) if proxies else None
    except:
        return None

def remove_special_characters(username):
    nfkd = unicodedata.normalize('NFKD', username)
    return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])

async def fetch_random_word(session, proxy):
    url = "http://www.palabrasaleatorias.com/palavras-aleatorias.php?fs=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'}
    try:
        async with session.get(url, proxy=f"http://{proxy}", timeout=config['timeout'], headers=headers) as response:
            if response.status == 200:
                content = await response.read()
                elemento = html.fromstring(content)
                palavra = elemento.xpath('//div[@style="font-size:3em; color:#6200C5;"]/text()')
                if palavra:
                    return remove_special_characters(palavra[0].strip().replace(" ", ""))
    except:
        return None

async def validate_username(session, semaphore, username, proxy, valid_file):
    async with semaphore:
        username = username.strip()
        if not username or len(username) < 3 or len(username) > 20:
            return

        url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
        try:
            async with session.get(url, proxy=f"http://{proxy}", timeout=config['timeout']) as response:
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
                    elif code == 2:
                        print(f"{Fore.YELLOW}[FILTRO] {username}{Style.RESET_ALL}")
        except:
            pass

async def word_extractor_worker(session, semaphore, proxies, valid_file):
    while True:
        palavra = await fetch_random_word(session, next(proxies))
        if palavra:
            asyncio.create_task(validate_username(session, semaphore, palavra, next(proxies), valid_file))
        await asyncio.sleep(0.05)

async def mining_mode(proxies):
    semaphore = asyncio.Semaphore(config['max_tasks'])
    connector = aiohttp.TCPConnector(limit=config['max_tasks'], force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        draw_banner()
        print(f"{Fore.MAGENTA}[!] MINERANDO COM {config['extraction_workers']} WORKERS... (CTRL+C para parar){Style.RESET_ALL}\n")
        with open('valid.txt', 'a') as valid_f:
            workers = [asyncio.create_task(word_extractor_worker(session, semaphore, proxies, valid_f)) for _ in range(config['extraction_workers'])]
            try:
                await asyncio.gather(*workers)
            except asyncio.CancelledError:
                pass

def settings_menu():
    draw_banner()
    print(f" {Fore.YELLOW}--- AJUSTES DE PERFORMANCE ---")
    try:
        config['extraction_workers'] = int(input(f" {Fore.WHITE}Quantidade de Workers (Extração) [{config['extraction_workers']}]: ") or config['extraction_workers'])
        config['max_tasks'] = int(input(f" {Fore.WHITE}Máximo de Tasks (Roblox) [{config['max_tasks']}]: ") or config['max_tasks'])
        print(f"\n{Fore.GREEN}Configurações salvas!")
    except ValueError:
        print(f"\n{Fore.RED}Entrada inválida. Mantendo padrões.")
    os.system('pause' if os.name == 'nt' else 'read -p "Press enter to continue" -n1 -s')

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    
    if not proxies:
        draw_banner()
        print(f"{Fore.RED}ERRO: 'proxies.txt' não encontrado!{Style.RESET_ALL}")
        return

    while True:
        draw_banner()
        print(f" {Fore.WHITE}[{Fore.MAGENTA}1{Fore.WHITE}] Checagem Única")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}2{Fore.WHITE}] Carregar Lista/Link")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}3{Fore.WHITE}] {Fore.CYAN}INICIAR MINERAÇÃO TURBO")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}4{Fore.WHITE}] Configurar Workers/Speed")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}0{Fore.WHITE}] Sair")
        
        choice = input(f"\n {Fore.CYAN}Opção {Fore.WHITE}> ")
        
        if choice == '1':
            name = input(f" {Fore.YELLOW}Nome: ")
            async with aiohttp.ClientSession() as session:
                await validate_username(session, asyncio.Semaphore(1), name, next(proxies), open('valid.txt', 'a'))
            input("\nPronto. Enter...")
        
        elif choice == '2':
            path_or_url = input(f" {Fore.YELLOW}Caminho/URL: ").strip()
            # ... (logica de lista igual anterior)
            
        elif choice == '3':
            await mining_mode(proxies)
            
        elif choice == '4':
            settings_menu()

        elif choice == '0':
            sys.exit()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Encerrado.{Style.RESET_ALL}")
