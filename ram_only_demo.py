import socket    # for network info (runs in RAM)
import platform  # for system info (runs in RAM)
import datetime  # for current time (runs in RAM)


# ── STEP 1: All variables live in RAM ──────────────────────
name     = "RAM Demo Program"   # stored in RAM
version  = "1.0"                # stored in RAM
messages = []                   # list stored in RAM

# ── STEP 2: Function runs in RAM ───────────────────────────
def add_message(msg):
    # This adds data to RAM (not saved anywhere)
    messages.append(msg)

# ── STEP 3: Socket module - get computer network info ──────
def get_network_info():
    hostname   = socket.gethostname()                  # RAM
    ip_address = socket.gethostbyname(hostname)        # RAM
    return hostname, ip_address
# ── STEP 4: Main program ───────────────────────────────────
def main():

    print("=" * 50)
    print("   PYTHON - RAM ONLY DEMO")
    print("=" * 50)

    # System info (all stored temporarily in RAM)
    hostname, ip = get_network_info()
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    os_name      = platform.system()

    print(f"\n  Computer Name : {hostname}")
    print(f"  IP Address    : {ip}")
    print(f"  OS            : {os_name}")
    print(f"  Time          : {current_time}")

    print("\n" + "-" * 50)
    print("  Loading messages into RAM...")
    print("-" * 50)

    # Add messages to RAM list
    add_message("Hello from RAM!")
    add_message("I am NOT saved to disk.")
    add_message("When program ends, I disappear.")
    add_message("Socket gave us network info from RAM too!")

    # Show messages from RAM
    for i, msg in enumerate(messages, 1):
        print(f"  Message {i}: {msg}")

    print("\n" + "-" * 50)
    print("  RAM is now being cleared...")
    print("  Program closing. All data gone!")
    print("=" * 50)

# ── RUN ────────────────────────────────────────────────────
if __name__ == "__main__":
    main()