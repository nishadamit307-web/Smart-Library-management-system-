"""
=============================================================
lcd_i2c.py  —  MicroPython I2C LCD driver
Pico W  ←  I2C  →  PCF8574 I/O expander  →  HD44780 16×2 LCD
=============================================================

Wiring (default)
----------------
Pico W GP0 (SDA)  →  Module SDA
Pico W GP1 (SCL)  →  Module SCL
Pico W 3V3        →  Module VCC
Pico W GND        →  Module GND

PCF8574 I2C address: 0x27  (most common)
                     0x3F  (alternate, if 0x27 fails)

Usage
-----
    from machine import I2C, Pin
    from lcd_i2c import LCD_I2C

    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)
    lcd = LCD_I2C(i2c, addr=0x27)
    lcd.print_line("Hello!", row=0)
    lcd.print_line("Pico W Ready", row=1)
"""

import utime


class LCD_I2C:
    """HD44780-compatible 16×2 character LCD driven over I2C via PCF8574."""

    # ── HD44780 command codes ─────────────────────────────────────────────
    _CMD_CLEAR        = 0x01
    _CMD_HOME         = 0x02
    _CMD_ENTRY_MODE   = 0x04
    _CMD_DISPLAY_CTRL = 0x08
    _CMD_FUNCTION_SET = 0x20
    _CMD_DDRAM_ADDR   = 0x80

    # ── Entry-mode / display-control flags ────────────────────────────────
    _ENTRY_LEFT       = 0x02
    _DISPLAY_ON       = 0x04
    _CURSOR_OFF       = 0x00
    _BLINK_OFF        = 0x00
    _2LINE            = 0x08
    _5x8_DOTS         = 0x00
    _4BIT_MODE        = 0x00

    # ── PCF8574 bit masks ─────────────────────────────────────────────────
    _BL  = 0x08    # Backlight
    _EN  = 0x04    # Enable strobe
    _RW  = 0x02    # R/W (always 0 = write)
    _RS  = 0x01    # Register select (0=cmd, 1=data)

    # DDRAM row offsets for rows 0–3
    _ROW_OFFSETS = [0x00, 0x40, 0x14, 0x54]

    def __init__(self, i2c, addr: int = 0x27,
                 rows: int = 2, cols: int = 16):
        self._i2c  = i2c
        self._addr = addr
        self._rows = rows
        self._cols = cols
        self._backlight = self._BL   # backlight ON by default
        self._init_display()

    # ── Initialisation sequence (from HD44780 datasheet) ─────────────────

    def _init_display(self):
        utime.sleep_ms(50)

        # Force 4-bit mode (send 0x3 three times, then 0x2)
        for _ in range(3):
            self._write4(0x30)
            utime.sleep_ms(5)
        self._write4(0x20)
        utime.sleep_ms(1)

        # Full initialisation commands
        self._cmd(self._CMD_FUNCTION_SET | self._2LINE | self._5x8_DOTS)
        self._cmd(self._CMD_DISPLAY_CTRL | self._DISPLAY_ON |
                  self._CURSOR_OFF      | self._BLINK_OFF)
        self.clear()
        self._cmd(self._CMD_ENTRY_MODE | self._ENTRY_LEFT)

    # ── Low-level I2C helpers ─────────────────────────────────────────────

    def _i2c_write(self, byte: int):
        """Write a single byte to the PCF8574."""
        self._i2c.writeto(self._addr, bytes([byte | self._backlight]))

    def _strobe(self, data: int):
        """Pulse the Enable pin to latch data into the HD44780."""
        self._i2c_write(data | self._EN)
        utime.sleep_us(500)
        self._i2c_write(data & ~self._EN)
        utime.sleep_us(100)

    def _write4(self, data: int):
        """Send 4 bits with Enable strobe."""
        self._i2c_write(data)
        self._strobe(data)

    def _send(self, data: int, mode: int = 0):
        """
        Send a full byte in two 4-bit nibbles.

        Parameters
        ----------
        data : int   Byte to send (command or ASCII character value)
        mode : int   0 = command register,  _RS = data register
        """
        high = mode | (data & 0xF0)            | self._backlight
        low  = mode | ((data << 4) & 0xF0)     | self._backlight
        self._write4(high)
        self._write4(low)

    def _cmd(self, cmd: int):
        """Send a command byte."""
        self._send(cmd, mode=0)
        utime.sleep_us(50)

    def _data(self, char_code: int):
        """Send a data (character) byte."""
        self._send(char_code, mode=self._RS)

    # ── Public API ────────────────────────────────────────────────────────

    def clear(self):
        """Clear the display and return cursor to home."""
        self._cmd(self._CMD_CLEAR)
        utime.sleep_ms(2)

    def home(self):
        """Return cursor to home position (top-left) without clearing."""
        self._cmd(self._CMD_HOME)
        utime.sleep_ms(2)

    def set_cursor(self, col: int, row: int):
        """Move cursor to (col, row).  col and row are 0-based."""
        row = max(0, min(row, self._rows - 1))
        col = max(0, min(col, self._cols - 1))
        self._cmd(self._CMD_DDRAM_ADDR | (col + self._ROW_OFFSETS[row]))

    def write(self, text: str):
        """Write a string at the current cursor position."""
        for ch in text:
            self._data(ord(ch))

    def print_line(self, text: str, row: int = 0):
        """
        Write text to a specific row, padded/truncated to exactly 16 chars.
        This overwrites the entire row cleanly with no artefacts.
        """
        text = text[:self._cols]
padded = text + ' ' * (self._cols - len(text))
        self.set_cursor(0, row)
        self.write(padded)

    def backlight_on(self):
        """Turn the LCD backlight on."""
        self._backlight = self._BL
        self._i2c_write(self._backlight)

    def backlight_off(self):
        """Turn the LCD backlight off."""
        self._backlight = 0x00
        self._i2c_write(self._backlight)

    def display_on(self):
        """Turn display content on (backlight unaffected)."""
        self._cmd(self._CMD_DISPLAY_CTRL | self._DISPLAY_ON)

    def display_off(self):
        """Blank the display (backlight unaffected)."""
        self._cmd(self._CMD_DISPLAY_CTRL)

    def create_char(self, location: int, char_map: list):
        """
        Create a custom 5×8 character in CGRAM.

        Parameters
        ----------
        location : int   Slot 0–7 in CGRAM
        char_map : list  8 bytes (rows of 5 pixels each)
        """
        location &= 0x07
        self._cmd(0x40 | (location << 3))
        for byte in char_map:
            self._data(byte)
