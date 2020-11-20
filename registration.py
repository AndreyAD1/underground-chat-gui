import json
from logger import logger
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from open_connection import open_connection


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


def main():
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
        lambda event: register(host_entry, port_entry, user_name_entry)
    )

    host_entry.pack()
    port_entry.pack()
    user_name_entry.pack()
    sign_up_button.pack()
    messages_window.pack()
    user_hash.pack()

    root.mainloop()


if __name__ == '__main__':
    main()
