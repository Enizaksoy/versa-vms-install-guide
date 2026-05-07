"""
Change admin password from '<default-ova-pass>' to <old-admin-pass> using vsh modify-system-password.
Uses invoke_shell + expect-style prompt matching.
"""
import sys, time, re
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST = '192.168.30.15'
USER = 'admin'
OLD_PASS = '<default-ova-pass>'
NEW_PASS = '<old-admin-pass>'

def expect(chan, patterns, timeout=30):
    """Read from channel until any of patterns regex matches. Return (matched_pattern, full_buffer)."""
    buf = ''
    end = time.time() + timeout
    while time.time() < end:
        if chan.recv_ready():
            data = chan.recv(65535).decode('utf-8', errors='replace')
            buf += data
            sys.stdout.write(data)
            sys.stdout.flush()
            for pat in patterns:
                if re.search(pat, buf, re.IGNORECASE):
                    return pat, buf
        else:
            time.sleep(0.3)
    return None, buf

def send(chan, text, hide=False):
    if hide:
        print(f"[sending: {'*' * 8}]")
    else:
        print(f"[sending: {text!r}]")
    chan.send(text + '\n')

def main():
    print(f"=== Connecting to {HOST} as {USER} (old pass) ===")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=OLD_PASS, timeout=15,
              allow_agent=False, look_for_keys=False)
    chan = c.invoke_shell(term='xterm', width=200, height=50)
    chan.settimeout(2.0)

    # Wait for shell prompt
    expect(chan, [r'\$\s*$', r'#\s*$'], timeout=15)
    print("\n[shell ready]\n")

    # Run vsh modify-system-password
    send(chan, 'vsh modify-system-password')

    # vsh runs with sudo internally; may ask for sudo password first
    # Then prompts for current/new/confirm
    while True:
        pat, buf = expect(chan, [
            r'\[sudo\] password for',
            r'(current|old).*password',
            r'(new|enter new).*password',
            r'(retype|confirm|verify).*password',
            r'password.*updated|password.*changed|successfully',
            r'authentication.*token.*updated',
            r'\$\s*$',
            r'#\s*$',
            r'BAD PASSWORD|password.*unchanged',
            r'enter.*username|user.*name',
        ], timeout=20)
        if not pat:
            print("\n[timeout — sending blank line and breaking]")
            send(chan, '')
            break
        # Strip last seen text from buffer to avoid re-matching
        last = buf.lower()
        if 'sudo' in pat:
            send(chan, OLD_PASS, hide=True)
        elif 'current' in pat or 'old' in pat:
            send(chan, OLD_PASS, hide=True)
        elif 'username' in pat or 'user' in pat:
            send(chan, USER)
        elif 'retype' in pat or 'confirm' in pat or 'verify' in pat:
            send(chan, NEW_PASS, hide=True)
        elif 'new' in pat or 'enter new' in pat:
            send(chan, NEW_PASS, hide=True)
        elif 'updated' in pat or 'changed' in pat or 'successfully' in pat or 'token' in pat:
            print("\n[password changed]")
            break
        elif 'BAD' in pat or 'unchanged' in pat:
            print("\n[FAILED — password unchanged]")
            c.close()
            return 1
        else:
            print(f"\n[unmatched pattern hit: {pat}]")
            break

    # Drain any remaining output
    time.sleep(2)
    if chan.recv_ready():
        sys.stdout.write(chan.recv(65535).decode(errors='replace'))

    c.close()

    # Verify by reconnecting with NEW password
    print(f"\n=== Verifying — reconnect with new password ===")
    time.sleep(3)
    try:
        c2 = paramiko.SSHClient()
        c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c2.connect(HOST, username=USER, password=NEW_PASS, timeout=15,
                   allow_agent=False, look_for_keys=False)
        _, o, _ = c2.exec_command("hostname && id", timeout=10)
        print(o.read().decode())
        c2.close()
        print("=== SUCCESS: new password works ===")
        return 0
    except Exception as e:
        print(f"=== FAILED to login with new password: {e} ===")
        # Try old password to confirm state
        try:
            c3 = paramiko.SSHClient()
            c3.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c3.connect(HOST, username=USER, password=OLD_PASS, timeout=15,
                       allow_agent=False, look_for_keys=False)
            print("[old password still works — change did not take effect]")
            c3.close()
        except Exception:
            print("[old password also fails — state unknown, check ESXi console]")
        return 1

if __name__ == '__main__':
    sys.exit(main())
