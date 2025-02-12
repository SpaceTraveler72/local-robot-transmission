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
        self.server_socket.listen(0)
        print(f"Listening on {host}:{port}")
        self.frames = {}
        self.lock = threading.Lock()

    def handle_client(self, connection, client_id):
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
                    self.frames[client_id] = im
        finally:
            connection.close()

    def start(self):
        client_id = 0
        while True:
            connection = self.server_socket.accept()[0].makefile('rb')
            threading.Thread(target=self.handle_client, args=(connection, client_id)).start()
            client_id += 1

    def update_image(self, labels, max_width=None, max_height=None):
        with self.lock:
            for client_id, frame in self.frames.items():
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if max_width and max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                labels[client_id].imgtk = imgtk
                labels[client_id].config(image=imgtk)

if __name__ == "__main__":
    server = CameraServer()
    threading.Thread(target=server.start).start()

    root = tk.Tk()
    root.title("Camera Feeds")

    labels = []
    for i in range(4):  # Assuming a maximum of 4 cameras
        label = tk.Label(root)
        label.pack(side=tk.LEFT)
        labels.append(label)

    max_width = 400
    max_height = 300

    while True:
        server.update_image(labels, max_width, max_height)
        root.update()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    root.destroy()