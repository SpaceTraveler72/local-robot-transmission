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
                content=[],
            )
        
        raise ValueError(f"Unsupported message type: {message_type!r}")
    
    def _start_connection(self, host, port):
        addr = (host, port)
        print(f"Starting connection to {addr}")
        
        # Create socket for robot data
        # robot_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # robot_sock.setblocking(False)
        # robot_sock.connect_ex(addr)
        # robot_events = selectors.EVENT_READ | selectors.EVENT_WRITE
        
        # # Send initial message to establish connection with initial robot state
        # robot_request = self._create_request("text/json")
        # robot_addr = (host, port)
        # robot_message = libclient.Message(self.sel, robot_sock, robot_addr, robot_request, "robot_data",  
        #                                   default_input_data=self.robot_state, 
        #                                   default_recieve_data=self.sensor_data)
        # self.sel.register(robot_sock, robot_events, robot_message)
        
        # Create socket for camera stream
        camera_addr = (host, port)
        camera_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        camera_sock.setblocking(False)
        camera_sock.connect_ex(camera_addr)
        camera_events = selectors.EVENT_READ | selectors.EVENT_WRITE
        
        camera_request = self._create_request("camera")
        camera_message = libclient.Message(self.sel, camera_sock, camera_addr, camera_request,
                                           default_input_data=[], 
                                           default_recieve_data=[])
        self.sel.register(camera_sock, camera_events, camera_message)
    
    def process_message(self, message, mask):
        message.input_data = []
        data = message.process_events(mask)
        self.camera_data = data
        print(f"Received {len(data)} frames")
        for frame in self.camera_data:
            cv2.imshow('Receiving Video', frame)
            cv2.waitKey(1)

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