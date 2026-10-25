"""
Smart Library — qr_scanner.py
Robust QR scanner using OpenCV built-in detector
Works without pyzbar — no extra installation needed
"""

import cv2
import threading
import time
import numpy as np


class QRScanner:
    def __init__(self, camera_index=0, cooldown=3.0):
        self.camera_index = camera_index
        self.cooldown     = cooldown
        self.cap          = None
        self.running      = False
        self._frame       = None
        self._last_scanned= {}
        self._lock        = threading.Lock()
        self._thread      = None
        self.on_scan_callback = None

        # Try best available detector
        self._detector = None
        self._det_name = ''
        try:
            self._detector = cv2.QRCodeDetectorAruco()
            self._det_name = 'Aruco'
        except Exception:
            try:
                self._detector = cv2.QRCodeDetector()
                self._det_name = 'OpenCV'
            except Exception:
                self._det_name = 'None'

        print(f"[SCANNER] Using detector: {self._det_name}")

    def set_callback(self, callback):
        self.on_scan_callback = callback

    def start(self):
        # Try camera indices 0,1,2
        for idx in [self.camera_index, 1, 2]:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.cap = cap
                    self.camera_index = idx
                    print(f"[SCANNER] Camera found at index {idx}")
                    break
                cap.release()

        if self.cap is None:
            # Try without CAP_DSHOW
            for idx in [0, 1, 2]:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    self.cap = cap
                    self.camera_index = idx
                    print(f"[SCANNER] Camera found at index {idx} (fallback)")
                    break

        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(
                "No webcam found! Make sure camera is connected and not used by another app."
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        self.cap = None

    def get_frame(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def is_running(self):
        return self.running

    def _scan_loop(self):
        fail_count = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                fail_count += 1
                if fail_count > 30:
                    print("[SCANNER] Camera read failed repeatedly")
                    break
                time.sleep(0.05)
                continue
            fail_count = 0

            # Try to detect QR
            qr_data = self._detect_qr(frame)

            if qr_data:
                now  = time.monotonic()
                last = self._last_scanned.get(qr_data, 0)
                if (now - last) > self.cooldown:
                    self._last_scanned[qr_data] = now
                    # Green overlay on detection
                    cv2.putText(frame, f"QR: {qr_data[:25]}", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 0), 2)
                    if self.on_scan_callback:
                        threading.Thread(
                            target=self.on_scan_callback,
                            args=(qr_data,),
                            daemon=True
                        ).start()

            # Status overlay
            status = f"SCANNING [{self._det_name}]"
            cv2.putText(frame, status, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 0), 2)

            with self._lock:
                self._frame = frame

            time.sleep(0.033)

    def _detect_qr(self, frame):
        """Try multiple methods to detect QR code."""
        if self._detector is None:
            return None

        # Method 1: Standard detect
        try:
            data, bbox, _ = self._detector.detectAndDecode(frame)
            if data and data.strip():
                if bbox is not None:
                    pts = bbox.astype(int)
                    cv2.polylines(frame, [pts], True, (0, 230, 0), 3)
                return data.strip()
        except Exception:
            pass

        # Method 2: Try on grayscale
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            data, bbox, _ = self._detector.detectAndDecode(gray)
            if data and data.strip():
                return data.strip()
        except Exception:
            pass

        # Method 3: Try on sharpened image
        try:
            kernel  = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharp   = cv2.filter2D(frame, -1, kernel)
            data, bbox, _ = self._detector.detectAndDecode(sharp)
            if data and data.strip():
                return data.strip()
        except Exception:
            pass

        # Method 4: Try on zoomed center
        try:
            h, w = frame.shape[:2]
            cx, cy = w // 4, h // 4
            crop   = frame[cy:cy+h//2, cx:cx+w//2]
            data, bbox, _ = self._detector.detectAndDecode(crop)
            if data and data.strip():
                return data.strip()
        except Exception:
            pass

        return None
