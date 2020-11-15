import asyncio
import json
import re

import aiofiles
from tkinter import messagebox

from logger import logger
from open_connection import open_connection
from statuses import NicknameReceived, ReadConnectionStateChanged
from statuses import SendingConnectionStateChanged


class InvalidToken(Exception):
    pass


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


async def send_messages(
        host,
        port,
        sending_queue,
        token,
        status_msgs_queue,
        watchdog_queue
):
    async with open_connection(host, port) as (reader, writer):
        status_msgs_queue.put_nowait(
            SendingConnectionStateChanged.ESTABLISHED
        )
        user_features = await authorize(reader, writer, token)
        if not user_features:
            logger.error('Не удалось получить свойства юзера.')
            logger.error('Проверьте токен юзера.')
            messagebox.showerror(
                'Неверный токен',
                'Проверьте токен, сервер его не узнал'
            )
            raise InvalidToken
        user_name = user_features["nickname"]
        logger.debug(f'Выполнена авторизация. Пользователь {user_name}')
        status_msgs_queue.put_nowait(NicknameReceived(user_name))
        watchdog_queue.put_nowait('Authorization done')

        try:
            while True:
                sending_message = await sending_queue.get()
                logger.debug(f'Пользователь написал: {sending_message}')
                filtered_message = re.sub(r'\n\n', '', sending_message)
                server_response = await reader.readline()
                logger.debug(repr(server_response.decode()))
                writer.write((filtered_message + '\n').encode())
                await writer.drain()
                writer.write(b'\n')
                await writer.drain()
                watchdog_queue.put_nowait('Message sent')
        except asyncio.CancelledError:
            logger.warning('Stop the coroutine "send_messages"')
            raise


async def read_msgs(
        message_queue,
        history_queue,
        host,
        port,
        status_updates_queue,
        watchdog_queue
):
    async with open_connection(host, port) as (reader, writer):
        status_updates_queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
        try:
            while True:
                received_data = await reader.readline()
                message = received_data.decode()
                message_queue.put_nowait(message)
                history_queue.put_nowait(message)
                watchdog_queue.put_nowait('A new message in the chat')
        except asyncio.CancelledError:
            logger.warning('Stop the coroutine "read_msgs"')
            raise


async def save_messages(filepath, history_queue):
    while True:
        new_message = await history_queue.get()
        try:
            async with aiofiles.open(filepath, 'a') as chat_history_file:
                await chat_history_file.write(new_message)
        except FileNotFoundError:
            logger.error(f'Can not write messages to the file {filepath}')
            messagebox.showwarning(
                'Ошибка записи истории',
                f'Не удается записать историю сообщений в файл {filepath}'
            )
