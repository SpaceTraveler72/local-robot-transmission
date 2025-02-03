# lets make the client code
import selectors
import socket, cv2, pickle, struct
import threading

class CamRecv:
	def __init__(self):
		self.cam_sockets = []
		self.sel = selectors.DefaultSelector()
		
		self.host_ip = 'localhost'
		self.port = 9999
		self.data = b""
		self.payload_size = struct.calcsize("Q")

		self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		address = (self.host_ip, self.port)
		self.client_socket.connect(address)
  
		self.frame = None

	def begin_thread(self):
		thread = threading.Thread(target=self.update_sock)
		thread.daemon = True
		thread.start()
        

	def update_sock(self):
		while len(self.data) < self.payload_size:
			packet = self.client_socket.recv(4*1024) # 4K
			self.data += packet
		packed_msg_size = self.data[:self.payload_size]
		data = self.data[self.payload_size:]
		msg_size = struct.unpack("Q", packed_msg_size)[0]

		while len(data) < msg_size:
			data += self.client_socket.recv(4*1024)

		frame_data = data[:msg_size]
		data = data[msg_size:]
		frame = pickle.loads(frame_data)
		frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		self.frame = frame
