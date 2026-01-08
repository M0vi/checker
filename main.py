import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import unicodedata
from lxml import html

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

MAX_CONCURRENT_TASKS = 100
EXTRACTION_WORKERS = 20
TIMEOUT_PADRAO = 4

def load_proxies(filename):
    try:
        if not os.path.exists(filename): return None
        with open(filename, 'r') as file:
            proxies = file.read().splitlines()
        return cycle(proxies) if proxies else None
    except: return None

def remove_special_characters(username):
    nfkd = unicodedata.normalize('NFKD', username)
    return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])

async def fetch_aleatorios_org(session, proxy):
    url = "https://www.aleatorios.org/substantivos.php"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36'}
    try:
        async with session.get(url, proxy=f"http://{proxy}", timeout=TIMEOUT_PADRAO, headers=headers) as response:
            if response.status == 200:
                content = await response.read()
                tree = html.fromstring(content)
                palavra = tree.xpath('/html/body/div[2]/section/section[1]/div/div/h2/text()')
                if palavra:
                    clean = remove_special_characters(palavra[0].strip().replace(" ", ""))
                    return clean
    except:
        pass
    return None

async def validate_username(session, semaphore, username, proxy, valid_file):
    async with semaphore:
        if not username or len(username) < 3 or len(username) > 20:
            return
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
                    elif code == 2:
                        print(f"{Fore.YELLOW}[FILTRO] {username}{Style.RESET_ALL}")
        except:
            pass

async def extraction_worker(session, semaphore, proxies, valid_file):
    while True:
        proxy_miner = next(proxies)
        palavra = await fetch_aleatorios_org(session, proxy_miner)
        if palavra:
            proxy_validator = next(proxies)
            asyncio.create_task(validate_username(session, semaphore, palavra, proxy_validator, valid_file))
        await asyncio.sleep(0.01)

async def start_mass_check(usernames, proxies):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    async with aiohttp.ClientSession() as session:
        with open('valid.txt', 'a') as f:
            tasks = [asyncio.create_task(validate_username(session, semaphore, name.strip(), next(proxies), f)) for name in usernames]
            await asyncio.gather(*tasks)

async def main():
    if not os.path.exists('valid.txt'): open('valid.txt', 'w').close()
    proxies = load_proxies("proxies.txt")
    if not proxies:
        print(f"{Fore.RED}Erro: 'proxies.txt' inexistente!{Style.RESET_ALL}")
        return
    while True:
        print(f"\n{Fore.CYAN}--- ROBLOX MINER ---")
        print(f"1. Manual\n2. Lista/Link\n3. MINERAR\n0. Sair")
        choice = input(f"{Fore.CYAN}>{Style.RESET_ALL} ")
        if choice == '1':
            name = input("Nome: ")
            async with aiohttp.ClientSession() as s:
                await validate_username(s, asyncio.Semaphore(1), name, next(proxies), open('valid.txt', 'a'))
        elif choice == '2':
            path = input("Arquivo ou Link: ").strip()
            if path.startswith("http"):
                async with aiohttp.ClientSession() as s:
                    async with s.get(path) as r: 
                        await start_mass_check((await r.text()).splitlines(), proxies)
            else:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f: 
                        await start_mass_check(f.read().splitlines(), proxies)
        elif choice == '3':
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
            connector = aiohttp.TCPConnector(force_close=True, limit=MAX_CONCURRENT_TASKS)
            async with aiohttp.ClientSession(connector=connector) as session:
                with open('valid.txt', 'a') as vf:
                    workers = [asyncio.create_task(extraction_worker(session, semaphore, proxies, vf)) for _ in range(EXTRACTION_WORKERS)]
                    await asyncio.gather(*workers)
        elif choice == '0': break

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
