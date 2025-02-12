import io
import socket
import struct
from PIL import Image, ImageTk
import cv2
import numpy
import threading
import tkinter as tk

class CameraServer:
    def __init__(self, host='localhost', port=9999):
        self.server_socket = socket.socket()
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        print(f"Listening on {host}:{port}")
        self.frame = None
        self.lock = threading.Lock()

    def handle_client(self, connection):
        try:
            while True:
                image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
                if not image_len:
                    break
                image_stream = io.BytesIO()
                image_stream.write(connection.read(image_len))
                image_stream.seek(0)
                image = Image.open(image_stream)
                im = cv2.cvtColor(numpy.array(image), cv2.COLOR_RGB2BGR)
                with self.lock:
                    self.frame = im
        finally:
            connection.close()

    def start(self):
        connection = self.server_socket.accept()[0].makefile('rb')
        threading.Thread(target=self.handle_client, args=(connection,)).start()

    def update_image(self, label, max_width=None, max_height=None):
        with self.lock:
            if self.frame is not None:
                img = Image.fromarray(cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB))
                if max_width and max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                label.imgtk = imgtk
                label.config(image=imgtk)

if __name__ == "__main__":
    server = CameraServer()
    threading.Thread(target=server.start).start()

    root = tk.Tk()
    root.title("Camera Feed")
    label = tk.Label(root)
    label.pack()

    max_width = 800
    max_height = 600

    while True:
        server.update_image(label, max_width, max_height)
        root.update()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    root.destroy()