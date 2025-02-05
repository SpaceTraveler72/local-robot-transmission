#!/usr/bin/env python3

import selectors
import socket
import threading
import traceback
import cv2

import libserver as libserver


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
        self.robot_state = {"horizontal_motors": (0, 0, 0, 0), "vertical_motors": (0, 0), "enabled": False}
        self.camera_connections = []
        
        self.host = 'localhost'
        self.port = 65432
    
    def set_IMU_data(self, x : float, y : float, z : float):
        self.sensor_data["IMU"] = (x, y, z)
        
    def get_horizontal_motors(self):
        return self.robot_state["horizontal_motors"]
    
    def get_vertical_motors(self):
        return self.robot_state["vertical_motors"]
    
    def get_enabled(self):
        return self.robot_state["enabled"]

    def begin_thread(self):
        thread = threading.Thread(target=self.run_server_socket)
        thread.start()

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Accepted connection from {addr}")
        conn.setblocking(False)
        message = libserver.Message(self.sel, conn, addr, "robot-data", 
                                    default_input_data=self.sensor_data, 
                                    default_recieve_data=self.robot_state)
        self.sel.register(conn, selectors.EVENT_READ, data=message)
    
    def _connect_all_cameras(self):
        i = 0
        while True:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.camera_connections.append(cap)
            else:
                break
            i += 1
    
    def process_message(self, message, mask):
        message_type = message.key
                        
        if message_type == "robot_data":
            message.input_data = self.sensor_data
        elif message_type == "camera_stream":
            frames = []
            for camera in self.camera_connections:
                ret, frame = camera.read()
                if ret:
                    frames.append(frame)
                    
            print(f"Sending {len(frames)} frames")
            message.input_data = frames
            
        data = message.process_events(mask)
        
        if message_type == "robot_data":
            self.robot_state = data
            #print(f"Received: {data}")
        elif message_type == "camera_stream":
            pass
    
    def run_server_socket(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.host, self.port))
        lsock.listen()
        print(f"Listening on {(self.host, self.port)}")
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        
        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            self.process_message(message, mask)
                        except Exception:
                            print(
                                f"Main: Error: Exception for {message.addr}:\n"
                                f"{traceback.format_exc()}"
                            )
                            message.close()
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

transmission = RelayThread()
transmission.begin_thread()
