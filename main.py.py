"""
=============================================================
Smart Library Management System — Raspberry Pi Pico W
main.py  (MicroPython)
=============================================================

Hardware connections
--------------------
Component          Pico W Pin    Notes
─────────────────────────────────────────────────────
16×2 LCD (I2C)     GP0 (SDA)    Via PCF8574 I2C module
                   GP1 (SCL)
                   3V3  &  GND
Green LED          GP15          Through 220 Ω resistor to GND
Red LED            GP14          Through 220 Ω resistor to GND
Active Buzzer      GP13          Direct (3.3 V active buzzer)
                                 Or via NPN transistor for passive
USB (Serial)       USB port      Connected to laptop

Protocol (USB-Serial, 115200 baud)
------------------------------------
Laptop → Pico (JSON, newline-terminated):
  {"action":"ISSUE","book_id":"BK001","title":"Python Prog","author":"Mark Lutz"}
  {"action":"RETURN","book_id":"BK003","title":"Gatsby","author":"Fitzgerald"}
  {"action":"INVALID","book_id":"","title":"INVALID QR","author":""}

Pico → Laptop (JSON, newline-terminated):
  {"status":"OK","action":"ISSUE"}
  {"status":"ERROR","message":"parse error"}

LED / Buzzer behaviour
-----------------------
Action     Green LED    Red LED         Buzzer
─────────────────────────────────────────────────
Idle       Slow blink   OFF             —
ISSUE      Steady ON    3 quick blinks  2 short beeps
RETURN     Steady ON    3 quick blinks  1 short beep
INVALID    OFF          Steady ON       3 long beeps
=============================================================
"""

import machine
import utime
import json
import sys
import select

from lcd_i2c import LCD_I2C

# ── Pin numbers ──────────────────────────────────────────────────────────────
PIN_GREEN  = 15
PIN_RED    = 14
PIN_BUZZER = 13
PIN_SDA    = 0
PIN_SCL    = 1
LCD_ADDR   = 0x27    # Change to 0x3F if display stays blank

# ── Hardware initialisation ──────────────────────────────────────────────────
green_led = machine.Pin(PIN_GREEN,  machine.Pin.OUT)
red_led   = machine.Pin(PIN_RED,    machine.Pin.OUT)
buzzer    = machine.Pin(PIN_BUZZER, machine.Pin.OUT)

i2c = machine.I2C(
    0,
    sda=machine.Pin(PIN_SDA),
    scl=machine.Pin(PIN_SCL),
    freq=400_000
)

# Scan I2C bus and print found addresses (helpful for debug)
devices = i2c.scan()
print(f"[INIT] I2C devices found: {[hex(d) for d in devices]}")

lcd = LCD_I2C(i2c, addr=LCD_ADDR, rows=2, cols=16)

# ── Heartbeat timer state ────────────────────────────────────────────────────
_heartbeat_active = True   # False while processing a scan result

def _heartbeat_cb(timer):
    """Timer ISR — blink green LED when idle."""
    if _heartbeat_active:
        green_led.toggle()

heartbeat_timer = machine.Timer()
heartbeat_timer.init(
    period=800,
    mode=machine.Timer.PERIODIC,
    callback=_heartbeat_cb
)


# ═══════════════════════════════════════════════════════════════════════════════
# Low-level hardware helpers
# ═══════════════════════════════════════════════════════════════════════════════

def beep(duration_ms: int = 100, count: int = 1, gap_ms: int = 80):
    """Activate the buzzer `count` times, each lasting `duration_ms`."""
    for _ in range(count):
        buzzer.value(1)
        utime.sleep_ms(duration_ms)
        buzzer.value(0)
        utime.sleep_ms(gap_ms)


def blink_red(count: int = 3, on_ms: int = 150, off_ms: int = 150):
    """Blink the red LED `count` times."""
    for _ in range(count):
        red_led.value(1)
        utime.sleep_ms(on_ms)
        red_led.value(0)
        utime.sleep_ms(off_ms)


def send_json(obj: dict):
    """Write a JSON response to the laptop via USB-Serial."""
    sys.stdout.write(json.dumps(obj) + '\n')


# ═══════════════════════════════════════════════════════════════════════════════
# Display helpers
# ═══════════════════════════════════════════════════════════════════════════════

def show_idle():
    """Display startup / idle screen."""
    lcd.clear()
    lcd.print_line(" Smart Library", row=0)
    lcd.print_line("  System Ready  ", row=1)


def show_book_issued(book_id: str, title: str):
    """
    Display ISSUED message on the LCD.
    Row 0: "ISSUED  BK001"
    Row 1: book title (truncated to 16 chars)
    """
    lcd.clear()
    header = f"ISSUED  {book_id}"
    lcd.print_line(header[:16], row=0)
    lcd.print_line(title[:16],  row=1)


def show_book_returned(book_id: str, title: str):
    """Display RETURNED message on the LCD."""
    lcd.clear()
    header = f"RETURN  {book_id}"
    lcd.print_line(header[:16], row=0)
    lcd.print_line(title[:16],  row=1)


