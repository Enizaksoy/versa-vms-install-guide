"""
Robust SSH helper. Properly shell-quotes the sudo password so chars like
$, !, ", etc. don't break.
"""
import sys, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko, base64

def sq(s):
    """Single-quote a string for safe shell embedding (handles embedded apostrophes)."""
    return "'" + s.replace("'", "'\"'\"'") + "'"

class VmsSSH:
    def __init__(self, host, user, password, timeout=15):
        self.host = host
        self.user = user
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, username=user, password=password, timeout=timeout,
                            allow_agent=False, look_for_keys=False)

    def run(self, cmd, sudo=False, login=False, timeout=120, quiet=False, pty=False):
        """Run cmd. login=True wraps in bash -lc (sources profile.d for vsh function).
        For sudo: cmd is run as 'sudo bash -c <cmd>' with password piped in.
        pty=True allocates a pseudo-tty (needed for vsh which has internal sudo calls)."""
        if login:
            inner = f"bash -lc {sq(cmd)}"
        else:
            inner = cmd

        if sudo:
            full = f"echo {sq(self.password)} | sudo -S -p '' bash -c {sq(inner)}"
        else:
            full = inner

        if not quiet:
            print(f"$ {cmd}")
        _, o, e = self.client.exec_command(full, timeout=timeout, get_pty=pty)
        rc = o.channel.recv_exit_status()
        out = o.read().decode(errors='replace')
        err = e.read().decode(errors='replace')
        if not quiet:
            if out.strip(): print(out.rstrip())
            if err.strip() and 'password for' not in err and 'job control' not in err and 'ioctl' not in err:
                print(f"[err] {err.rstrip()}")
            print(f"[rc={rc}]\n")
        return rc, out, err

    def vsh(self, args, timeout=120, quiet=False, pty=True):
        """Run a vsh subcommand via login shell. pty=True so internal sudo gets a tty."""
        return self.run(f"vsh {args}", login=True, sudo=False, timeout=timeout, quiet=quiet, pty=pty)

    def close(self):
        self.client.close()

if __name__ == '__main__':
    # quick sanity
    HOST, USER, PASS = '192.168.30.15', 'admin', '<vms-admin-pass>'
    s = VmsSSH(HOST, USER, PASS)
    s.run("hostname")
    s.run("id", sudo=True)
    s.run("awk -F: '$1==\"versa\" {print $1, $3}' /etc/shadow", sudo=True)
    s.close()
