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

# --- CONFIGURAÇÕES E ESTADO ---
config = {
    "max_tasks": 60,
    "extraction_workers": 12,
    "timeout": 5
}

# Cache para evitar checar a mesma palavra na mesma sessão
CHECKED_CACHE = set()
DUPLICATE_COUNT = 0

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_banner():
    clear()
    print(f"""
    {Fore.CYAN}╔══════════════════════════════════════════════════════╗
    ║             {Fore.MAGENTA}ROBLOX USERNAME MINER v3.0{Fore.CYAN}               ║
    ╠══════════════════════════════════════════════════════╣
    ║  {Fore.WHITE}Workers: {Fore.YELLOW}{config['extraction_workers']:<3}{Fore.CYAN} | Tasks: {Fore.YELLOW}{config['max_tasks']:<3}{Fore.CYAN} | Cache: {Fore.GREEN}{len(CHECKED_CACHE):<6}{Fore.CYAN} ║
    ╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """)

def load_proxies(filename):
    try:
        if not os.path.exists(filename):
            return None
        with open(filename, 'r') as file:
            proxies = [p.strip() for p in file.read().splitlines() if p.strip()]
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
    global DUPLICATE_COUNT
    
    # Verifica se a palavra já foi checada nesta sessão
    if username.lower() in CHECKED_CACHE:
        DUPLICATE_COUNT += 1
        return
    
    async with semaphore:
        CHECKED_CACHE.add(username.lower())
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
                elif response.status == 429:
                    # Se der Rate Limit, remove do cache para tentar novamente depois com outro proxy
                    CHECKED_CACHE.discard(username.lower())
        except:
            # Em caso de erro de conexão, remove do cache para não "perder" a palavra
            CHECKED_CACHE.discard(username.lower())

async def word_extractor_worker(session, semaphore, proxies, valid_file):
    while True:
        palavra = await fetch_random_word(session, next(proxies))
        if palavra:
            # Lança a validação como uma task separada para não travar o worker de extração
            asyncio.create_task(validate_username(session, semaphore, palavra, next(proxies), valid_file))
        await asyncio.sleep(0.05)

async def mining_mode(proxies):
    semaphore = asyncio.Semaphore(config['max_tasks'])
    connector = aiohttp.TCPConnector(limit=config['max_tasks'], force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        draw_banner()
        print(f"{Fore.MAGENTA}[!] MINERANDO... | Cache atual: {len(CHECKED_CACHE)} nomes")
        print(f"{Fore.CYAN}[CTRL+C] para voltar ao menu\n{Style.RESET_ALL}")
        
        with open('valid.txt', 'a') as valid_f:
            workers = [asyncio.create_task(word_extractor_worker(session, semaphore, proxies, valid_f)) for _ in range(config['extraction_workers'])]
            try:
                await asyncio.gather(*workers)
            except asyncio.CancelledError:
                pass
            except KeyboardInterrupt:
                for w in workers: w.cancel()

def settings_menu():
    draw_banner()
    print(f" {Fore.YELLOW}--- AJUSTES DE PERFORMANCE ---")
    try:
        config['extraction_workers'] = int(input(f" {Fore.WHITE}Workers de Extração [{config['extraction_workers']}]: ") or config['extraction_workers'])
        config['max_tasks'] = int(input(f" {Fore.WHITE}Tasks no Roblox [{config['max_tasks']}]: ") or config['max_tasks'])
        print(f"\n{Fore.GREEN}Configurações salvas!")
    except ValueError:
        print(f"\n{Fore.RED}Entrada inválida.")
    os.system('pause' if os.name == 'nt' else 'read -p "Pressione Enter..." -n1 -s')

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    
    if not proxies:
        draw_banner()
        print(f"{Fore.RED}ERRO: Coloque seus proxies em 'proxies.txt'{Style.RESET_ALL}")
        return

    while True:
        draw_banner()
        print(f" {Fore.WHITE}[{Fore.MAGENTA}1{Fore.WHITE}] Checagem Manual")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}2{Fore.WHITE}] {Fore.CYAN}INICIAR MINERAÇÃO TURBO")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}3{Fore.WHITE}] Configurar Workers")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}4{Fore.WHITE}] Limpar Cache de Sessão ({len(CHECKED_CACHE)})")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}0{Fore.WHITE}] Sair")
        
        choice = input(f"\n {Fore.CYAN}Opção {Fore.WHITE}> ")
        
        if choice == '1':
            name = input(f" {Fore.YELLOW}Nome: ")
            async with aiohttp.ClientSession() as session:
                await validate_username(session, asyncio.Semaphore(1), name, next(proxies), open('valid.txt', 'a'))
            input("\nConcluído. Enter...")
            
        elif choice == '2':
            await mining_mode(proxies)
            
        elif choice == '3':
            settings_menu()
            
        elif choice == '4':
            CHECKED_CACHE.clear()
            print(f"{Fore.GREEN}Cache limpo!")
            await asyncio.sleep(1)

        elif choice == '0':
            sys.exit()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
