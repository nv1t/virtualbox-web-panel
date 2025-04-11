#!/usr/bin/env python3
import argparse
import http.server
import urllib.parse
import subprocess
import os
import json
import re
import socket  # Needed for error checking in run_server

# Mapping of characters to their corresponding keyboard scancodes.
KEYCODES = {
    'a': '1e', 'b': '30', 'c': '2e', 'd': '20', 'e': '12',
    'f': '21', 'g': '22', 'h': '23', 'i': '17', 'j': '24',
    'k': '25', 'l': '26', 'm': '32', 'n': '31', 'o': '18',
    'p': '19', 'q': '10', 'r': '13', 's': '1f', 't': '14',
    'u': '16', 'v': '2f', 'w': '11', 'x': '2d', 'y': '15',
    'z': '2c',
    '0': '0b', '1': '02', '2': '03', '3': '04', '4': '05',
    '5': '06', '6': '07', '7': '08', '8': '09', '9': '0a',
    ' ': '39',
    '-': '0c', '=': '0d', '[': '1a', ']': '1b', '\\': '2b',
    ';': '27', '\'': '28', '`': '29', ',': '33', '.': '34', '/': '35',
    '!': '02', '@': '03', '#': '04', '$': '05', '%': '06', '^': '07',
    '&': '08', '*': '09', '(': '0a', ')': '0b', '_': '0c', '+': '0d',
    '{': '1a', '}': '1b', '|': '2b', ':': '27', '"': '28', '~': '29',
    '<': '33', '>': '34', '?': '35'
}

# Scancode sequences for special keys.
SPECIAL_KEYCODES = {
    "backspace": ["0e", "8e"],
    "insert": ["e0", "52", "e0", "d2"],
    "home": ["e0", "47", "e0", "c7"],
    "end": ["e0", "4f", "e0", "cf"],
    "pageup": ["e0", "49", "e0", "c9"],
    "pagedown": ["e0", "51", "e0", "d1"],
    "left": ["e0", "4b", "e0", "cb"],
    "right": ["e0", "4d", "e0", "cd"],
    "up": ["e0", "48", "e0", "c8"],
    "down": ["e0", "50", "e0", "d0"],
    "ctrl": ["1d", "9d"],
    "strg": ["1d", "9d"],
    "shift": ["2a", "aa"],
    "alt": ["38", "b8"],
    "win": ["e0", "5b", "e0", "db"],
    "windows": ["e0", "5b", "e0", "db"],
    "esc": ["01", "81"],
    "escape": ["01", "81"],
    "enter": ["1c", "9c"],
    "return": ["1c", "9c"],
    "tab": ["0f", "8f"],
    "capslock": ["3a", "ba"],
    "f1": ["3b", "bb"], "f2": ["3c", "bc"], "f3": ["3d", "bd"], "f4": ["3e", "be"],
    "f5": ["3f", "bf"], "f6": ["40", "c0"], "f7": ["41", "c1"], "f8": ["42", "c2"],
    "f9": ["43", "c3"], "f10": ["44", "c4"], "f11": ["57", "d7"], "f12": ["58", "d8"],
    "del": ["53", "d3"], "delete": ["53", "d3"]
}

# Mapping for characters that require the Shift modifier.
SHIFT_REQUIRED = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6',
    '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
    ':': ';', '"': '28', '~': '29', '<': '33', '>': '34', '?': '35'
}
SHIFT_REQUIRED.update({chr(c): chr(c).lower() for c in range(ord('A'), ord('Z') + 1)})

def text_to_scancodes(text):
    """
    Converts text to a sequence of keyboard scancodes.
    If a character requires Shift, adds the necessary scancodes.
    """
    codes = []
    for ch in text:
        if ch in SHIFT_REQUIRED:
            base = SHIFT_REQUIRED[ch]
            if base not in KEYCODES:
                continue
            sc = KEYCODES[base]
            codes.extend(["2a", sc, format(int(sc, 16) + 0x80, 'x'), "aa"])
        elif ch.isupper():
            lower = ch.lower()
            if lower not in KEYCODES:
                continue
            sc = KEYCODES[lower]
            codes.extend(["2a", sc, format(int(sc, 16) + 0x80, 'x'), "aa"])
        elif ch in KEYCODES:
            sc = KEYCODES[ch]
            codes.extend([sc, format(int(sc, 16) + 0x80, 'x')])
        else:
            continue
    return codes

