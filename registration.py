import asyncio
import json
from logger import logger
import re
import socket
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from anyio import create_task_group

from gui import TkAppClosed
from gui import update_conversation_history as update_scroll_panel, update_tk


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
    username_entry.delete(0, tk.END)


async def register(request_info_queue, new_user_hash_queue, log_queue):
    while True:
        host, port, user_name = await request_info_queue.get()
        server_address = f'{host}:{port}'
        log_msg = f'Установка соединения с сервером {server_address}'
        logger.debug(log_msg)
        log_queue.put_nowait(log_msg)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except socket.gaierror:
            log_msg = f'ОШИБКА. Нет соединения с сервером {server_address}'
            logger.error(log_msg)
            log_queue.put_nowait(log_msg)
            new_user_hash_queue.put_nowait('ОШИБКА. Нет соединения с сервером')
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
        log_queue.put_nowait(repr(server_response.decode()))
        user_features = json.loads(server_response)
        try:
            user_token = user_features['account_hash']
        except (AttributeError, KeyError):
            user_token = None

        new_user_hash_queue.put_nowait(user_token)


async def update_hash_label(user_hash_label, new_user_hash_queue):
    while True:
        user_hash = await new_user_hash_queue.get()
        user_hash_label['text'] = f'Хэш нового пользователя: {user_hash}'


async def draw(request_info_queue, new_user_hash_queue, log_queue):
    root = tk.Tk()
    root.title('Регистрация в чат Майнкрафтера')
    root_frame = tk.Frame(root)
    upper_frame = tk.Frame(root_frame)
    lower_frame = tk.Frame(root_frame)

    host_entry = tk.Entry(upper_frame, width=50)
    port_entry = tk.Entry(upper_frame, width=50)
    user_name_entry = tk.Entry(upper_frame, width=50)
    sign_up_button = tk.Button(upper_frame, text='Регистрация')
    user_hash_label = tk.Label(upper_frame, width=50, bg='black', fg='white')
    sign_up_button['command'] = lambda: process_button_click(
        host_entry,
        port_entry,
        user_name_entry,
        request_info_queue
    )

    log_panel = ScrolledText(lower_frame, wrap='none')
    log_panel.pack(side="bottom", fill="both", expand=True)

    root_frame.pack(fill="both", expand=True)
    upper_frame.pack()
    lower_frame.pack()
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
            new_user_hash_queue,
            log_queue
        )
        await task_group.spawn(
            update_hash_label,
            user_hash_label,
            new_user_hash_queue
        )
        await task_group.spawn(update_scroll_panel, log_panel, log_queue)


def main():
    try:
        request_info_queue = asyncio.Queue()
        new_user_hash_queue = asyncio.Queue()
        log_queue = asyncio.Queue()
        main_coroutine = draw(
            request_info_queue,
            new_user_hash_queue,
            log_queue
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main_coroutine)
    except (KeyboardInterrupt, TkAppClosed):
        return


if __name__ == '__main__':
    main()
