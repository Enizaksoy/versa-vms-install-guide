"""
Probe vsh configure: run with PTY shell, capture prompts for first ~60s,
abort to study what comes next. This tells us the prompt sequence WITHOUT
committing to a long install.
"""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import paramiko

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

print("=== Probing vsh configure (read-only, abort after first prompt) ===")
chan = s.client.invoke_shell(term='xterm', width=200, height=50)
chan.settimeout(2.0)

# wait for shell prompt
time.sleep(2)
buf = ''
while chan.recv_ready():
    buf += chan.recv(65535).decode(errors='replace')

# send command
chan.send('vsh configure\n')
print("[sent: vsh configure]\n")

# Read for 90 sec
buf = ''
end = time.time() + 90
last_data = time.time()
while time.time() < end:
    if chan.recv_ready():
        d = chan.recv(65535).decode(errors='replace')
        buf += d
        sys.stdout.write(d)
        sys.stdout.flush()
        last_data = time.time()
    else:
        time.sleep(0.3)
        # If no data for 8 sec and we have a prompt, break
        if time.time() - last_data > 8 and buf and re.search(r'(:|\?|\[Y/n\]|\[y/N\])\s*\x1b?\[?[0-9;m]*$', buf.split('\n')[-1].strip()):
            print("\n[stalled at prompt — breaking probe]")
            break

# Send Ctrl-C to abort and exit
print("\n[sending Ctrl-C to abort]")
chan.send('\x03')
time.sleep(2)
chan.send('exit\n')
time.sleep(1)
chan.close()
s.close()
