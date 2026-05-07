"""
Upload pre-upgrade patch to VMS and apply via vsh system-upgrade.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
LOCAL_PATCH = r'C:\Users\eniza\Downloads\vms_5.2.2_pre_upgrade_patch.bin'
REMOTE_PATCH = '/home/versa/packages/vms_5.2.2_pre_upgrade_patch.bin'

s = VmsSSH(HOST, USER, PASSWORD)

# 0) Pre-state
print("=== Versa packages dir before ===")
s.run("ls -la /home/versa/packages/ 2>/dev/null", sudo=True)
s.run("vsh status 2>&1 | head -25", login=True)

# 1) Upload patch via SFTP
print(f"\n=== Uploading {LOCAL_PATCH} -> {REMOTE_PATCH} ===")
s.run("mkdir -p /home/versa/packages/ && chown versa:versa /home/versa/packages/", sudo=True)

# Upload to /tmp first then move (admin can't write to /home/versa/packages/ directly)
sftp = s.client.open_sftp()
sftp.put(LOCAL_PATCH, '/tmp/vms_5.2.2_pre_upgrade_patch.bin')
sftp.close()
s.run(f"mv /tmp/vms_5.2.2_pre_upgrade_patch.bin {REMOTE_PATCH} && chmod 755 {REMOTE_PATCH} && ls -la {REMOTE_PATCH}", sudo=True)

# 2) Verify file shape — is it a self-extracting bin?
print("\n=== Patch file inspection ===")
s.run(f"file {REMOTE_PATCH}", sudo=True)
s.run(f"head -5 {REMOTE_PATCH} | head -c 200 | od -c | head -10", sudo=True)

# 3) Apply via vsh system-upgrade
# NOTE: vsh's system-upgrade calls initmsghelper.sh -a system-upgrade -p <file>
# It tails /var/log/versa/upgrade.log automatically.
print(f"\n=== Apply via vsh system-upgrade ===")
print("(this may take several minutes; monitoring upgrade.log)")

# Run via interactive shell so we can see live output, but don't tail forever
chan = s.client.invoke_shell(term='xterm', width=200, height=50)
chan.settimeout(2.0)

# wait for prompt
time.sleep(2)
while chan.recv_ready():
    chan.recv(65535)

chan.send(f"vsh system-upgrade {REMOTE_PATCH}\n")

import re
buf = ''
end = time.time() + 60 * 30  # 30 min cap
last = time.time()
while time.time() < end:
    if chan.recv_ready():
        d = chan.recv(65535).decode(errors='replace')
        buf += d
        sys.stdout.write(d)
        sys.stdout.flush()
        last = time.time()
        # break when we see a known terminator
        tail = buf[-500:]
        if re.search(r'(installation.*complete|upgrade.*successful|failed|error|\[admin@vms-1.*\]\s*\$\s*$)', tail, re.I):
            time.sleep(3)
            # one more drain
            while chan.recv_ready():
                d2 = chan.recv(65535).decode(errors='replace')
                buf += d2
                sys.stdout.write(d2)
                sys.stdout.flush()
            break
    else:
        time.sleep(0.5)
        if time.time() - last > 300:
            print("\n[STALL > 5 min, sending Ctrl-C]")
            chan.send('\x03')
            time.sleep(2)
            break

# Send Ctrl-C in case tail -f is still running
chan.send('\x03')
time.sleep(1)
chan.close()

# 4) Final status
print("\n=== Final vsh status ===")
s.run("vsh status 2>&1 | head -30", login=True)

s.close()
