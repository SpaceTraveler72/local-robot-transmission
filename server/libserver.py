import io
import json
import pickle
import selectors
import struct
import sys

import imutils


class Message:
    def __init__(self, selector, sock, addr, default_input_data, default_recieve_data):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        
        # stuff added but not in the original code
        self.input_data = default_input_data
        self.recieve_data = default_recieve_data

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {mode!r}.")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096) # type: ignore
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

    def _write(self):
        # If the buffer is empty, switch back to reading mode
        if not self._send_buffer:
            self._jsonheader_len = None
            self.jsonheader = None
            self.request = None
            self._set_selector_events_mask("r")
            return
        
        print(f"Sending {self._send_buffer!r} to {self.addr}")
        try:
            # Should be ready to write
            sent = self.sock.send(self._send_buffer) # type: ignore
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            self._send_buffer = self._send_buffer[sent:]



    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _camera_encode(self, frames, frame_width=350):
        resized_frames = []
        # Resize the frame to the specified width (default is 350)
        for frame in frames:
            frame = imutils.resize(frame, width=frame_width)
            resized_frames.append(frame)
        # use pickle as the encoding method
        return pickle.dumps(resized_frames)

    def _camera_decode(self, data):
        return pickle.loads(data)

    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_response_json_content(self):
        # sent the content of the message to be the sensor data
        content = self.input_data
        
        # magic
        content_encoding = "utf-8"
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return response

    def _create_response_camera_content(self):
        # sent the content of the message to be the camera data
        content = self.input_data
        
        # magic
        content_encoding = "pickle"
        response = {
            "content_bytes": self._camera_encode(content),
            "content_type": "camera",
            "content_encoding": content_encoding,
        }
        return response

    def process_events(self, mask,):
        if mask & selectors.EVENT_READ:
            print("Reading")
            self.read()
        if mask & selectors.EVENT_WRITE:
            print("Writing")
            self.write()
        
        # returns the recieved_data if you want to grab it through this function
        return self.recieve_data

    def read(self):
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.request is None:
                self.process_request()

    def write(self):
        if self.request:
            self.create_response()

        self._write()

    def close(self):
        print(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(
                f"Error: selector.unregister() exception for "
                f"{self.addr}: {e!r}"
            )

        try:
            self.sock.close() # type: ignore
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen: # type: ignore
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f"Missing required header '{reqhdr}'.")

    def process_request(self):
        content_len = self.jsonheader["content-length"] # type: ignore
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader["content-type"] == "text/json": # type: ignore
            encoding = self.jsonheader["content-encoding"] # type: ignore
            self.request = self._json_decode(data, encoding)
            
            self.recieve_data = dict(self.request)
        elif self.jsonheader["content-type"] == "camera": # type: ignore
            self.request = self._camera_decode(data)
            self.recieve_data = self.request
        else:
            raise ValueError(f"Unsupported content type: {self.jsonheader['content-type']!r}") # type: ignore
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def create_response(self):
        if self.jsonheader["content-type"] == "text/json": # type: ignore
            response = self._create_response_json_content()
        elif self.jsonheader["content-type"] == "camera": # type: ignore
            response = self._create_response_camera_content()
        else:
            # Binary or unknown content-type
            raise ValueError(f"Unsupported content type: {self.jsonheader['content-type']!r}") # type: ignore
        message = self._create_message(**response)
        self._send_buffer += message
        
        # Set selector to listen for read events, we're done writing.
        self._set_selector_events_mask("r")
        
        # Reset state to read the next message
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None

