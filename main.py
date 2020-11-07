import asyncio
import gui

import configargparse


def get_input_arguments():
    argument_parser = configargparse.get_argument_parser()
    argument_parser.add(
        '--host',
        type=str,
        default='minechat.dvmn.org',
        env_var='CHAT_HOST',
        help='The chat address.'
    )
    argument_parser.add(
        '--reading_port',
        type=int,
        default=5000,
        env_var='READING_PORT',
        help='The port number to read the chat messages.'
    )
    argument_parser.add(
        '--writing_port',
        type=int,
        default=5050,
        env_var='WRITING_PORT',
        help='The port number to write chat messages.'
    )
    argument_parser.add(
        '--token',
        type=str,
        default='',
        env_var='USER_TOKEN',
        help='An existed user token the client should use to send a message.'
    )
    argument_parser.add(
        '--user_name',
        type=str,
        default='Script Bot',
        env_var='USER_NAME',
        help="""
        If user do not set the argument '--token', 
        the script will create a new user having this name.
        """
    )
    argument_parser.add(
        '--history_filepath',
        type=str,
        default='chat_history.txt',
        env_var='HISTORY_FILEPATH',
        help='A file path where script should output result.'
    )
    input_arguments = argument_parser.parse_args()
    return input_arguments


def main():
    input_arguments = get_input_arguments()

    messages_queue = asyncio.Queue()
    history_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    main_coroutine = gui.draw(
        input_arguments,
        messages_queue,
        history_queue,
        sending_queue,
        status_updates_queue
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_coroutine)


if __name__ == '__main__':
    main()
