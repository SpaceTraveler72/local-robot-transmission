# Welcome to PyShine

# This code is for the server 
# Lets import the libraries
import socket, cv2, pickle, struct, imutils
import threading

class VideoServer:
    def __init__(self, host_ip, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host_ip, port))
        self.server_socket.listen(5)
        print("LISTENING AT:", (host_ip, port))
    
    def start_thread(self):
        thread = threading.Thread(target=self._start)
        thread.daemon = False
        thread.start()

    def _start(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print('GOT CONNECTION FROM:', addr)
            if client_socket:
                self.send_video(client_socket)

    def send_video(self, client_socket):
        vid = cv2.VideoCapture(0)
        while vid.isOpened():
            img, frame = vid.read()
            frame = imutils.resize(frame, width=350)
            a = pickle.dumps(frame)
            message = struct.pack("Q", len(a)) + a
            client_socket.sendall(message)
            
            cv2.imshow('TRANSMITTING VIDEO', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                client_socket.close()
                break

if __name__ == "__main__":
    host_ip = 'localhost'
    port = 9999
    video_server = VideoServer(host_ip, port)
    video_server.start_thread()