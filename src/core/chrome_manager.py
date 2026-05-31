"""
Chrome browser and tab management.
"""

import subprocess
from pathlib import Path
import os
import socket
import struct
import base64
import json
import time
import urllib.request


class ChromeManager:
    """Manages Chrome browser and tab interactions."""

    # GPU acceleration flags - balanced set that works reliably
    # Removed flags that can cause GPU process to crash
    GPU_FLAGS = [
        "--disable-blink-features=AutomationControlled",  # Helps with some sites
        "--enable-gpu-rasterization",
        "--enable-native-gpu-memory-buffers",
    ]

    def __init__(self):
        """Initialize the Chrome manager."""
        self.chrome_path = self.find_chrome()
        self.env = self._setup_environment()

    def _setup_environment(self):
        """Setup environment variables for GPU acceleration."""
        env = os.environ.copy()
        
        # Pass GPU-related environment variables to Chrome processes
        # These ensure Chrome inherits the GPU configuration from the system
        gpu_env_vars = [
            'VK_ICD_FILENAMES',  # Vulkan driver
            'DXVK_HUD',  # D3D11 diagnostics
            'VKDEVICE',  # Vulkan device selection
            'AMD_DEVICE_SPECS',  # AMD-specific device info
        ]
        
        for var in gpu_env_vars:
            if var in os.environ:
                print(f"  GPU env {var}: {os.environ[var]}")
        
        return env

    def find_chrome(self):
        """Locate Chrome executable on the system."""
        common_paths = [
            Path("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"),
            Path("C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"),
            Path(Path.home() / "AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def open_url(self, url):
        """Open a URL in Chrome."""
        if self.chrome_path and self.chrome_path.exists():
            try:
                print(f"    Opening Chrome: {self.chrome_path}")
                import os
                # Use os.startfile for native Windows launching (avoids elevation issues)
                os.startfile(str(self.chrome_path), arguments=url)
                print(f"    Launched via os.startfile()")
                return True
            except Exception as e:
                print(f"    Error: {e}")
                return False
        else:
            print(f"    Chrome NOT found. Tried: {self.chrome_path}")
            return False

    def open_urls_with_profile(self, urls, profile_name=None):
        """Open multiple URLs in Chrome with a specific profile."""
        if not self.chrome_path or not self.chrome_path.exists():
            print("Chrome not found on this system")
            return False

        cmd = [str(self.chrome_path)]
        if profile_name:
            cmd.extend([f"--profile-directory={profile_name}"])

        cmd.extend(urls)

        try:
            subprocess.Popen(cmd)
            return True
        except Exception as e:
            print(f"Error opening URLs in Chrome: {e}")
            return False

    def open_url_positioned(self, url, x, y, width, height, profile_name=None):
        """
        Open a URL in Chrome with native window positioning.
        
        This launches Chrome with --window-position and --window-size flags,
        allowing Chrome to open directly at the target location rather than
        being moved post-launch. This is better for GPU initialization.
        
        Args:
            url: URL to open
            x: X coordinate for window position
            y: Y coordinate for window position
            width: Window width in pixels
            height: Window height in pixels
            profile_name: Optional Chrome profile directory name
            
        Returns:
            True if successfully launched, False otherwise
        """
        if not self.chrome_path or not self.chrome_path.exists():
            print(f"Chrome NOT found at: {self.chrome_path}")
            return False

        try:
            cmd = [str(self.chrome_path)]
            
            # Force new window (prevents tabs from consolidating in existing window)
            cmd.append("--new-window")
            
            # Add positioning flags (will be applied when window opens)
            cmd.extend([
                f"--window-position={x},{y}",
                f"--window-size={width},{height}"
            ])
            
            # Add GPU acceleration flags
            cmd.extend(self.GPU_FLAGS)
            
            # Add URL
            cmd.append(url)
            
            print(f"    Launching Chrome tab:")
            print(f"      Position: ({x}, {y}), Size: {width}x{height}")
            print(f"      GPU Flags: {len(self.GPU_FLAGS)} acceleration flags enabled")
            
            # Launch with inherited GPU environment variables
            # Use shell=True to avoid elevation conflicts on Windows
            subprocess.Popen(cmd, env=self.env, shell=True)
            
            print(f"    Launched via subprocess.Popen() with GPU env vars")
            print(f"    (Native Chrome positioning: ({x}, {y}) {width}x{height})")
            return True
            
        except Exception as e:
            print(f"    Error launching positioned Chrome: {e}")
            import traceback
            traceback.print_exc()
            return False


class ChromeCDPSession:
    """
    Minimal Chrome DevTools Protocol (CDP) client for precise window positioning.

    Launches Chrome with --remote-debugging-port, then uses CDP to create each
    window via Target.createTarget and position it via Browser.setWindowBounds.
    This bypasses Windows UIPI restrictions entirely because Chrome is moving
    its own windows rather than an external process trying to move them.

    Uses only Python stdlib (socket, struct, base64, json, urllib) — no extra deps.
    """

    PORT = 9222

    def __init__(self):
        self._sock = None
        self._msg_id = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def launch_chrome(self, chrome_path: Path, gpu_flags: list) -> bool:
        """
        Launch Chrome headlessly (--no-startup-window) with the DevTools debug
        port.  Uses os.startfile so the child process is spawned via
        ShellExecuteEx ("open" verb), which de-elevates even when Python is
        running elevated — this is required for Chrome's DevTools HTTP server
        to bind on 127.0.0.1:9222.
        CDP will create every window; no URL needed at launch time.
        """
        flags = [
            f"--remote-debugging-port={self.PORT}",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-startup-window",
            "--disable-session-crashed-bubble",
        ] + list(gpu_flags)
        args_str = " ".join(flags)
        # ShellExecuteEx "open" from an elevated process routes through
        # explorer.exe and uses the interactive user's standard (non-admin)
        # token — exactly how the legacy os.startfile() fallback works.
        os.startfile(str(chrome_path), "open", args_str)
        return True

    def wait_for_port(self, timeout: float = 15.0, log=None) -> bool:
        """Block until Chrome's debug HTTP endpoint is reachable."""
        deadline = time.time() + timeout
        first_err: str | None = None
        while time.time() < deadline:
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{self.PORT}/json/version", timeout=1
                )
                return True
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                if first_err is None:
                    first_err = err
                    msg = f"  [CDP] Waiting for port {self.PORT} — {err}"
                    if log:
                        log(msg)
                    else:
                        print(msg)
                time.sleep(0.3)
        msg = f"  [CDP] wait_for_port timed out — last error: {first_err}"
        if log:
            log(msg)
        else:
            print(msg)
        return False

    def connect(self) -> bool:
        """Open a WebSocket connection to Chrome's browser-level CDP endpoint."""
        try:
            data = json.loads(
                urllib.request.urlopen(
                    f"http://127.0.0.1:{self.PORT}/json/version", timeout=5
                ).read()
            )
            ws_url = data["webSocketDebuggerUrl"]
            # ws://127.0.0.1:PORT/devtools/browser/<guid>
            path = ws_url.split(f":{self.PORT}")[1]

            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(10)
            self._sock.connect(("127.0.0.1", self.PORT))

            key = base64.b64encode(os.urandom(16)).decode()
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.PORT}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"\r\n"
            )
            self._sock.sendall(handshake.encode())

            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += self._sock.recv(4096)

            if b"101" not in resp:
                self._sock.close()
                self._sock = None
                return False

            self._sock.settimeout(8.0)
            return True
        except Exception as e:
            print(f"CDP connect error: {e}")
            return False

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    # ------------------------------------------------------------------
    # WebSocket framing (RFC 6455)
    # ------------------------------------------------------------------

    def _send_frame(self, text: str):
        """Send a masked WebSocket text frame (client→server must be masked)."""
        payload = text.encode("utf-8")
        n = len(payload)
        mask = os.urandom(4)
        masked = bytes(payload[i] ^ mask[i % 4] for i in range(n))

        if n < 126:
            header = bytes([0x81, 0x80 | n]) + mask
        elif n < 65536:
            header = bytes([0x81, 0xFE]) + struct.pack(">H", n) + mask
        else:
            header = bytes([0x81, 0xFF]) + struct.pack(">Q", n) + mask

        self._sock.sendall(header + masked)

    def _recv_frame(self) -> str | None:
        """
        Receive a complete WebSocket message from Chrome, accumulating
        continuation frames (fragmented messages).

        Chrome often sends large CDP event payloads as multiple frames
        (FIN=0 text frame followed by FIN=1 continuation frames).  Reading
        only the first frame causes frame-sync loss on the next call, which
        can produce a bogus huge length and hang forever in recv_exact.
        This implementation keeps reading until FIN=1.
        """
        def recv_exact(n: int) -> bytes:
            if n > 16 * 1024 * 1024:  # Sanity cap: 16 MB
                raise ValueError(f"WebSocket frame length too large: {n}")
            buf = b""
            while len(buf) < n:
                chunk = self._sock.recv(min(65536, n - len(buf)))
                if not chunk:
                    raise ConnectionError("WebSocket closed")
                buf += chunk
            return buf

        fragments = b""
        while True:
            header = recv_exact(2)
            fin    = bool(header[0] & 0x80)
            opcode = header[0] & 0x0F
            masked = bool(header[1] & 0x80)
            length = header[1] & 0x7F

            if length == 126:
                length = struct.unpack(">H", recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", recv_exact(8))[0]

            mask    = recv_exact(4) if masked else b""
            payload = recv_exact(length)
            if mask:
                payload = bytes(payload[i] ^ mask[i % 4] for i in range(length))

            if opcode == 0x8:   # Close
                return None
            if opcode == 0x9:   # Ping — skip
                continue
            if opcode == 0xA:   # Pong — skip
                continue
            if opcode == 0x1:   # New text frame (possibly first fragment)
                fragments = payload
            elif opcode == 0x0: # Continuation frame
                fragments += payload
            # else: unknown opcode, skip

            if fin:
                return fragments.decode("utf-8", errors="replace")

    # ------------------------------------------------------------------
    # CDP commands
    # ------------------------------------------------------------------

    def _send_cmd(self, method: str, params: dict = None) -> dict:
        """
        Send a CDP command and return its result dict.
        Skips event messages (no 'id') until the matching response arrives.
        """
        self._msg_id += 1
        mid = self._msg_id
        self._send_frame(json.dumps({"id": mid, "method": method,
                                     "params": params or {}}))
        for _ in range(500):  # skip up to 500 events before giving up
            try:
                raw = self._recv_frame()
            except socket.timeout:
                print(f"CDP timeout waiting for '{method}'")
                return {}
            if raw is None:
                return {}
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == mid:
                return msg.get("result", {})
        return {}

    def open_window_at(self, url: str, x: int, y: int,
                       width: int, height: int) -> bool:
        """
        Create a new Chrome window for url and position it exactly at (x,y,w,h).
        Returns True on success.
        """
        result = self._send_cmd("Target.createTarget", {
            "url": url,
            "newWindow": True,
            "width": width,
            "height": height,
        })
        target_id = result.get("targetId")
        if not target_id:
            return False

        # Chrome may need a brief moment to associate the target with a window
        window_id = None
        for _ in range(5):
            res = self._send_cmd("Browser.getWindowForTarget",
                                 {"targetId": target_id})
            window_id = res.get("windowId")
            if window_id is not None:
                break
            time.sleep(0.2)

        if window_id is None:
            return False

        self._send_cmd("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {
                "left": x,
                "top": y,
                "width": width,
                "height": height,
                "windowState": "normal",
            },
        })
        return True

