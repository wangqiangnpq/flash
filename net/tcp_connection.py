import gevent
from gevent.queue import Queue
from .codec import Codec
from utils.buffer import Buffer
from utils.log import logger


class TcpConnection(object):
    def __init__(self, socket: gevent.socket.socket, codec: Codec, processor):
        self._socket = socket
        self._codec = codec
        self._processor = processor
        self._buffer = Buffer()
        self._stop = False
        self._queue = Queue()
        self.address = self._socket.getpeername()


    def _recv(self):
        while not self._stop:
            msg = self._codec.decode(self._buffer, self)
            if msg is None:
                try:
                    data = self._socket.recv(8 * 1024)
                    if data is None or len(data) == 0:
                        break
                except Exception as e:
                    logger.error("Connection:%s, recv message, exception:%s", self.address, e)
                    break
                self._buffer.shrink()
                self._buffer.append(data)
                continue
            self._processor(self, msg)
        gevent.spawn(lambda : self.close())
        pass

    def _send(self):
        while not self._stop:
            try:
                data = self._queue.get()
                if data is not None:
                    self._socket.sendall(data)
                else:
                    break
            except Exception as e:
                logger.error("Connection:%s, send message, exception:%s", self.address, e)
                break
        pass

    def run(self):
        self._send_spawn = gevent.spawn(lambda : self._send())
        self._recv()

    def close(self):
        self._stop = True
        self._queue.put(None)
        gevent.joinall([self._send_spawn])
        self._socket.close()
        logger.info("Connection:%s, close", self.address)
        pass


    def send_message(self, m):
        array = self._codec.encode(m, self)
        self._queue.put(array)
        pass
