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
        self.num_cameras = 0
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
        message = libserver.Message(self.sel, conn, addr, self.robot_state, self.sensor_data)
        self.sel.register(conn, selectors.EVENT_READ, data=message)
    
    def _connect_all_cameras(self):
        self.num_cameras = 0
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.num_cameras += 1
                self.camera_connections.append(cap)
            else:
                break
    
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
                            message.process_events(mask, self.sensor_data)
                            print(f"Received: {message.robot_state}")
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