def parse_keys_input(input_str):
    """
    Parses tokens (e.g., <enter>, <ctrl>) and converts regular text to scancodes.
    """
    tokens = re.split(r'(<[^>]+>)', input_str)
    codes = []
    for token in tokens:
        if not token:
            continue
        if token.startswith("<") and token.endswith(">"):
            key_name = token[1:-1].lower()
            if key_name in SPECIAL_KEYCODES:
                codes.extend(SPECIAL_KEYCODES[key_name])
        else:
            codes.extend(text_to_scancodes(token))
    return codes

def run_vboxmanage_command(args):
    """
    Helper function to execute VBoxManage commands.
    Args:
        args (list): List of arguments for the VBoxManage command.
    Returns:
        subprocess.CompletedProcess: The result of the command execution.
    Raises:
        subprocess.CalledProcessError: If the command fails.
    """
    cmd = ["VBoxManage"] + args
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

class VirtualBoxHandler(http.server.BaseHTTPRequestHandler):
    def safe_write(self, data):
        """Write data to client (ignoring broken connections)."""
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            print("Client disconnected before response completed.")

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        route = parsed_url.path
        params = urllib.parse.parse_qs(parsed_url.query)

        # Endpoint: List available VMs.
        if route == "/list-vms":
            try:
                completed = run_vboxmanage_command(["list", "vms"])
                output = completed.stdout
                vm_names = re.findall(r'"([^"]+)"', output)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.safe_write(json.dumps(vm_names).encode())
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(f"Error listing VMs:\n{e.stderr}".encode())
            return

        # Main HTML Frontend.
        if route == "/":
            html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>VirtualBox Control Panel</title>
  <style>
    /* Global Styles */
    html, body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
      background: #f5f5f5;
      color: #333;
      height: 100%;
    }
    * { box-sizing: border-box; }

    /* VM Control Panel */
    #vm-controls {
      padding: 10px;
      text-align: center;
    }
    #vm-controls select,
    #vm-controls input,
    #vm-controls button {
      font-size: 1em;
      padding: 6px;
      margin: 5px;
    }
    .vm-button {
      background: #4CAF50;
      border: none;
      color: #fff;
      padding: 8px 16px;
      margin: 5px;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.3s;
    }
    .vm-button:hover { background: #45a049; }

    /* Screenshot Container */
    #screenshot-container {
      padding: 10px;
      text-align: center;
      margin-bottom: 150px; /* Extra bottom margin */
    }
    #screenshot {
      max-width: 90%;
      max-height: calc(100vh - 180px); /* Constrain height so input is not obstructed */
      height: auto;
      border: 1px solid #ccc;
    }

    /* Fixed Input Form */
    #inputForm {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: #fff;
      padding: 10px;
      box-shadow: 0 -2px 8px rgba(0,0,0,0.2);
    }
    #inputForm form {
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #inputForm label { margin-right: 10px; }
    #inputForm input[type="text"] {
      flex: 1;
      padding: 8px;
      font-size: 0.8em; /* Smaller text */
      border: 1px solid #ccc;
      border-radius: 4px;
    }

    /* Sidebar for Detailed VM Info */
    #vmInfoSidebar {
      position: fixed;
      top: 0;
      right: -680px;  /* Sidebar width is 700px; 20px remains visible when collapsed */
      width: 700px;
      height: 100%;
      background: #fff;
      box-shadow: -2px 0 8px rgba(0,0,0,0.3);
      transition: right 0.3s ease;
      overflow-y: auto;
      overflow-x: hidden;
      z-index: 1000;
    }
    #vmInfoSidebar.active { right: 0; }

    /* Sticky Header inside Sidebar for Toggle Button */
    #vmInfoHeader {
      position: sticky;
      top: 0;
      left: 0;
      width: 100%;
      background: #4CAF50;
      height: 40px;
      line-height: 40px;
      padding: 0 2px;
      z-index: 10;
      border-bottom: 1px solid #ccc;
      display: flex;
      align-items: center;
    }

    /* Toggle Icon inside Sidebar Header */
    #toggleSidebarIcon {
      cursor: pointer;
      font-size: 20px;
      user-select: none;
      color: #fff;
      flex-shrink: 0;
      padding: 0 0px;
    }

    /* Content inside Sidebar */
    #vmInfoContent {
      padding: 20px;
      width: 100%; /* Fill sidebar width */
      transition: none;
      word-wrap: break-word;   /* Force word wrap */
      overflow-wrap: break-word;
      white-space: normal;
    }

    /* VM Info Table */
    #vmInfoTable {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
      table-layout: fixed;
    }
    #vmInfoTable th,
    #vmInfoTable td {
      border: 1px solid #ccc;
      padding: 8px;
      text-align: left;
      word-wrap: break-word;
      overflow-wrap: break-word;
      white-space: normal;
    }
    #vmInfoTable th { background: #f2f2f2; }
  </style>
  <script>
    window.onload = function() {
      const input = document.getElementById("keys");
      input.addEventListener("keydown", function(event) {
        if (event.key === "Enter") {
          event.preventDefault();
          if (input.value === "") { input.value = "<enter>"; }
          sendKeys();
          input.value = "";
        } else if (event.key === "Backspace" && input.value === "") {
          event.preventDefault();
          input.value = "<backspace>";
          sendKeys();
          input.value = "";
        }
      });
      loadVMs();
      setInterval(updateScreenshot, 1000);
      setInterval(loadVMs, 10000);
    };

    // Control VM actions.
    function controlVM(action) {
      var vm = getSelectedVM();
      if (!vm) return;
      fetch(`/control-vm?vm=${encodeURIComponent(vm)}&action=${encodeURIComponent(action)}`)
      .then(response => response.text())
      .then(data => {
        alert(`VM action '${action}' executed. Response: ${data}`);
        updateVMStatusIcon();
      })
      .catch(error => console.error(`Error performing action '${action}' on VM:`, error));
    }

    // Load list of VMs.
    function loadVMs() {
      fetch("/list-vms")
      .then(response => response.json())
      .then(data => {
        var vmSelect = document.getElementById("vmSelect");
        var current = vmSelect.value;
        vmSelect.innerHTML = "";
        data.forEach(function(vm) {
          var option = document.createElement("option");
          option.value = vm;
          option.text = vm;
          if (vm === current) { option.selected = true; }
          vmSelect.appendChild(option);
        });
        updateSelectedVM();
        updateVMStatusIcon();
      })
      .catch(error => console.error("Error loading VMs:", error));
    }

    function getSelectedVM() {
      return document.getElementById("vmSelect").value;
    }

    // Update screenshot, VM status, and if sidebar is active, reload VM details.
    function updateSelectedVM() {
      updateScreenshot();
      updateVMStatusIcon();
      if(document.getElementById("vmInfoSidebar").classList.contains("active")){
        loadVMInfo();
      }
    }

    // Update the screenshot shown (used for live view).
    function updateScreenshot() {
      var vm = getSelectedVM();
      document.getElementById("screenshot").src = "/screenshot.png?vm=" + encodeURIComponent(vm) + "&ts=" + new Date().getTime();
    }

    // NEW: Download screenshot function.
    function downloadScreenshot() {
      var vm = getSelectedVM();
      // Build the URL with a timestamp to avoid caching issues and with download=1.
      var url = "/screenshot.png?vm=" + encodeURIComponent(vm) + "&download=1&ts=" + new Date().getTime();
      // Create an invisible link element.
      var link = document.createElement("a");
      link.href = url;
      link.download = "screenshot.png";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    function sendKeys() {
      var vm = getSelectedVM();
      var keys = document.getElementById("keys").value;
      fetch("/send-keystrokes?vm=" + encodeURIComponent(vm) + "&keys=" + encodeURIComponent(keys))
      .then(response => response.text())
      .then(data => { console.log("Keystroke response:", data); })
      .catch(error => console.error("Error sending keystrokes:", error));
    }

    function updateVMStatusIcon() {
      var vm = getSelectedVM();
      if (!vm) return;
      fetch("/vm-status?vm=" + encodeURIComponent(vm))
      .then(response => response.json())
      .then(data => {
        const icon = document.getElementById("vmStatusIcon");
        icon.textContent = data.running ? "🟢" : "🔴";
      })
      .catch(err => console.error("VM status fetch failed:", err));
    }

    // Toggle the sidebar.
    function toggleSidebar() {
      var sidebar = document.getElementById("vmInfoSidebar");
      var icon = document.getElementById("toggleSidebarIcon");
      if (sidebar.classList.contains("active")) {
        sidebar.classList.remove("active");
        icon.textContent = "◀ - VM Details";  // Collapsed state: click to slide out.
      } else {
        loadVMInfo();
        sidebar.classList.add("active");
        icon.textContent = "▶ - VM Details";  // Expanded state: click to slide in.
      }
    }

    // Load detailed VM info.
    function loadVMInfo() {
      var vm = getSelectedVM();
      if (!vm) return;
      fetch("/vm-info?vm=" + encodeURIComponent(vm))
      .then(response => response.json())
      .then(data => {
        var content = "";
        content += "<table id='vmInfoTable'><tr><th>Key</th><th>Value</th></tr>";
        for (var key in data) {
          content += "<tr><td>" + key + "</td><td>" + data[key] + "</td></tr>";
        }
        content += "</table>";
        document.getElementById("vmInfoContent").innerHTML = content;
      })
      .catch(error => console.error("Error loading VM info:", error));
    }
  </script>
</head>
<body>
  <div id="vm-controls">
    <!-- VM Control Buttons -->
    <button class="vm-button" onclick="controlVM('start')">Start</button>
    <button class="vm-button" onclick="controlVM('savestate')">Save State</button>
    <button class="vm-button" onclick="controlVM('poweroff')">Shutdown</button>
    <button class="vm-button" onclick="downloadScreenshot()">Screenshot</button>
    <br>
    <label for="vmSelect">Select VM:</label>
    <select id="vmSelect" onchange="updateSelectedVM()">
      <option value="">Loading VMs...</option>
    </select>
    <span id="vmStatusIcon"></span>
  </div>
  <div id="screenshot-container">
    <img id="screenshot" src="/screenshot.png" alt="VM Screenshot">
  </div>
  <!-- Fixed Input Form -->
  <div id="inputForm">
    <form onsubmit="return false;">
      <label for="keys">Enter keystrokes (e.g., &lt;ctrl&gt;, &lt;shift&gt;):</label>
      <input type="text" id="keys" name="keys" required>
    </form>
  </div>
  <!-- Sidebar for Detailed VM Info -->
  <div id="vmInfoSidebar">
    <div id="vmInfoHeader">
      <!-- Sticky header with toggle button fixed at top -->
      <div id="toggleSidebarIcon" onclick="toggleSidebar()">◀ VM Details</div>
    </div>
    <div id="vmInfoContent">Loading VM info...</div>
  </div>
</body>
</html>
"""
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.safe_write(html.encode())
            return

        # Endpoint: Control VM actions.
        if route == "/control-vm":
            vm_name = params.get("vm", ["myVM"])[0]
            action = params.get("action", [""])[0].lower()
            if action not in ["start", "poweroff", "savestate"]:
                self.send_response(400)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(b"Invalid VM action requested.")
                return
            try:
                if action == "start":
                    run_vboxmanage_command(["startvm", vm_name, "--type", "headless"])
                else:
                    run_vboxmanage_command(["controlvm", vm_name, action])
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(f"Action '{action}' executed on VM '{vm_name}'.".encode())
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(f"Error executing action '{action}' on VM '{vm_name}': {e.stderr}".encode())
            return

        # Endpoint: Fetch screenshot.
        if route == "/screenshot.png":
            vm_name = params.get("vm", ["myVM"])[0]
            screenshot_path = "screenshot.png"
            try:
                run_vboxmanage_command(["controlvm", vm_name, "screenshotpng", screenshot_path])
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                # NEW: Check if download parameter is present, and add content-disposition.
                if params.get("download", ["0"])[0] == "1":
                    self.send_header("Content-Disposition", "attachment; filename=\"screenshot.png\"")
                self.end_headers()
                with open(screenshot_path, "rb") as f:
                    content = f.read()
                self.safe_write(content)
            except subprocess.CalledProcessError:
                self.send_response(200)
                self.send_header("Content-type", "image/svg+xml")
                if params.get("download", ["0"])[0] == "1":
                    self.send_header("Content-Disposition", "attachment; filename=\"screenshot.svg\"")
                self.end_headers()
                self.safe_write(b"<svg width=\"300\" height=\"200\" xmlns=\"http://www.w3.org/2000/svg\"><rect width=\"100%\" height=\"100%\" fill=\"#f0f0f0\"/><text x=\"50%\" y=\"50%\" text-anchor=\"middle\" dominant-baseline=\"middle\" font-family=\"Arial, sans-serif\" font-size=\"20\" fill=\"#888\">No Image available</text></svg>")
            return

        # Endpoint: Send keystrokes.
        if route == "/send-keystrokes":
            vm_name = params.get("vm", ["myVM"])[0]
            if "keys" not in params:
                self.send_response(400)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(b"Missing required query parameter 'keys'.")
                return
            keys_input = params["keys"][0]
            scancodes = parse_keys_input(keys_input)
            if not scancodes:
                self.send_response(400)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(b"Unable to convert input string to scancodes.")
                return
            try:
                run_vboxmanage_command(["controlvm", vm_name, "keyboardputscancode"] + scancodes)
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(f"Keystrokes sent to VM '{vm_name}' successfully.".encode())
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.safe_write(f"Error sending keystrokes to VM '{vm_name}': {e.stderr}".encode())
            return

        # Endpoint: Return VM status.
        if route == "/vm-status":
            vm_name = params.get("vm", ["myVM"])[0]
            try:
                result = run_vboxmanage_command(["showvminfo", vm_name, "--machinereadable"])
                running = 'VMState="running"' in result.stdout
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.safe_write(json.dumps({"running": running}).encode())
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.safe_write(json.dumps({"error": e.stderr}).encode())
            return

        # Endpoint: Return detailed VM info.
        if route == "/vm-info":
            vm_name = params.get("vm", ["myVM"])[0]
            try:
                result = run_vboxmanage_command(["showvminfo", vm_name, "--machinereadable"])
                info_lines = result.stdout.splitlines()
                info = {}
                for line in info_lines:
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"')
                        info[key] = value
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.safe_write(json.dumps(info, indent=2).encode())
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.safe_write(json.dumps({"error": e.stderr}).encode())
            return

        # 404 Not Found.
        self.send_response(404)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.safe_write(b"Route not found.\n")

# Start the server on the specified port.
def run_server(start_port, max_tries=10):
    for i in range(max_tries):
        port = start_port + i
        try:
            server_address = ("", port)
            httpd = http.server.HTTPServer(server_address, VirtualBoxHandler)
            print(f"Server started on port {port}.")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("Server is shutting down.")
                httpd.server_close()
            break
        except OSError as e:
            if e.errno == socket.errno.EADDRINUSE:
                print(f"Port {port} is in use, trying next...")
            else:
                raise
    else:
        print(f"Could not start server after trying {max_tries} ports.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9091, help="Starting port for the server")
    args = parser.parse_args()
    run_server(args.port)
