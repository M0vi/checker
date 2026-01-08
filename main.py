import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import random
import unicodedata

# Webhook mantido conforme solicitado
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"

# Ajuste este valor para controlar a velocidade. 
# 100-200 é ideal para Termux.
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
    """Envia o nome para o Discord reutilizando a sessão"""
    data = {"content": f"**{username}** ✅"}
    try:
        async with session.post(DISCORD_WEBHOOK_URL, json=data) as response:
            return response.status == 204
    except:
        return False

async def validate_username(session, semaphore, username, proxy, valid_file):
    """Valida o usuário respeitando o limite do semáforo"""
    async with semaphore:
        username = remove_special_characters(username).strip()
        if not username:
            return

        url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
        proxy_url = f"http://{proxy}"
        
        try:
            # Timeout curto para não travar em proxies lentos
            async with session.get(url, proxy=proxy_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    code = data.get('code')
                    
                    if code == 0:
                        print(f"{Fore.GREEN}[DISPONÍVEL] {username}{Style.RESET_ALL}")
                        valid_file.write(username + '\n')
                        valid_file.flush() # Salva no arquivo imediatamente
                        await send_to_discord_webhook(session, username)
                    elif code == 1:
                        print(f"{Fore.RED}[EM USO] {username}{Style.RESET_ALL}")
                    elif code == 2:
                        print(f"{Fore.YELLOW}[INAPROPRIADO] {username}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.WHITE}[FILTRO] {username} (Cód: {code}){Style.RESET_ALL}")
                elif response.status == 429:
                    # Opcional: print de aviso de rate limit
                    pass
        except:
            # Ignora erros de conexão/proxy para manter a velocidade
            pass

async def validate_usernames_from_file(filename, proxies):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    # Criamos uma única sessão para todas as requisições (muito mais rápido)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            with open(filename, "r", encoding="utf-8") as f, open('valid.txt', 'a') as valid_f:
                tasks = []
                print(f"{Fore.CYAN}Carregando tarefas... Aguarde.{Style.RESET_ALL}")
                
                for line in f:
                    proxy = next(proxies)
                    # Cria a tarefa em segundo plano
                    task = asyncio.create_task(validate_username(session, semaphore, line, proxy, valid_f))
                    tasks.append(task)
                
                if tasks:
                    print(f"{Fore.MAGENTA}Checando {len(tasks)} nomes...{Style.RESET_ALL}")
                    await asyncio.gather(*tasks)
                else:
                    print(f"{Fore.RED}Arquivo vazio.{Style.RESET_ALL}")
        except FileNotFoundError:
            print(f"{Fore.RED}Arquivo não encontrado.{Style.RESET_ALL}")

async def main():
    # Garante que o arquivo de válidos existe
    if not os.path.exists('valid.txt'):
        open('valid.txt', 'w').close()

    proxies = load_proxies("proxies.txt")
    if not proxies:
        print(f"{Fore.RED}Crie o arquivo 'proxies.txt' primeiro!{Style.RESET_ALL}")
        return

    while True:
        print(f"\n{Fore.MAGENTA}[+]{Fore.RESET} 1. Nome Manual")
        print(f"{Fore.MAGENTA}[+]{Fore.RESET} 2. Checar Lista (.txt)")
        print(f"{Fore.MAGENTA}[+]{Fore.RESET} 0. Sair")
        
        choice = input(f"{Fore.MAGENTA}>{Fore.RESET} ")
        
        if choice == '1':
            username = input("Nome: ")
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(1)
                with open('valid.txt', 'a') as vf:
                    await validate_username(session, sem, username, next(proxies), vf)
        elif choice == '2':
            filename = input("Nome do arquivo (ex: lista.txt): ")
            await validate_usernames_from_file(filename, proxies)
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}Opção inválida.{Style.RESET_ALL}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrompido pelo usuário.{Style.RESET_ALL}")
