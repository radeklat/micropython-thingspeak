try:
    import usocket as socket
    import ussl as ssl
    from ucollections import namedtuple
    from utime import time, ticks_ms, ticks_diff
except ImportError:
    import socket
    import ssl
    from typing import Dict, Union, List, Type
    from collections import namedtuple
    from time import time

    def ticks_ms():
        return time() * 1000

    def ticks_diff(end_time, start_time):
        return end_time - start_time


class ThingSpeakError(Exception):
    pass


class Channel:
    __slots__ = ['name', 'write_key', 'fields']

    def __init__(self, name: str, write_key: str, fields: List[str]):
        self.name = name
        self.write_key = write_key
        self.fields = {
            field: 'field' + str(index + 1) for index, field in enumerate(fields)
        }

    def get_field_id(self, field_name: str) -> str:
        return self.fields[field_name]


class _ProtocolBase:
    MESSAGE_COUNT_ON_ERROR_FROM_API = -1

    def __init__(self, log: bool):
        self._log = log

    def send(self, channel: Channel, values: Dict[str, Union[str, int, float]]) -> int:
        raise NotImplementedError()


class _ProtoWeb(_ProtocolBase):
    _API_DNS_LOOKUP_INTERVAL_SEC = 60 * 60
    _API_HOST = 'api.thingspeak.com'
    _API_PORT = None
    _HTTP_POST_TEMPLATE = "GET /update?api_key={write_api_key}&{data} HTTP/1.1\r\n" \
                          "Host: {host}\r\n" \
                          "Connection: close\r\n\r\n"

    def __init__(self, log: bool):
        super().__init__(log)
        self._next_dns_lookup_timestamp = 0
        self._address_info = None

    @staticmethod
    def _make_http_data(
            channel: Channel, data: Dict[str, Union[str, int, float]]
    ) -> bytes:
        if len(data) == 0:
            raise ThingSpeakError("No data given for channel '{}'".format(channel.name))

        data_items = []
        for field_name, field_value in data.items():
            if field_name not in channel.fields:
                raise ThingSpeakError(
                    "Channel '{}' doesn't have field '{}'.".format(channel.name, field_name)
                )
            data_items.append('{}={}'.format(channel.get_field_id(field_name), field_value))

        text_data = '&'.join(data_items) if len(data_items) > 1 else data_items[0]

        return _ProtoWeb._HTTP_POST_TEMPLATE.format(
            host=_ProtoWeb._API_HOST, write_api_key=channel.write_key,
            content_length=len(text_data), data=text_data
        ).encode()

    def _resolve_ip(self):
        assert self._API_PORT is not None, '_API_PORT must be defined in subclasses.'
        now = time()

        if self._next_dns_lookup_timestamp <= now:
            self._address_info = socket.getaddrinfo(_ProtoWeb._API_HOST, self._API_PORT)
            self._next_dns_lookup_timestamp = now + _ProtoWeb._API_DNS_LOOKUP_INTERVAL_SEC
            if self._log:
                print("ThingSpeak at {}:{}".format(*self._address_info[0][-1]))

    def _parse_reply(self, reply: bytes) -> int:
        messages_count = _ProtoWeb.MESSAGE_COUNT_ON_ERROR_FROM_API

        try:
            status = int(reply.split(b'\r\n', 1)[0].split(b' ')[1])

            if status == 200:
                messages_count = int(reply.rsplit(b'\r\n\r\n', 1)[-1])
            else:
                if self._log:
                    print("HTTP call failed:", reply)
        except IndexError:
            print("Malformed reply:", reply)
        except ValueError:
            messages_count = 0

        return messages_count

    @staticmethod
    def _send_to_socket(sock: socket.SocketType, http_data: bytes) -> bytes:
        raise NotImplementedError()

    def send(self, channel: Channel, values: Dict[str, Union[str, int, float]]) -> int:
        self._resolve_ip()

        family, socket_type, proto, _, ip_address_port = self._address_info[0]
        sock = socket.socket(family, socket_type, proto)
        sock.connect(ip_address_port)

        reply = self._parse_reply(
            self._send_to_socket(
                sock, self._make_http_data(channel, values)
            )
        )

        sock.close()

        return reply


class ProtoHTTPS(_ProtoWeb):
    _API_PORT = 443

    @staticmethod
    def _send_to_socket(sock: socket.SocketType, http_data: bytes) -> bytes:
        ssl_sock = ssl.wrap_socket(sock)
        ssl_sock.write(http_data)

        return ssl_sock.read()


class ProtoHTTP(_ProtoWeb):
    _API_PORT = 80
    BUFF_SIZE = 512

    @staticmethod
    def _recvall(sock):
        data = b''
        while True:
            part = sock.recv(ProtoHTTP.BUFF_SIZE)
            if len(part) == 0:
                break
            data += part

        return data

    @staticmethod
    def _send_to_socket(sock: socket.SocketType, http_data: bytes) -> bytes:
        sock.send(http_data)
        return ProtoHTTP._recvall(sock)


class ThingSpeakAPI:
    _FREE_API_LIMIT_SEC = 16
    _API_ALL_DEVICES_POSTING_LIMIT_SEC = 10.512

    def __init__(
            self, channels: List[Channel],
            protocol_class: Type[_ProtocolBase] = ProtoHTTPS,
            log: bool = False
    ):
        self._api = protocol_class(log)  # type: _ProtocolBase
        self._channels = {channel.name: channel for channel in channels}
        self._api_time_limit_sec = max(
            ThingSpeakAPI._API_ALL_DEVICES_POSTING_LIMIT_SEC * len(channels),
            ThingSpeakAPI._FREE_API_LIMIT_SEC
        )
        self._free_api_delay = 0
        self._log = log

    @property
    def free_api_delay(self):
        return self._free_api_delay

    def _get_channel(self, channel_name: str) -> Channel:
        channel = self._channels.get(channel_name, None)

        if channel is None:
            raise ThingSpeakError("No configuration for channel '{}'.".format(channel_name))

        return channel

    def send(self, channel_name: str, values: Dict[str, Union[str, int, float]]) -> bool:
        """
        :return: True when send succeeds (API returns measurement number) or False when send
            fails (API returns error). Error usually means wrong API key.
        """
        start = ticks_ms()

        messages_count = self._api.send(self._get_channel(channel_name), values)

        if messages_count != _ProtocolBase.MESSAGE_COUNT_ON_ERROR_FROM_API:
            execution_sec = ticks_diff(ticks_ms(), start) / 1000
            self._free_api_delay = max(0, self._api_time_limit_sec - execution_sec)

            if self._log:
                print(channel_name, values, '#%s, took %.2fs, next in %.2fs' % (
                    messages_count, execution_sec, self._free_api_delay
                ))

            return True

        self._free_api_delay = 0
        return False
