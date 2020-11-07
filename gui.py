import asyncio
from enum import Enum
import json
import re
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import aiofiles

from open_connection import open_connection
from logger import logger


class TkAppClosed(Exception):
    pass


class ReadConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(Enum):
    INITIATED = 'устанавливаем соединение'
    ESTABLISHED = 'соединение установлено'
    CLOSED = 'соединение закрыто'

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname):
        self.nickname = nickname


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


def display_message(panel, message):
    panel['state'] = 'normal'
    if panel.index('end-1c') != '1.0':
        panel.insert('end', '\n')
    panel.insert('end', message.strip())
    # TODO сделать промотку умной, чтобы не мешала просматривать историю сообщений
    # ScrolledText.frame
    # ScrolledText.vbar
    panel.yview(tk.END)
    panel['state'] = 'disabled'


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def update_conversation_history(panel, messages_queue):
    while True:
        msg = await messages_queue.get()
        display_message(panel, msg)


async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, read_label, write_label = status_labels

    read_label['text'] = f'Чтение: нет соединения'
    write_label['text'] = f'Отправка: нет соединения'
    nickname_label['text'] = f'Имя пользователя: неизвестно'

    while True:
        msg = await status_updates_queue.get()
        if isinstance(msg, ReadConnectionStateChanged):
            read_label['text'] = f'Чтение: {msg}'

        if isinstance(msg, SendingConnectionStateChanged):
            write_label['text'] = f'Отправка: {msg}'

        if isinstance(msg, NicknameReceived):
            nickname_label['text'] = f'Имя пользователя: {msg.nickname}'


async def send_messages(host, port, sending_queue):
    while True:
        sending_message = await sending_queue.get()
        logger.debug(f'Пользователь написал: {sending_message}')
        async with open_connection(host, port) as (reader, writer):
            server_response = await reader.readline()
            logger.debug(repr(server_response.decode()))
            filtered_message = re.sub(r'\n\n', '', sending_message)
            writer.write((filtered_message + '\n').encode())
            await writer.drain()
            writer.write(b'\n')
            await writer.drain()
            server_response = await reader.readline()
            logger.debug(repr(server_response.decode()))


async def read_msgs(message_queue, queue_for_history, host, port):
    async with open_connection(host, port) as (reader, writer):
        while True:
            received_data = await reader.readline()
            message = received_data.decode()
            message_queue.put_nowait(message)
            queue_for_history.put_nowait(message)


async def save_messages(filepath, history_queue):
    while True:
        new_message = await history_queue.get()
        try:
            async with aiofiles.open(filepath, 'a') as chat_history_file:
                await chat_history_file.write(new_message)
        except FileNotFoundError:
            logger.error(f'Can not write messages to the file {filepath}')
            return


async def authorize(reader, writer, token):
    server_response = await reader.readline()
    logger.debug(repr(server_response.decode()))
    logger.debug(repr(token))
    writer.write(f'{token}\n'.encode())
    await writer.drain()
    server_response = await reader.readline()
    decoded_response = server_response.decode()
    logger.debug(repr(decoded_response))
    try:
        user_features = json.loads(server_response)
    except json.JSONDecodeError:
        logger.error(
            f'Can not parse to JSON the server response: {decoded_response}.'
        )
        user_features = None
    return user_features


def create_status_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tk.X)

    connections_frame = tk.Frame(status_frame)
    connections_frame.pack(side="left")

    nickname_label = tk.Label(
        connections_frame,
        height=1,
        fg='grey',
        font='arial 10',
        anchor='w'
    )
    nickname_label.pack(side="top", fill=tk.X)

    status_read_label = tk.Label(
        connections_frame,
        height=1,
        fg='grey',
        font='arial 10',
        anchor='w'
    )
    status_read_label.pack(side="top", fill=tk.X)

    status_write_label = tk.Label(
        connections_frame,
        height=1,
        fg='grey',
        font='arial 10',
        anchor='w'
    )
    status_write_label.pack(side="top", fill=tk.X)

    return nickname_label, status_read_label, status_write_label


async def draw(
        input_arguments,
        messages_queue,
        history_queue,
        sending_queue,
        status_updates_queue
):
    root = tk.Tk()

    root.title('Чат Майнкрафтера')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    status_labels = create_status_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    input_field.bind(
        "<Return>",
        lambda event: process_new_message(input_field, sending_queue)
    )

    send_button = tk.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_new_message(
        input_field,
        sending_queue
    )
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap='none')
    conversation_panel.pack(side="top", fill="both", expand=True)

    history_filepath = input_arguments.history_filepath
    try:
        async with aiofiles.open(history_filepath, 'r') as file:
            chat_history = await file.readlines()
            [display_message(conversation_panel, msg) for msg in chat_history]
    except FileNotFoundError:
        logger.warning(f'Can not open chat history file: {history_filepath}.')

    server_host = input_arguments.host
    reading_port = input_arguments.reading_port
    sending_port = input_arguments.sending_port
    token = input_arguments.token

    async with open_connection(server_host, sending_port) as (reader, writer):
        user_features = await authorize(reader, writer, token)
    if not user_features:
        logger.error('Не удалось получить свойства юзера.')
        logger.error('Проверьте токен юзера и номер порта сервера.')
        return
    print(f'Выполнена авторизация. Пользователь {user_features["nickname"]}')

    await asyncio.gather(
        update_tk(root_frame),
        update_conversation_history(conversation_panel, messages_queue),
        update_status_panel(status_labels, status_updates_queue),
        send_messages(server_host, sending_port, sending_queue),
        read_msgs(messages_queue, history_queue, server_host, reading_port),
        save_messages(input_arguments.history_filepath, history_queue)
    )
