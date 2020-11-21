import asyncio
import json
from logger import logger
import re
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from anyio import create_task_group

from gui import TkAppClosed, update_tk
from open_connection import open_connection


def process_button_click(
        host_entry,
        port_entry,
        username_entry,
        request_info_queue
):
    host = host_entry.get()
    port = port_entry.get()
    username = username_entry.get()
    request_info_queue.put_nowait((host, port, username))
    username.delete(0, tk.END)


async def register(host, port, user_name):
    async with open_connection(host, port) as (reader, writer):
        server_response = await reader.readline()
        logger.debug(repr(server_response.decode()))

        writer.write(b'\n')
        await writer.drain()
        server_response = await reader.readline()
        logger.debug(repr(server_response.decode()))

        filtered_nick = re.sub(r'(\\+n|\n|\\+)', '', user_name)
        message_to_send = f'{filtered_nick}\n'
        logger.debug(repr(message_to_send))
        writer.write(message_to_send.encode())
        await writer.drain()

        server_response = await reader.readline()
        logger.debug(repr(server_response.decode()))
        user_features = json.loads(server_response)
        try:
            user_token = user_features['account_hash']
        except (AttributeError, KeyError):
            user_token = None

    return user_token


async def draw(request_info_queue, new_user_hash_queue):
    root = tk.Tk()
    root.title('Регистрация в чат Майнкрафтера')
    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    host_entry = tk.Entry(width=20)
    port_entry = tk.Entry(width=20)
    user_name_entry = tk.Entry(width=20)
    sign_up_button = tk.Button(text='Регистрация')
    messages_window = ScrolledText(root_frame, wrap='none')
    user_hash = tk.Label(width=20, bg='black', fg='white')

    sign_up_button.bind(
        'Sign Up',
        lambda event: process_button_click(
            host_entry,
            port_entry,
            user_name_entry,
            request_info_queue
        )
    )

    host_entry.pack()
    port_entry.pack()
    user_name_entry.pack()
    sign_up_button.pack()
    messages_window.pack()
    user_hash.pack()

    async with create_task_group() as task_group:
        await task_group.spawn(update_tk, root_frame)


def main():
    try:
        request_info_queue = asyncio.Queue()
        new_user_hash_queue = asyncio.Queue()
        main_coroutine = draw(request_info_queue, new_user_hash_queue)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main_coroutine)
    except (KeyboardInterrupt, TkAppClosed):
        return


if __name__ == '__main__':
    main()
