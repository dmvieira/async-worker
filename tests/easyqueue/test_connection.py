import asyncio

import asynctest
from asynctest import Mock, CoroutineMock, call, ANY, mock

from asyncworker.easyqueue.connection import AMQPConnection
from tests.easyqueue.base import AsyncBaseTestCase


class AMQPConnectionTests(AsyncBaseTestCase, asynctest.TestCase):
    async def setUp(self):
        super(AMQPConnectionTests, self).setUp()
        self.connection = AMQPConnection(**self.conn_params, on_error=Mock())

    async def test_connect_opens_a_connection_communication_channel(self):
        self.assertFalse(self.connection.is_connected)
        self.assertIsNone(self.connection._protocol)
        self.assertIsNone(self.connection._transport)
        self.assertIsNone(self.connection.channel)

        await self.connection._connect()

        self.assertTrue(self.connection.is_connected)
        self.assertEqual(self.connection._protocol, self._protocol)
        self.assertEqual(self.connection._transport, self._transport)
        self.assertIsNotNone(self.connection.channel)

    async def test_connection_lock_ensures_amqp_connect_is_only_called_once(
        self
    ):
        transport = Mock()
        protocol = Mock(channel=CoroutineMock(is_open=True))

        conn = (transport, protocol)
        with asynctest.patch(
            "asyncworker.easyqueue.connection.aioamqp.connect",
            return_value=conn,
        ) as connect:
            await asyncio.gather(
                *(self.connection._connect() for _ in range(100))
            )
            self.assertEqual(connect.await_count, 1)

    async def test_connects_with_correct_args(self):

        await self.connection._connect()

        self.assertEqual(
            self._connect.call_args_list,
            [
                call(
                    host=self.conn_params["host"],
                    password=self.conn_params["password"],
                    virtualhost=self.conn_params["virtual_host"],
                    login=self.conn_params["username"],
                    on_error=self.connection._on_error,
                    loop=ANY,
                    heartbeat=self.conn_params["heartbeat"],
                )
            ],
        )

    async def test_it_closes_the_connection(self):
        await self.connection._connect()
        await self.connection.close()

        self.assertTrue(self._protocol.close.called)
        self.assertTrue(self._transport.close.called)

    async def test_is_does_not_close_if_already_closed(self):

        with mock.patch.object(
            self.connection, "_protocol", CoroutineMock(close=CoroutineMock())
        ) as _protocol, mock.patch.object(
            self.connection, "_transport"
        ) as _transport:

            await self.connection.close()

            self.assertEqual(0, _protocol.close.await_count)
            self.assertEqual(0, _transport.close.call_count)
