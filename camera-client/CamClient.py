# lets make the client code
import socket, cv2, pickle, struct
from tkinter import Tk, Label
from PIL import Image, ImageTk

# create socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = 'localhost' # paste your server ip address here
port = 9999
client_socket.connect((host_ip, port)) # a tuple
data = b""
payload_size = struct.calcsize("Q")

# Initialize Tkinter
root = Tk()
root.title("Receiving Video")
label = Label(root)
label.pack()

def update_frame():
	global data
	while len(data) < payload_size:
		packet = client_socket.recv(4*1024) # 4K
		if not packet: 
			root.quit()
			return
		data += packet
	packed_msg_size = data[:payload_size]
	data = data[payload_size:]
	msg_size = struct.unpack("Q", packed_msg_size)[0]
	
	while len(data) < msg_size:
		data += client_socket.recv(4*1024)
  
	frame_data = data[:msg_size]
	data = data[msg_size:]
	frame = pickle.loads(frame_data)
	frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
	img = Image.fromarray(frame)
	imgtk = ImageTk.PhotoImage(image=img)
	label.image = imgtk
	label.configure(image=imgtk)
	label.after(10, update_frame)

update_frame()
root.mainloop()