def show_invalid(raw: str = ''):
    """Display INVALID QR warning on the LCD."""
    lcd.clear()
    lcd.print_line("** INVALID QR **", row=0)
    lcd.print_line("  Not in DB!    ", row=1)


def show_error(msg: str):
    """Generic error display."""
    lcd.clear()
    lcd.print_line("!! ERROR !!",  row=0)
    lcd.print_line(msg[:16],       row=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Action handlers
# ═══════════════════════════════════════════════════════════════════════════════

def handle_issue(data: dict):
    """
    Book issued:
    • Green LED steady ON
    • Red LED blinks 3×
    • Buzzer: 2 short beeps
    • LCD: show ISSUED + title
    """
    global _heartbeat_active
    _heartbeat_active = False
    heartbeat_timer.deinit()

    green_led.value(1)
    red_led.value(0)

    book_id = data.get('book_id', '')
    title   = data.get('title',   'Unknown')

    show_book_issued(book_id, title)
    beep(100, count=2)
    blink_red(count=3, on_ms=150, off_ms=150)

    send_json({'status': 'OK', 'action': 'ISSUE'})
    print(f"[ISSUE] {book_id} — {title}")

    utime.sleep_ms(3000)
    _restore_idle()


def handle_return(data: dict):
    """
    Book returned:
    • Green LED steady ON
    • Red LED blinks 3×
    • Buzzer: 1 short beep
    • LCD: show RETURNED + title
    """
    global _heartbeat_active
    _heartbeat_active = False
    heartbeat_timer.deinit()

    green_led.value(1)
    red_led.value(0)

    book_id = data.get('book_id', '')
    title   = data.get('title',   'Unknown')

    show_book_returned(book_id, title)
    beep(100, count=1)
    blink_red(count=3, on_ms=150, off_ms=150)

    send_json({'status': 'OK', 'action': 'RETURN'})
    print(f"[RETURN] {book_id} — {title}")

    utime.sleep_ms(3000)
    _restore_idle()


def handle_invalid(data: dict):
    """
    Invalid / unknown QR:
    • Green LED OFF
    • Red LED steady ON during alert
    • Buzzer: 3 long beeps
    • LCD: show warning
    """
    global _heartbeat_active
    _heartbeat_active = False
    heartbeat_timer.deinit()

    green_led.value(0)
    red_led.value(1)

    show_invalid(data.get('book_id', ''))
    beep(500, count=3, gap_ms=200)   # 3 long warning beeps

    send_json({'status': 'OK', 'action': 'INVALID'})
    print("[INVALID] Unrecognised QR code")

    utime.sleep_ms(2000)
    red_led.value(0)
    _restore_idle()


def _restore_idle():
    """Re-enable idle heartbeat and show ready screen."""
    global _heartbeat_active
    show_idle()
    green_led.value(1)
    red_led.value(0)
    _heartbeat_active = True
    heartbeat_timer.init(
        period=800,
        mode=machine.Timer.PERIODIC,
        callback=_heartbeat_cb
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Serial packet processor
# ═══════════════════════════════════════════════════════════════════════════════

def process_packet(raw: str):
    """Parse a JSON packet from the laptop and dispatch to the right handler."""
    raw = raw.strip()
    if not raw:
        return

    try:
        data   = json.loads(raw)
        action = data.get('action', '').upper()

        if action == 'ISSUE':
            handle_issue(data)
        elif action == 'RETURN':
            handle_return(data)
        elif action == 'INVALID':
            handle_invalid(data)
        else:
            show_error(f"Bad action:{action}")
            send_json({'status': 'ERROR', 'message': f'Unknown action: {action}'})

    except ValueError as exc:
        # JSON parse error
        show_error("JSON ERR")
        send_json({'status': 'ERROR', 'message': f'JSON: {exc}'})
        print(f"[ERROR] JSON parse: {exc}  raw={raw!r}")

    except Exception as exc:
        show_error("RUNTIME ERR")
        send_json({'status': 'ERROR', 'message': str(exc)})
        print(f"[ERROR] Unhandled: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main loop
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """
    Start-up sequence then enter the main serial-read loop.

    The loop uses select.poll() with a short timeout so that the
    heartbeat timer can still fire in between reads.
    """
    # ── Startup ─────────────────────────────────────────────────────────────
    show_idle()
    green_led.value(1)
    red_led.value(0)
    beep(200, count=2)   # Two short startup beeps
    print("[BOOT] Smart Library Pico W controller ready.")
    print(f"[BOOT] Listening on USB-Serial at 115200 baud.")

    # ── Serial read loop ─────────────────────────────────────────────────────
    poll   = select.poll()
    poll.register(sys.stdin, select.POLLIN)
    buffer = ''

    while True:
        # Check for incoming data (50 ms timeout → keeps ISR responsive)
        events = poll.poll(50)

        if events:
            # Data available — read one character at a time
            ch = sys.stdin.read(1)
            if ch == '\n':
                process_packet(buffer)
                buffer = ''
            elif ch == '\r':
                pass    # ignore carriage returns
            else:
                buffer += ch

        # Watchdog: if buffer grows too long without a newline, flush it
        if len(buffer) > 512:
            print(f"[WARN] Buffer overflow, flushing: {buffer[:40]}…")
            buffer = ''


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    main()
