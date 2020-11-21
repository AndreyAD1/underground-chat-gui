import asyncio
import json
from logger import logger
import re
import socket
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from anyio import create_task_group

from gui import TkAppClosed, update_tk


def process_button_click(
        host_entry,
        port_entry,
        username_entry,
        request_info_queue
):
    logger.debug('begin to process button click')
    host = host_entry.get()
    port = port_entry.get()
    username = username_entry.get()
    request_info_queue.put_nowait((host, port, username))
    username.delete(0, tk.END)


async def register(request_info_queue, new_user_hash_queue):
    while True:
        host, port, user_name = await request_info_queue.get()
        logger.debug('Begin to register')
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except socket.gaierror:
            new_user_hash_queue.put_nowait('Нет соединения с сервером')
            continue

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

        new_user_hash_queue.put_nowait(user_token)


async def update_hash_label(user_hash_label, new_user_hash_queue):
    while True:
        user_hash = await new_user_hash_queue.get()
        if user_hash is None:
            # process the error
            user_hash = 'ERROR'
        user_hash_label['text'] = f'Хэш нового пользователя: {user_hash}'


async def draw(request_info_queue, new_user_hash_queue):
    root = tk.Tk()
    root.title('Регистрация в чат Майнкрафтера')
    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    host_entry = tk.Entry(width=50)
    port_entry = tk.Entry(width=50)
    user_name_entry = tk.Entry(width=50)
    sign_up_button = tk.Button(text='Регистрация')
    user_hash_label = tk.Label(width=50, bg='black', fg='white')

    sign_up_button['command'] = lambda: process_button_click(
            host_entry,
            port_entry,
            user_name_entry,
            request_info_queue
        )

    host_entry.pack()
    port_entry.pack()
    user_name_entry.pack()
    sign_up_button.pack()
    user_hash_label.pack()

    async with create_task_group() as task_group:
        await task_group.spawn(update_tk, root_frame)
        await task_group.spawn(
            register,
            request_info_queue,
            new_user_hash_queue
        )
        await task_group.spawn(
            update_hash_label,
            user_hash_label,
            new_user_hash_queue
        )


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
