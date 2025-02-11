import io
import socket
import struct
import time
import cv2
import sys
from PIL import Image

client_socket = socket.socket()
client_socket.connect(('localhost', 9999))
connection = client_socket.makefile('wb')

camera = cv2.VideoCapture(0)

try:
    while True:
        ret, frame = camera.read()
        if not ret:
            break
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img)
        image_stream = io.BytesIO()
        img_pil.save(image_stream, format='JPEG')
        image_stream.seek(0)
        image_len = image_stream.getbuffer().nbytes
        connection.write(struct.pack('<L', image_len))
        connection.write(image_stream.read())
        time.sleep(0.01)
finally:
    connection.write(struct.pack('<L', 0))
    connection.close()
    client_socket.close()
    camera.release()
