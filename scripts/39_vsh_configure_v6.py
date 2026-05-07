"""
vsh configure runner v4 — fixes:
  - REMOVED stall-based abort (caused premature exit + SIGHUP killed vsh)
  - Only exits on: shell prompt return, Operation Aborted, or DEADLINE
  - Uses paramiko transport keepalive to keep TCP alive during long quiet phases
  - All v3 rules retained
"""
import sys, os, time, re, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'

ANSWERS = {
    'mgmt_ip':       '192.168.30.15',
    'fqdn':          'vms-1.mylab.com',
    'elastic_fqdn':  'vms-1-elastic.mylab.com',
    'elastic_ip':    '192.168.30.16',
    'vos_ip':        '192.168.20.15',
    'node_name':     'vms-1.mylab.com',
    'keystore_pass': '<keystore-pass>',
    'san1':          'vms-1-elastic.mylab.com',
    'san2':          'vms-vos.mylab.com',
    'director_pri':  '192.168.10.51',
    'director_sec':  '0.0.0.0',
}

RULES = [
    (r'continue to change shell password\s*\?\s*\(y/N\)\s*:',                    'N',                          False),
    (r'change the shell login system password\s*\(y/N\)\s*:',                    'N',                          False),
    (r're-install the node\s*\?\s*\(y/N\)\s*:',                                  'N',                          False),
    (r'primary interface configuration finalized\?\s*\(y/N\)\s*:',               'Y',                          False),
    (r'hostname of this VMS server finalized\?\s*\(y/N\)\s*:',                   'Y',                          False),
    (r'1st Control Plane Node of the cluster\s*\?\s*\(y/N\)\s*:',                'Y',                          False),
    (r'additional Control Plane Node being added to the cluster\s*\?\s*\(y/N\)', 'N',                          False),
    (r'entries for Subject Alt-Names finalized\?',                               'Y',                          False),
    (r'Do you want to continue with .* as the entry\s*\?\s*\(y/N\)',             'Y',                          False),
    (r'Do you want to (re)?ge(ne)?rate the certificates with .*FQDN.*\(y/N\)',   'Y',                          False),
    (r'change the existing configuration\s*\?\s*\(y/N\)',                        'Y',                          False),
    (r'Elastic IP of this VMS Cluster finalized\?\s*\(y/N\)',                    'Y',                          False),
    (r'Please Enter this VMS Server Management/Primary Interface IP Address',    ANSWERS['mgmt_ip'],           False),
    (r'Please enter the Hostname of this VMS Server',                            ANSWERS['fqdn'],              False),
    (r'Please Enter FQDN used in Versa Message Service',                         ANSWERS['fqdn'],              False),
    (r'Please Enter Subject ALT Name 1 used in Versa Message Service',           ANSWERS['san1'],              False),
    (r'Please Enter Subject ALT Name 2 used in Versa Message Service',           ANSWERS['san2'],              False),
    (r"Please Enter Primary Versa Director.*IP Address",                          ANSWERS['director_pri'],      False),
    (r"Please Enter Secondary Versa Director.*IP Address",                        ANSWERS['director_sec'],      False),
    (r'Please Enter a unique name for this VMS node',                            ANSWERS['node_name'],         False),
    (r'IP Address for this VMS Cluster where VOS/ADC will connect',              ANSWERS['vos_ip'],            False),
    (r'Please Enter FQDN used as Entry for applications',                        ANSWERS['elastic_fqdn'],      False),
    (r'Please enter the Elastic IP of this VMS Server',                          ANSWERS['elastic_ip'],        False),
    (r'Please enter username\s*:',                                                'admin',                      False),
    (r'Enter Password for Application Certificate',                              ANSWERS['keystore_pass'],     True),
    (r'RE-?Enter Password for Application Certificate',                          ANSWERS['keystore_pass'],     True),
]

def find_match(buf_slice):
    for pat, response, hide in RULES:
        m = re.search(pat, buf_slice, re.IGNORECASE | re.MULTILINE)
        if m:
            return pat, response, hide, m
    return None, None, None, None

def main():
    s = VmsSSH(HOST, USER, PASSWORD)
    # Keepalive every 15s to prevent TCP timeout during quiet phases
    s.client.get_transport().set_keepalive(15)
    chan = s.client.invoke_shell(term='xterm', width=200, height=50)
    chan.settimeout(2.0)

    log_dir = r'C:\Claude\vms_install\logs'
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(log_dir, f'configure_v6_{ts}.log')
    log = open(log_path, 'w', encoding='utf-8')
    print(f"=== Logging to {log_path} ===\n")

    def emit(text):
        sys.stdout.write(text); sys.stdout.flush()
        log.write(text); log.flush()

    time.sleep(2)
    while chan.recv_ready():
        d = chan.recv(65535).decode(errors='replace')
        emit(d)

    emit("\n[CMD] vsh configure\n")
    chan.send('vsh configure\n')

    buf = ''
    search_pos = 0
    last_data = time.time()
    DEADLINE = time.time() + 60 * 90  # 90 min cap (was 75)
    last_keepalive = time.time()

    while time.time() < DEADLINE:
        if chan.recv_ready():
            d = chan.recv(65535).decode(errors='replace')
            buf += d
            emit(d)
            last_data = time.time()
        else:
            time.sleep(0.5)
            # periodic keepalive ping (but not too often)
            if time.time() - last_keepalive > 30:
                # write a no-op character to keep tty alive? No, just rely on TCP keepalive
                last_keepalive = time.time()

        if time.time() - last_data < 0.6:
            continue

        slice_to_search = buf[search_pos:]
        if not slice_to_search.strip():
            continue

        pat, response, hide, m = find_match(slice_to_search)
        if pat:
            time.sleep(0.3)
            while chan.recv_ready():
                d2 = chan.recv(65535).decode(errors='replace')
                buf += d2
                emit(d2)
            disp = '*' * len(response) if hide else response
            emit(f"\n[ANSWER: ({pat[:60]}) → {disp!r}]\n")
            chan.send(response + '\n')
            search_pos = search_pos + m.end()
            last_data = time.time()
            continue

        # Terminal state detection — ONLY break on real signals, NOT stall:
        tail = buf[-400:]
        # 1) Shell prompt return = vsh exited cleanly
        if re.search(r'\[admin@vms-1[^]]*\]\s*\$\s*$', tail.strip()):
            # confirm by waiting briefly to see if more arrives
            time.sleep(2)
            extra = ''
            while chan.recv_ready():
                extra += chan.recv(65535).decode(errors='replace')
            if extra.strip():
                buf += extra
                emit(extra)
                last_data = time.time()
                continue
            emit("\n[DONE — back at shell prompt]\n")
            break
        # 2) Explicit failure
        if re.search(r'Operation Aborted', tail):
            emit("\n[ERROR — Operation Aborted]\n")
            break
        # 3) Final completion signals
        if re.search(r'(Configuration is complete|configure.*successful|All services Running)', tail, re.I):
            time.sleep(5)
            while chan.recv_ready():
                d = chan.recv(65535).decode(errors='replace')
                buf += d
                emit(d)
            emit("\n[DONE — completion marker hit]\n")
            break

    # Final vsh status
    emit("\n[CMD] vsh status\n")
    chan.send('vsh status\n')
    end = time.time() + 90
    while time.time() < end:
        if chan.recv_ready():
            d = chan.recv(65535).decode(errors='replace')
            emit(d)
        else:
            time.sleep(0.5)

    chan.close()
    s.close()
    log.close()
    print(f"\n[Done. Log: {log_path}]")

if __name__ == '__main__':
    main()
