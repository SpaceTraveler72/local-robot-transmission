import io
import socket
import struct
import time
import cv2
from PIL import Image
import threading

class CameraClient:
    def __init__(self, host='localhost', port=9999):
        self.client_socket = socket.socket()
        self.client_socket.connect((host, port))
        self.connection = self.client_socket.makefile('wb')
        self.camera = cv2.VideoCapture(0)

    def handle_client(self):
        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    break
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img)
                image_stream = io.BytesIO()
                img_pil.save(image_stream, format='JPEG')
                image_stream.seek(0)
                image_len = image_stream.getbuffer().nbytes
                self.connection.write(struct.pack('<L', image_len))
                self.connection.write(image_stream.read())
                time.sleep(0.01)
        finally:
            self.connection.write(struct.pack('<L', 0))
            self.connection.close()
            self.client_socket.close()
            self.camera.release()

    def start(self):
        threading.Thread(target=self.handle_client).start()

if __name__ == "__main__":
    client = CameraClient()
    client.start()
