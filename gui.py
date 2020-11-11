import asyncio
import logging

import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from anyio import create_task_group
from async_timeout import timeout
import aiofiles

from logger import logger
from process_messages import read_msgs, send_messages, save_messages
from statuses import NicknameReceived, ReadConnectionStateChanged
from statuses import SendingConnectionStateChanged


class TkAppClosed(Exception):
    pass


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


class WatchdogFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return int(record.created)


async def watch_for_connection(watchdog_queue):
    watchdog_logger = logging.getLogger(__name__)
    watchdog_logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    formatter = WatchdogFormatter('[%(asctime)s] %(message)s')
    console.setFormatter(formatter)
    watchdog_logger.addHandler(console)
    while True:
        try:
            async with timeout(1) as timeout_manager:
                connection_message = await watchdog_queue.get()
                report = f'Connection is alive. Source: {connection_message}'
                watchdog_logger.debug(report)
        except asyncio.TimeoutError as ex:
            if not timeout_manager.expired:
                raise
            watchdog_logger.debug('1s timeout is elapsed')
            # raise ConnectionError from ex


async def handle_connection(
        input_arguments,
        messages_queue,
        history_queue,
        sending_queue,
        status_updates_queue,
        watchdog_queue
):
    server_host = input_arguments.host
    sending_port = input_arguments.sending_port
    token = input_arguments.token
    reading_port = input_arguments.reading_port
    while True:
        async with create_task_group() as task_group:
            await task_group.spawn(
                read_msgs,
                messages_queue,
                history_queue,
                server_host,
                reading_port,
                status_updates_queue,
                watchdog_queue
            )
            await task_group.spawn(
                send_messages,
                server_host,
                sending_port,
                sending_queue,
                token,
                status_updates_queue,
                watchdog_queue
            )
            await task_group.spawn(watch_for_connection, watchdog_queue)
            # try:
            #     await task_group.spawn(watch_for_connection, watchdog_queue)
            # except ConnectionError:
            #     continue


async def draw(
        input_arguments,
        messages_queue,
        history_queue,
        sending_queue,
        status_updates_queue,
        watchdog_queue
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

    connection_handling_coroutine = handle_connection(
        input_arguments,
        messages_queue,
        history_queue,
        sending_queue,
        status_updates_queue,
        watchdog_queue
    )

    await asyncio.gather(
        update_tk(root_frame),
        update_conversation_history(conversation_panel, messages_queue),
        update_status_panel(status_labels, status_updates_queue),
        connection_handling_coroutine,
        save_messages(input_arguments.history_filepath, history_queue),
    )
