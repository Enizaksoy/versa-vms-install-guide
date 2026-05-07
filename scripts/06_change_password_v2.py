"""
v2: Stronger password (19 chars, no dict word) + robust state machine.
"""
import sys, time, re
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST = '192.168.30.15'
USER = 'admin'
OLD_PASS = '<default-ova-pass>'
NEW_PASS = '<vms-admin-pass>'  # 19 chars

def drain(chan, timeout=2.0):
    end = time.time() + timeout
    buf = ''
    while time.time() < end:
        if chan.recv_ready():
            data = chan.recv(65535).decode('utf-8', errors='replace')
            buf += data
            sys.stdout.write(data); sys.stdout.flush()
            end = time.time() + 0.5  # extend on data
        else:
            time.sleep(0.1)
    return buf

def expect_one(chan, patterns, timeout=30):
    """Wait until ANY pattern matches in incoming data. Returns (idx, full_buf) or (-1, buf) on timeout."""
    buf = ''
    end = time.time() + timeout
    while time.time() < end:
        if chan.recv_ready():
            data = chan.recv(65535).decode('utf-8', errors='replace')
            buf += data
            sys.stdout.write(data); sys.stdout.flush()
            for i, pat in enumerate(patterns):
                if re.search(pat, buf, re.IGNORECASE):
                    return i, buf
        else:
            time.sleep(0.2)
    return -1, buf

def send(chan, text, hide=False):
    if hide:
        print(f"[SEND: {'*' * len(text)}]")
    else:
        print(f"[SEND: {text!r}]")
    chan.send(text + '\n')

def main():
    print(f"=== Connecting as {USER} (old pass) ===")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=OLD_PASS, timeout=15,
              allow_agent=False, look_for_keys=False)
    chan = c.invoke_shell(term='xterm', width=200, height=50)

    # initial banner + prompt
    expect_one(chan, [r'\$\s*$', r'#\s*$'], timeout=15)

    send(chan, 'vsh modify-system-password')

    # Stage 1: sudo password
    idx, _ = expect_one(chan, [
        r'\[sudo\] password for',
        r'New password:',
    ], timeout=15)
    if idx == 0:
        send(chan, OLD_PASS, hide=True)
        # Stage 1b: now wait for "New password:"
        idx, _ = expect_one(chan, [r'New password:'], timeout=20)
        if idx != 0:
            print("\n[ERROR] no New password prompt after sudo")
            c.close()
            return 1
    elif idx == 1:
        pass  # already at New password prompt
    else:
        print("\n[ERROR] no sudo or New password prompt")
        c.close()
        return 1

    # Stage 2: send new password
    send(chan, NEW_PASS, hide=True)

    # Stage 3: retype OR BAD PASSWORD
    idx, buf = expect_one(chan, [
        r'Retype new password:',
        r'BAD PASSWORD',
        r'Aborted',
    ], timeout=15)
    if idx == 1:
        print("\n[ERROR] BAD PASSWORD on first entry")
        # Drain and abort
        drain(chan, 5)
        c.close()
        return 2
    if idx == 2:
        print("\n[ERROR] Operation Aborted")
        c.close()
        return 2
    if idx != 0:
        print("\n[ERROR] no Retype prompt")
        c.close()
        return 1

    # Stage 4: confirm password
    send(chan, NEW_PASS, hide=True)

    # Stage 5: success indicators
    idx, buf = expect_one(chan, [
        r'(password updated successfully|successfully changed|authentication token (manipulation error|updated successfully))',
        r'Aborted',
        r'BAD PASSWORD',
        r'Sorry, passwords do not match',
        r'\[admin@vms-1.*\]\s*\$\s*$',  # back to shell prompt
    ], timeout=20)

    if idx in (1, 2, 3):
        print(f"\n[ERROR] failure indicator hit ({idx})")
        drain(chan, 5)
        c.close()
        return 2

    print("\n[stage 5 passed — looks like success or back at prompt]")
    drain(chan, 3)
    c.close()

    # Verify with new password
    print(f"\n=== Verifying with new password ===")
    time.sleep(3)
    try:
        c2 = paramiko.SSHClient()
        c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c2.connect(HOST, username=USER, password=NEW_PASS, timeout=15,
                   allow_agent=False, look_for_keys=False)
        _, o, _ = c2.exec_command("hostname && id && date", timeout=10)
        print(o.read().decode())
        c2.close()
        print(f"\n=== SUCCESS — new password works ===")
        print(f"NEW_PASSWORD = {NEW_PASS}")
        return 0
    except Exception as e:
        print(f"=== FAILED: {e} ===")
        try:
            c3 = paramiko.SSHClient()
            c3.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c3.connect(HOST, username=USER, password=OLD_PASS, timeout=15,
                       allow_agent=False, look_for_keys=False)
            print("[old password still works — change did not take effect]")
            c3.close()
            return 3
        except Exception:
            print("[BOTH passwords fail — check ESXi console immediately]")
            return 4

if __name__ == '__main__':
    sys.exit(main())
