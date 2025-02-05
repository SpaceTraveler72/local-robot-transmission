
import selectors
import socket
import threading
import traceback

import cv2

import libclient as libclient


class RelayThread:
    _instance = None

    # When a new instance is created, sets it to the same global instance
    def __new__(cls):
        # If the instance is None, create a new instance
        # Otherwise, return already created instance
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._start()
        return cls._instance
    
    
    def _start(self):
        self.sel = selectors.DefaultSelector()
        self.sensor_data = {"IMU": (0.0, 0.0, 0.0)}
        self.robot_state = {"horizontal_motors": (0.0, 0.0, 0.0, 0.0), "vertical_motors": (0.0, 0.0), "enabled": False}
        
        self.host = 'localhost'
        self.port = 65432
    
    def set_horizontal_motors(self, fl : float, fr : float, br : float, bl : float):
        self.robot_state["horizontal_motors"] = (fl, fr, br, bl)
    
    def set_vertical_motors(self, front : float, back : float):
        self.robot_state["vertical_motors"] = (front, back)
    
    def set_enabled(self, enabled : bool):
        self.robot_state["enabled"] = enabled
    
    def get_imu_data(self):
        return self.sensor_data["IMU"]
    
    def begin_thread(self):
        thread = threading.Thread(target=self._run_client_socket)
        thread.start()

    def _create_request(self, message_type):
        if message_type == "text/json":
            return dict(
                type="text/json",
                encoding="utf-8",
                content=self.robot_state,
            )
        if message_type == "camera":
            return dict(
                type="camera",
                encoding="pickle",
                content=self.sensor_data,
            )
        
        raise ValueError(f"Unsupported message type: {message_type!r}")
    
    def _start_connection(self, host, port):
        addr = (host, port)
        print(f"Starting connection to {addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        
        # Send intial message to establish connection with initial robot state
        request = self._create_request("text/json")
        message = libclient.Message(self.sel, sock, addr, request, "robot_data",  self.robot_state, self.sensor_data)
        self.sel.register(sock, events, message)
        
        request = self._create_request("camera")
        message = libclient.Message(self.sel, sock, addr, request, "camera_stream","", None)
        self.sel.register(sock, events, message)
    
    def process_message(self, message, mask):
        message_type = message.key
                        
        if message_type == "robot_data":
            message.input_data = self.robot_state
        elif message_type == "camera_stream":
            message.input_data = ""
            
        data = message.process_events(mask)
        
        if message_type == "robot_data":
            self.sensor_data = data
            print(f"Received: {data}")
        elif message_type == "camera_stream":
            self.camera_data = data
            for frame in self.camera_data:
                cv2.imshow('Receving Video', frame)

    def _run_client_socket(self):
        try:
            # Start the connection
            self._start_connection(self.host, self.port)

            # Send and recieve messages
            while True:
                events = self.sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        self.process_message(message, mask)

                    except Exception:
                        print(
                            f"Main: Error: Exception for {message.addr}:\n"
                            f"{traceback.format_exc()}"
                        )
                        message.close()
                # reconnect if there are no active connections
                if not self.sel.get_map():
                    self._start_connection(self.host, self.port)

        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

transmission = RelayThread()
transmission.begin_thread()
transmission.set_horizontal_motors(1.0, 1.0, 1.0, 1.0)