import os
from unittest import TestCase

from src.thingspeak import ThingSpeakAPI, Channel, ProtoHTTPS, ProtoHTTP, ThingSpeakError


class ThingSpeakHTTPTestCase(TestCase):
    CHANNEL_NAME = "Testing channel"
    FIELD_NAME = "Testing field"
    API_KEY = os.environ['API_KEY']
    PROTOCOL = ProtoHTTP

    CORRECT_VALUES = {FIELD_NAME: 10}

    def setUp(self):
        self._thing_speak = ThingSpeakAPI([
            Channel(self.CHANNEL_NAME, self.API_KEY, [self.FIELD_NAME])
        ], self.PROTOCOL)

    @classmethod
    def setUpClass(cls):
        assert 'API_KEY' in os.environ, "Write API key not provided for tests."

    def test_send_works(self):
        self.assertTrue(
            self._thing_speak.send(self.CHANNEL_NAME, self.CORRECT_VALUES)
        )

    def test_send_fails_for_wrong_api_key(self):
        thing_speak = ThingSpeakAPI([
            Channel(self.CHANNEL_NAME, '', [self.FIELD_NAME])
        ], self.PROTOCOL)

        self.assertFalse(
            thing_speak.send(self.CHANNEL_NAME, self.CORRECT_VALUES)
        )

    def test_positive_delay_is_set_after_send(self):
        self._thing_speak.send(self.CHANNEL_NAME, self.CORRECT_VALUES)

        self.assertGreater(self._thing_speak.free_api_delay, 0)

    def test_send_does_allow_field_name_that_is_not_configured(self):
        with self.assertRaises(ThingSpeakError):
            self._thing_speak.send(
                self.CHANNEL_NAME, {'unconfigured field name': 10}
            )

    def test_send_does_allow_channel_that_is_not_configured(self):
        with self.assertRaises(ThingSpeakError):
            self._thing_speak.send(
                'unknown channel name', self.CORRECT_VALUES
            )

    def test_send_does_empty_data(self):
        with self.assertRaises(ThingSpeakError):
            self._thing_speak.send(self.CHANNEL_NAME, dict())


class ThingSpeakHTTPSTestCase(ThingSpeakHTTPTestCase):
    PROTOCOL = ProtoHTTPS
