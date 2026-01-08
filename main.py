import aiohttp
import asyncio
from itertools import cycle
from colorama import Fore, Style
import os
import random
import unicodedata


DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1458653748820967437/xgHjLemSxx9XLGnV2DfRUwAukKmkgGAyZx8QxQHzHmnzxXQhKbtgNEgKk0zlTsTY0Ply"  


def load_proxies(filename):
    with open(filename, 'r') as file:
        proxies = file.read().splitlines()
    return cycle(proxies)


def remove_special_characters(username):
    nfkd = unicodedata.normalize('NFKD', username)
    return ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])


async def send_to_discord_webhook(username):
    """Envia o nome de usuário válido para o webhook do Discord"""
    data = {"content": f"**{username}** ✅"}
    async with aiohttp.ClientSession() as session:
        async with session.post(DISCORD_WEBHOOK_URL, json=data) as response:
            if response.status == 204:
                print(f"{Fore.CYAN}Enviado '{username}' para o Discord!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Falha ao enviar '{username}' para o Discord (Status: {response.status}){Style.RESET_ALL}")


async def validate_username(session, username, proxy):
    username = remove_special_characters(username)  
    url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
    proxy_url = f"http://{proxy}"
    try:
        async with session.get(url, proxy=proxy_url) as response:
            if response.status == 200:
                data = await response.json()
                if data['code'] == 0:
                    print(f"{Fore.GREEN}O usuário '{username}' está disponível!{Style.RESET_ALL}")
                    with open('valid.txt', 'a') as file:
                        file.write(username + '\n')
                    print(f"{Fore.CYAN}Salvo '{username}' para 'valid.txt'{Style.RESET_ALL}")
                    
                    # Envia para o webhook do Discord
                    await send_to_discord_webhook(username)

                elif data['code'] == 1:
                    print(f"{Fore.RED}O usuário '{username}' já está em uso{Style.RESET_ALL}")
                elif data['code'] == 2:
                    print(f"{Fore.RED}O usuário '{username}' é inapropriado{Style.RESET_ALL}")
                elif data['code'] == 10:
                    print(f"{Fore.YELLOW}O usuário '{username}' provavelmente contém informações privadas{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Falha ao checar usuário '{username}' (Status: {response.status}){Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Falha ao checar usuário '{username}' com o proxy {proxy}: {e}{Style.RESET_ALL}")


async def validate_usernames_from_file(filename, proxies):
    async with aiohttp.ClientSession() as session:
        with open(filename, "r", encoding="utf-8") as file:
            usernames = file.read().splitlines()

        random.shuffle(usernames)

        tasks = []
        for username in usernames:
            username = remove_special_characters(username)
            proxy = next(proxies)
            tasks.append(validate_username(session, username, proxy))
        await asyncio.gather(*tasks)


async def main():
    open('valid.txt', 'w').close()

    proxies = load_proxies("proxies.txt")
    while True:
        print(f"{Fore.MAGENTA}[{Fore.RESET}+{Fore.MAGENTA}]{Fore.RESET} Escolha uma opção:")
        print(f"{Fore.MAGENTA}[{Fore.RESET}1{Fore.MAGENTA}]{Fore.RESET} Colocar nome manualmente")
        print(f"{Fore.MAGENTA}[{Fore.RESET}2{Fore.MAGENTA}]{Fore.RESET} Checar lista de nomes")
        print(f"{Fore.MAGENTA}[{Fore.RESET}0{Fore.MAGENTA}]{Fore.RESET} Sair")
        choice = input(f"{Fore.MAGENTA}[{Fore.RESET}>{Fore.MAGENTA}]{Fore.RESET} ")
        if choice == '1':
            username = input(f"{Fore.MAGENTA}[{Fore.RESET}+{Fore.MAGENTA}]{Fore.RESET} Digite um nome: ")
            async with aiohttp.ClientSession() as session:
                proxy = next(proxies)
                await validate_username(session, username, proxy)
        elif choice == '2':
            filename = input(f"{Fore.MAGENTA}[{Fore.RESET}+{Fore.MAGENTA}]{Fore.RESET} Digite o nome da pasta (deve incluir o formato da extensão; tipo .txt): ")
            await validate_usernames_from_file(filename, proxies)
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}Inválido{Style.RESET_ALL}")


if __name__ == '__main__':
    asyncio.run(main())
