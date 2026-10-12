"""香氛機直連工作階段；只開放白名單屬性。"""

import asyncio
import contextlib
import zlib

from bleak import BleakClient
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESCCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.integrations.mesh_protocol import ReplayWindow, integer_command, parse_properties


def uuid(channel):
    return f"0000{channel}-0000-1000-8000-00805f9b34fb"


class MeshSession:
    def __init__(self, address, secret):
        self.client = BleakClient(address, timeout=12, pair=False, winrt={"use_cached_services": False})
        self.secret = secret
        self.queues = {c: asyncio.Queue() for c in ["0010", "0016", "001a", "001b"]}
        self.properties = {}
        self.revisions = {}
        self.responses = {}
        self.replay = ReplayWindow()
        self.set_responses = {}
        self.condition = asyncio.Condition()
        self.tx_counter = 0
        self.reader = None
        self.receive_error = None
        self.opened = asyncio.Event()
        self.stage = "created"

    async def write(self, channel, value):
        await self.client.write_gatt_char(uuid(channel), value, response=False)

    async def wait(self, channel):
        return await asyncio.wait_for(self.queues[channel].get(), 6)

    def notify(self, characteristic, value):
        self.queues[characteristic.uuid[4:8]].put_nowait(bytes(value))

    async def __aenter__(self):
        try:
            self.stage = "connecting"
            await self.client.connect()
            for channel in self.queues:
                await self.client.start_notify(uuid(channel), self.notify)
            self.stage = "transport"
            await self.write("0010", b"\xa4")
            for _ in range(2):
                packet = await self.wait("0016")
                if packet[:3] != b"\x00\x00\x04":
                    raise ValueError("transport_negotiation_rejected")
                await self.write("0016", packet[:2] + b"\x05" + packet[3:])
            await asyncio.sleep(0.2)
            self.stage = "login"
            private = ec.generate_private_key(ec.SECP256R1())
            public = private.public_key().public_bytes(
                serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
            )[1:]
            await self.write("0010", bytes.fromhex("50000000"))
            await self.write("0016", bytes.fromhex("000000030100"))
            if await self.wait("0016") != bytes.fromhex("00000101"):
                raise ValueError("public_key_not_ready")
            await self.write("0016", b"\x01\x00" + public)
            if await self.wait("0016") != bytes.fromhex("00000100"):
                raise ValueError("public_key_not_received")
            packet = await self.wait("0016")
            if packet[:4] != bytes.fromhex("00000203") or len(packet) != 68:
                raise ValueError("invalid_remote_key")
            remote = packet[4:]
            await self.write("0016", bytes.fromhex("00000300"))
            shared = private.exchange(
                ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b"\x04" + remote)
            )
            self.session = HKDF(
                algorithm=hashes.SHA256(),
                length=64,
                salt=b"miot-mesh-login-salt",
                info=b"miot-mesh-login-info",
            ).derive(shared + self.secret)
            proof = AESCCM(self.session[16:32], tag_length=4).encrypt(
                bytes.fromhex("101112131415161718191a1b"), zlib.crc32(remote).to_bytes(4, "little"), b""
            )
            await self.write("0016", bytes.fromhex("000000050100"))
            if await self.wait("0016") != bytes.fromhex("00000101"):
                raise ValueError("login_proof_not_ready")
            await self.write("0016", b"\x01\x00" + proof)
            if await self.wait("0016") != bytes.fromhex("00000100"):
                raise ValueError("login_proof_not_received")
            if await self.wait("0010") != bytes.fromhex("51000000"):
                raise ValueError("login_rejected")
            self.stage = "opening_property_session"
            self.reader = asyncio.create_task(self.receive())
            await self.send(bytes.fromhex("05200000f0"))
            await asyncio.wait_for(self.opened.wait(), 8)
            self.stage = "ready"
            return self
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

    async def __aexit__(self, *_):
        if self.reader:
            self.reader.cancel()
            await asyncio.gather(self.reader, return_exceptions=True)
        if self.client.is_connected:
            with contextlib.suppress(Exception):
                await self.client.disconnect()

    async def send(self, plaintext):
        counter = self.tx_counter
        if counter >= 65535:
            raise ValueError("session_counter_exhausted")
        self.tx_counter += 1
        nonce = self.session[36:40] + bytes(4) + counter.to_bytes(4, "little")
        encrypted = counter.to_bytes(2, "little") + AESCCM(self.session[16:32], tag_length=4).encrypt(
            nonce, plaintext, b""
        )
        characteristic = self.client.services.get_characteristic(uuid("001a"))
        chunk_size = min(242, characteristic.max_write_without_response_size - 2)
        if chunk_size < 18:
            raise ValueError("insufficient_ble_mtu")
        chunks = [encrypted[i : i + chunk_size] for i in range(0, len(encrypted), chunk_size)]
        await self.write("001a", bytes.fromhex("00000000") + len(chunks).to_bytes(2, "little"))
        if await self.wait("001a") != bytes.fromhex("00000101"):
            raise ValueError("command_not_ready")
        for index, chunk in enumerate(chunks, 1):
            await self.write("001a", index.to_bytes(2, "little") + chunk)
        if await self.wait("001a") != bytes.fromhex("00000100"):
            raise ValueError("command_not_received")

    async def receive(self):
        try:
            while True:
                packet = await self.queues["001b"].get()
                if packet[:4] == bytes.fromhex("00000200"):
                    encrypted = packet[4:]
                    await self.write("001b", bytes.fromhex("00000300"))
                elif packet[:4] == bytes.fromhex("00000000") and len(packet) == 6:
                    count = int.from_bytes(packet[4:], "little")
                    if not 1 <= count <= 32:
                        raise ValueError("invalid_frame_count")
                    await self.write("001b", bytes.fromhex("00000101"))
                    parts = []
                    for index in range(1, count + 1):
                        part = await self.wait("001b")
                        if int.from_bytes(part[:2], "little") != index:
                            raise ValueError("invalid_frame_sequence")
                        parts.append(part[2:])
                    encrypted = b"".join(parts)
                    await self.write("001b", bytes.fromhex("00000100"))
                else:
                    raise ValueError("unknown_property_frame")
                if len(encrypted) < 7:
                    raise ValueError("truncated_encrypted_data")
                counter = int.from_bytes(encrypted[:2], "little")
                nonce = self.session[32:36] + bytes(4) + counter.to_bytes(4, "little")
                plain = AESCCM(self.session[:16], tag_length=4).decrypt(nonce, encrypted[2:], b"")
                self.replay.accept(counter)
                props = parse_properties(plain)
                if plain[4] == 0xF0:
                    self.opened.set()
                async with self.condition:
                    if plain[4] == 1:
                        if len(plain) != 11 or plain[5] != 1:
                            raise ValueError("invalid_set_response")
                        self.set_responses[int.from_bytes(plain[2:4], "little")] = (
                            (plain[6], int.from_bytes(plain[7:9], "little")),
                            int.from_bytes(plain[9:11], "little"),
                        )
                    if plain[4] == 3:
                        self.responses[int.from_bytes(plain[2:4], "little")] = props
                    for key, value in props.items():
                        self.properties[key] = value
                        self.revisions[key] = self.revisions.get(key, 0) + 1
                    self.condition.notify_all()
        except Exception as error:
            self.receive_error = (
                "replayed_packet" if str(error) == "replayed_packet" else type(error).__name__
            )
            async with self.condition:
                self.condition.notify_all()

    async def read(self, siid, piid):
        key = (siid, piid)
        tid = self.tx_counter
        self.responses.pop(tid, None)
        await self.send(bytes([9, 0x20, tid & 255, tid >> 8, 2, 1, siid, piid, 0]))
        async with self.condition:
            await asyncio.wait_for(
                self.condition.wait_for(lambda: tid in self.responses or self.receive_error), 8
            )
        if self.receive_error:
            raise ValueError("receive_failed")
        response = self.responses.pop(tid)
        if key not in response:
            raise ValueError("mismatched_property_response")
        return response[key]

    async def set_boolean(self, siid, piid, value):
        if (siid, piid) not in {(2, 2), (3, 1)} or type(value) is not bool:
            raise ValueError("unsupported_control")
        tid = self.tx_counter
        self.set_responses.pop(tid, None)
        await self.send(bytes([12, 0x20, tid & 255, tid >> 8, 0, 1, siid, piid, 0, 1, 0, int(value)]))
        return await self.confirm_write(tid, siid, piid, int(value))

    async def set_integer(self, siid, piid, value):
        tid = self.tx_counter
        command = integer_command(tid, siid, piid, value)
        self.set_responses.pop(tid, None)
        await self.send(command)
        return await self.confirm_write(tid, siid, piid, value)

    async def confirm_write(self, tid, siid, piid, value):
        async with self.condition:
            await asyncio.wait_for(
                self.condition.wait_for(lambda: tid in self.set_responses or self.receive_error), 8
            )
        if self.receive_error or self.set_responses.pop(tid, None) != ((siid, piid), 0):
            raise ValueError("control_rejected")
        # 傳輸 ACK 只代表收到封包；另行讀回同一個屬性才確認結果。
        for _ in range(6):
            await asyncio.sleep(0.5)
            actual = await self.read(siid, piid)
            if actual == int(value):
                return actual
        raise ValueError("control_not_confirmed")
