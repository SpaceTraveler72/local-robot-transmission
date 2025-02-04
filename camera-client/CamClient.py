import socket, cv2, pickle, struct
import threading
from tkinter import Tk, Label
from PIL import Image, ImageTk

class VideoClient:
    def __init__(self, host_ip, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host_ip, port))
        self.data = b""
        self.payload_size = struct.calcsize("Q")
        
    def receive_frame(self):
        while True:
            while len(self.data) < self.payload_size:
                packet = self.client_socket.recv(4*1024) # 4K
                if not packet:
                    return None
                self.data += packet
            packed_msg_size = self.data[:self.payload_size]
            self.data = self.data[self.payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]
            
            while len(self.data) < msg_size:
                self.data += self.client_socket.recv(4*1024)
            
            frame_data = self.data[:msg_size]
            self.data = self.data[msg_size:]
            frame = pickle.loads(frame_data)
            return frame

    def close(self):
        self.client_socket.close()

class VideoDisplay:
    def __init__(self, video_client):
        self.video_client = video_client
        self.root = Tk()
        self.root.title("Receiving Video")
        self.label = Label(self.root)
        self.label.pack()
        self.update_frame()

    def update_frame(self):
        frame = self.video_client.receive_frame()
        if frame is None:
            print("No frame received. Exiting ...")
            self.root.quit()
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.label.image = imgtk
        self.label.configure(image=imgtk)
        self.label.after(10, self.update_frame)

    def start(self):
        self.root.mainloop()

if __name__ == "__main__":
    host_ip = 'localhost' # paste your server ip address here
    port = 9999
    video_client = VideoClient(host_ip, port)
    video_display = VideoDisplay(video_client)
    video_display.start()
    video_client.close()