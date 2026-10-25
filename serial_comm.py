"""
=============================================================
Smart Library Management System — serial_comm.py
USB-Serial communication between the laptop and Pico W
=============================================================

Protocol
--------
Direction  : Laptop  →  Pico W
Format     : Newline-terminated JSON
Schema     :
  {
    "action"  : "ISSUE" | "RETURN" | "INVALID",
    "book_id" : "BK001",
    "title"   : "Python Programming",   # truncated to 16 chars
    "author"  : "Mark Lutz",            # truncated to 16 chars
    "status"  : "ISSUED" | "RETURNED" | "ERROR",
    "message" : "Optional short text"
  }

Direction  : Pico W  →  Laptop
Format     : Newline-terminated JSON
Schema     :
  {"status": "OK" | "ERROR", "action": "ISSUE" | ...}

Auto-detection heuristic
------------------------
Pico W appears on Windows as "USB Serial Device (COMx)" and on
Linux/macOS as /dev/ttyACM0, /dev/ttyUSB0 etc.  The code
iterates available ports and matches known vendor strings.
"""

import json
import threading
import time
from typing import Callable, Optional, Tuple

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("[WARNING] pyserial not installed — Pico W serial disabled.")
    print("          Run: pip install pyserial")


# ── Vendor / description strings that identify a Pico W ────────────────────
PICO_KEYWORDS = (
    'pico', 'rp2040', 'micropython', 'raspberry pi',
    'usb serial device',   # Windows generic CDC
    'cdc',
)


class SerialComm:
    """
    Manages USB-Serial communication with the Raspberry Pi Pico W.

    Thread model
    ------------
    • _read_thread — daemon thread that reads ACK / status messages
      from the Pico W and routes them to on_response_callback.
    • All send operations are synchronous from the caller's thread.
    """

    BAUD_RATE = 115200
    TIMEOUT   = 2            # seconds for read timeout

    def __init__(self):
        self.ser:   Optional[serial.Serial] = None
        self.port:  Optional[str]           = None
        self.connected = False

        self._read_thread: Optional[threading.Thread] = None
        self.on_response_callback: Optional[Callable[[dict], None]] = None

    # ── Connection Management ────────────────────────────────────────────────

    def find_pico_port(self) -> Optional[str]:
        """
        Scan connected serial ports and return the device path of the
        first port that looks like a Pico W.
        Returns None if none found.
        """
        if not SERIAL_AVAILABLE:
            return None

        for port_info in serial.tools.list_ports.comports():
            description  = (port_info.description  or '').lower()
            manufacturer = (port_info.manufacturer or '').lower()
            hwid         = (port_info.hwid          or '').lower()

            if any(kw in description  for kw in PICO_KEYWORDS) or \
               any(kw in manufacturer for kw in PICO_KEYWORDS) or \
               '2e8a' in hwid:    # Raspberry Pi USB vendor ID
                return port_info.device

        return None

    def connect(self, port: Optional[str] = None) -> Tuple[bool, str]:
        """
        Open a serial connection to the Pico W.

        Parameters
        ----------
        port : str or None
            Explicit port path (e.g. 'COM3', '/dev/ttyACM0').
            If None, auto-detect is attempted.

        Returns
        -------
        (success: bool, message: str)
        """
        if not SERIAL_AVAILABLE:
            return False, "pyserial not installed. Run: pip install pyserial"

        if self.connected:
            return True, f"Already connected on {self.port}"

        if port is None:
            port = self.find_pico_port()

        if port is None:
            return False, (
                "Pico W not detected. Ensure it is connected via USB "
                "and running the MicroPython firmware."
            )

        try:
            self.ser = serial.Serial(port, self.BAUD_RATE, timeout=self.TIMEOUT)
            self.port = port
            self.connected = True

            # Start background reader
            self._read_thread = threading.Thread(
                target=self._read_loop, daemon=True
            )
            self._read_thread.start()

            return True, f"Connected to Pico W on {port}"

        except serial.SerialException as exc:
            return False, f"Connection failed: {exc}"

    def disconnect(self):
        """Close the serial port and stop the reader thread."""
        self.connected = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser  = None
        self.port = None

    def get_available_ports(self) -> list:
        """Return list of (device, description) tuples for all serial ports."""
        if not SERIAL_AVAILABLE:
            return []
        return [
            (p.device, p.description)
            for p in serial.tools.list_ports.comports()
        ]

    # ── Sending ──────────────────────────────────────────────────────────────

    def send_book_data(
        self,
        action:  str,
        book_id: str,
        title:   str,
        author:  str,
        status:  str,
        message: str = ''
    ) -> Tuple[bool, str]:
        """
        Send a book-operation JSON packet to the Pico W.

        The title, author, and message fields are truncated to 16
        characters because the LCD is 16 columns wide.
        """
        if not self.connected or self.ser is None:
            return False, "Pico W not connected."

        payload = {
            'action':  action,
            'book_id': book_id,
            'title':   title[:16],
            'author':  author[:16],
            'status':  status,
            'message': message[:16],
        }

        try:
            line = json.dumps(payload) + '\n'
            self.ser.write(line.encode('utf-8'))
            self.ser.flush()
            return True, "Packet sent to Pico W."
        except serial.SerialException as exc:
            self.connected = False
            return False, f"Send error: {exc}"

    def send_invalid_scan(self, raw_data: str) -> bool:
        """Convenience wrapper: notify Pico W of an unrecognised QR code."""
        ok, _ = self.send_book_data(
            action  = 'INVALID',
            book_id = '',
            title   = 'INVALID QR',
            author  = '',
            status  = 'ERROR',
            message = raw_data[:16],
        )
        return ok

    # ── Background Reader ────────────────────────────────────────────────────

    def _read_loop(self):
        """
        Daemon thread: read JSON lines from the Pico W and forward them
        to on_response_callback.
        """
        while self.connected:
            try:
                if self.ser and self.ser.in_waiting:
                    raw = self.ser.readline()
                    line = raw.decode('utf-8', errors='ignore').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if self.on_response_callback:
                                self.on_response_callback(data)
                        except json.JSONDecodeError:
                            # Debug print from Pico W — ignore silently
                            pass
            except serial.SerialException:
                self.connected = False
                break
            except Exception:
                pass
            time.sleep(0.05)
