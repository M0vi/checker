import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style, init
import os
import unicodedata
from lxml import html
import sys

# Inicializa o Colorama para Windows
init(autoreset=True)

# Webhook configurado
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

# --- CONFIGURAÇÕES ---
MAX_CONCURRENT_TASKS = 60
EXTRACTION_WORKERS = 12
TIMEOUT_PADRAO = 5
# ---------------------

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_banner():
    clear()
    print(f"""
    {Fore.CYAN}╔══════════════════════════════════════════════════════╗
    ║             {Fore.MAGENTA}ROBLOX USERNAME MINER v2.0{Fore.CYAN}               ║
    ║        {Fore.WHITE}Status: {Fore.GREEN}ONLINE{Fore.CYAN} | Proxies: {Fore.YELLOW}ATIVOS{Fore.CYAN} | Site: {Fore.YELLOW}PROTEGIDO{Fore.CYAN} ║
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
    """Pega uma palavra do site usando proxy para ocultar seu IP"""
    url = "http://www.palabrasaleatorias.com/palavras-aleatorias.php?fs=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'}
    try:
        async with session.get(url, proxy=f"http://{proxy}", timeout=TIMEOUT_PADRAO, headers=headers) as response:
            if response.status == 200:
                content = await response.read()
                elemento = html.fromstring(content)
                palavra = elemento.xpath('//div[@style="font-size:3em; color:#6200C5;"]/text()')
                if palavra:
                    clean = remove_special_characters(palavra[0].strip().replace(" ", ""))
                    return clean
            return None
    except:
        return None

async def validate_username(session, semaphore, username, proxy, valid_file):
    """Valida o nome no Roblox"""
    async with semaphore:
        username = username.strip()
        if not username or len(username) < 3 or len(username) > 20:
            return

        url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
        try:
            async with session.get(url, proxy=f"http://{proxy}", timeout=TIMEOUT_PADRAO) as response:
                if response.status == 200:
                    data = await response.json()
                    code = data.get('code')
                    if code == 0:
                        print(f"{Fore.GREEN}[DISPONÍVEL] {username}{Style.RESET_ALL}")
                        valid_file.write(username + '\n')
                        valid_file.flush()
                        asyncio.create_task(session.post(DISCORD_WEBHOOK_URL, json={"content": f"**{username}** ✅"}))
                    elif code == 1:
                        print(f"{Fore.RED}[EM USO] {username}{Style.RESET_ALL}")
                    elif code == 2:
                        print(f"{Fore.YELLOW}[FILTRADO] {username}{Style.RESET_ALL}")
        except:
            pass

async def word_extractor_worker(session, semaphore, proxies, valid_file):
    """Worker para mineração infinita com extração protegida"""
    while True:
        palavra = await fetch_random_word(session, next(proxies))
        if palavra:
            asyncio.create_task(validate_username(session, semaphore, palavra, next(proxies), valid_file))
        await asyncio.sleep(0.1)

async def start_checking_list(usernames, proxies):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        with open('valid.txt', 'a') as valid_f:
            print(f"{Fore.CYAN}\n[!] Processando {len(usernames)} nomes...{Style.RESET_ALL}")
            tasks = [asyncio.create_task(validate_username(session, semaphore, name, next(proxies), valid_f)) for name in usernames]
            await asyncio.gather(*tasks)
            print(f"{Fore.GREEN}\n[✓] Lista finalizada.{Style.RESET_ALL}")
            input("Pressione Enter para voltar ao menu...")

async def mining_mode(proxies):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        print(f"{Fore.MAGENTA}\n[!] MODO MINERADOR ATIVADO (CTRL+C para parar){Style.RESET_ALL}")
        with open('valid.txt', 'a') as valid_f:
            workers = [asyncio.create_task(word_extractor_worker(session, semaphore, proxies, valid_f)) for _ in range(EXTRACTION_WORKERS)]
            try:
                await asyncio.gather(*workers)
            except asyncio.CancelledError:
                pass

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    
    if not proxies:
        draw_banner()
        print(f"{Fore.RED}ERRO: Crie um arquivo 'proxies.txt' com seus proxies antes de iniciar!{Style.RESET_ALL}")
        return

    while True:
        draw_banner()
        print(f" {Fore.WHITE}[{Fore.MAGENTA}1{Fore.WHITE}] Checagem Única (Manual)")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}2{Fore.WHITE}] Carregar Lista de Usuários (.txt ou Link)")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}3{Fore.WHITE}] Minerador Turbo (Palavras Aleatórias)")
        print(f" {Fore.WHITE}[{Fore.MAGENTA}0{Fore.WHITE}] Sair do Programa")
        
        choice = input(f"\n {Fore.CYAN}Seleção {Fore.WHITE}> ")
        
        if choice == '1':
            name = input(f" {Fore.YELLOW}Digite o nome: ")
            async with aiohttp.ClientSession() as session:
                await validate_username(session, asyncio.Semaphore(1), name, next(proxies), open('valid.txt', 'a'))
            input("\nPronto! Enter para continuar...")
        
        elif choice == '2':
            path_or_url = input(f" {Fore.YELLOW}Arquivo ou Link: ").strip()
            if path_or_url.startswith("http"):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(path_or_url) as r:
                            content = await r.text()
                            await start_checking_list(content.splitlines(), proxies)
                except Exception as e: print(f"Erro: {e}")
            else:
                if os.path.exists(path_or_url):
                    with open(path_or_url, "r", encoding="utf-8") as f:
                        await start_checking_list(f.read().splitlines(), proxies)
                else: print("Arquivo não encontrado.")

        elif choice == '3':
            await mining_mode(proxies)
            
        elif choice == '0':
            print(f"{Fore.YELLOW}Saindo...{Style.RESET_ALL}")
            sys.exit()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Operação interrompida pelo usuário.{Style.RESET_ALL}")
