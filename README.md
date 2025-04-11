# VirtualBox Web Control Panel

A lightweight HTTP server script that provides a simple web interface to control and interact with VirtualBox virtual machines. This project allows you to:

- List available VMs
- Start, stop, and save state of VMs
- Send keystrokes to a VM
- View periodic screenshots of the VM's display

## Features

- **List VMs:** Fetch the list of available VirtualBox VMs.
- **Control Actions:** Start, shut down, or save the state of a VM using corresponding endpoints.
- **Keystroke Injection:** Convert plain text (with support for special tokens like `<enter>` or `<ctrl>`) into scancodes and send them to a selected VM.
- **Screenshot Capture:** Retrieve a live screenshot from the VM.
- **VM Details:** Display detailed VM configuration information in a sidebar within the web interface.
- **Responsive Web Interface:** The front-end dashboard updates periodically and provides feedback for actions executed on the VM.


---

## Prerequisites

- **VirtualBox:** Ensure VirtualBox is installed and the `VBoxManage` command is available on your system's PATH.
- **Python 3:** The script requires Python 3.x. It uses standard libraries such as `argparse`, `http.server`, `subprocess`, and `json`.


## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/nv1t/virtualbox-web-panel.git
   cd virtualbox-web-panel
   ```

2. Make the script executable:
   ```bash
   chmod +x vbox_web_control.py
   ```

3. (Optional) Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

---

## Usage

Run the server:
```bash
./vbox_web_control.py --port 9091
```

Then open your browser and navigate to:
```
http://localhost:9091
```

---

## Web Interface

- **Dropdown to select VM**
- **Buttons to start/save state/shutdown a VM**
- **Textbox to send keystrokes**
- **Live screenshot preview**

You can enter plain text or special keys in angled brackets. For example:
```
<ctrl>a<enter>
```

### Supported Special Keys
```
<enter> <ctrl> <shift> <alt> <tab> <backspace> <esc> <delete> <up> <down> <left> <right>
```

---

## API Endpoints

| Endpoint              | Description                            |
|----------------------|----------------------------------------|
| `/list-vms`          | Lists available VirtualBox VMs         |
| `/control-vm`        | Start/stop/save VM via query params    |
| `/send-keystrokes`   | Send scancode-based keystrokes to VM   |
| `/screenshot.png`    | Fetches latest screenshot of VM        |
| `/vm-status`         | Returns JSON VM state info             |
| `/vm-info`           | Returns detailed machine-readable information about the specified VM in JSON format. |

### API Parameter Reference

#### `/control-vm`
| Parameter | Type   | Description                          |
|-----------|--------|--------------------------------------|
| `vm`      | string | Name of the VM                       |
| `action`  | string | One of `start`, `poweroff`, `savestate` |

#### `/send-keystrokes`
| Parameter | Type   | Description                                                  |
|-----------|--------|--------------------------------------------------------------|
| `vm`      | string | Name of the VM                                               |
| `keys`    | string | Keystrokes, can include special tokens like `<ctrl>`, `<enter>` |

#### `/screenshot.png`
| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `vm`      | string | Name of the VM |

#### `/vm-status`
| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `vm`      | string | Name of the VM |

#### `/vm-info`
| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `vm`      | string | Name of the VM |

## Notes

- Combo key combinations (e.g., `<ctrl>+<alt>+del`) are not supported. Only sequential key presses are allowed.

- Ensure the VirtualBox VM is in a state that allows screenshot and keyboard input (e.g., running in headless mode).
- If screenshot generation fails, a fallback SVG will be shown.

---

## Contributing

Contributions and feedback are welcome! Feel free to fork the repository and submit pull requests to improve functionality, add features, or correct issues.

---

## Future Improvements

- Support for combo key combinations (e.g., `<ctrl>+<alt>+del`)
- Authentication layer for control access
- Configurable polling intervals for screenshots
- Command history/autocomplete in input box

