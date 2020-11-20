import tkinter as tk
from tkinter.scrolledtext import ScrolledText


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

    host_entry.pack()
    port_entry.pack()
    user_name_entry.pack()
    sign_up_button.pack()
    messages_window.pack()

    root.mainloop()


if __name__ == '__main__':
    main()
