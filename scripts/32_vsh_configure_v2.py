"""
vsh configure runner v2 — fixes:
  - Buffer position pointer (only match prompts after last answer)
  - Added 'primary interface finalized?' rule => Y
  - Added more rules captured from initial probe
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
}

# Order: most specific first
RULES = [
    # already-known prompts from probe
    (r'continue to change shell password.*\(y/N\)\s*:',                                'N',                          False),
    (r'primary interface configuration finalized\?\s*\(y/N\)\s*:',                     'Y',                          False),
    (r'Subject Alt-Names finalized\?.*\[?y/N\]?\s*:',                                  'Y',                          False),

    # Disk warning prompt (continue?)
    (r'rotational disk.*continue.*\(y/N\)|continue with rotational',                   'y',                          False),

    # First Control Plane Node
    (r'First Control Plane Node.*\(Y/n\)|First Control Plane.*\[Y/n\]',                 'Y',                          False),

    # Confirm FQDN entered
    (r'Continue.*FQDN.*\[Y/n\]|FQDN.*confirm.*\[Y/n\]|continue with this FQDN',         'Y',                          False),
    # Generate cert prompt
    (r'Generate.*cert.*FQDN.*\[Y/n\]|Generate certificate.*\[Y/n\]',                    'Y',                          False),
    # Use existing imported certs
    (r'(Use|use existing).*(cert|imported).*\[Y/n\]|certs.*present.*\[Y/n\]',           'Y',                          False),

    # FQDN/hostname (must come AFTER more specific Y/n confirmations)
    (r'Please Enter (the )?FQDN used in (Versa Message|VMS Server|VMS).*:',             ANSWERS['fqdn'],              False),
    (r'(Enter\s+)?VMS Server FQDN.*:',                                                  ANSWERS['fqdn'],              False),
    (r'(Enter\s+)?Hostname.*:',                                                          ANSWERS['fqdn'],              False),

    # Management Interface IP
    (r'(Management|Northbound) Interface IP.*:',                                         ANSWERS['mgmt_ip'],           False),
    (r'(Management|Northbound).*IP\s*[Aa]ddress.*:',                                     ANSWERS['mgmt_ip'],           False),

    # Subject ALT names
    (r'Subject ALT Name 1.*:|Alt[- ]?Name 1.*:|First.*SAN.*:',                           ANSWERS['san1'],              False),
    (r'Subject ALT Name 2.*:|Alt[- ]?Name 2.*:|Second.*SAN.*:',                          ANSWERS['san2'],              False),

    # Node name
    (r'(Unique )?[Nn]ode\s*[Nn]ame.*:',                                                  ANSWERS['node_name'],         False),

    # Keystore / private key password (asked twice usually)
    (r'(Enter\s+)?Password for Application Certificate\s*:',                             ANSWERS['keystore_pass'],     True),
    (r'RE-?Enter Password for Application Certificate\s*:',                               ANSWERS['keystore_pass'],     True),
    (r'[Cc]ertificate.*[Kk]eystore.*[Pp]assword.*:',                                      ANSWERS['keystore_pass'],     True),
    (r'[Pp]rivate.*[Kk]ey.*[Pp]assword.*:',                                               ANSWERS['keystore_pass'],     True),

    # VOS/ADC connection IP
    (r'(VOS|ADC|Southbound).*IP\s*[Aa]ddress.*:|connection IP.*:',                       ANSWERS['vos_ip'],            False),

    # Elastic
    (r'[Ee]lastic.*FQDN.*:',                                                              ANSWERS['elastic_fqdn'],      False),
    (r'[Ee]lastic.*IP.*:',                                                                ANSWERS['elastic_ip'],        False),

    # Generic confirmation Y/N — ONLY at end as safety net (commented out — risky)
]

def find_match(buf_slice):
    for pat, response, hide in RULES:
        m = re.search(pat, buf_slice, re.IGNORECASE | re.MULTILINE)
        if m:
            return pat, response, hide, m
    return None, None, None, None

def main():
    s = VmsSSH(HOST, USER, PASSWORD)
    chan = s.client.invoke_shell(term='xterm', width=200, height=50)
    chan.settimeout(2.0)

    log_dir = r'C:\Claude\vms_install\logs'
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(log_dir, f'configure_v2_{ts}.log')
    log = open(log_path, 'w', encoding='utf-8')
    print(f"=== Logging full transcript to {log_path} ===\n")

    def emit(text):
        sys.stdout.write(text)
        sys.stdout.flush()
        log.write(text)
        log.flush()

    # consume initial banner
    time.sleep(2)
    while chan.recv_ready():
        d = chan.recv(65535).decode(errors='replace')
        emit(d)

    emit("\n[CMD] vsh configure\n")
    chan.send('vsh configure\n')

    buf = ''
    search_pos = 0  # only search beyond this position
    last_data = time.time()
    DEADLINE = time.time() + 60 * 75  # 75 min cap
    no_data_break = 600

    while time.time() < DEADLINE:
        if chan.recv_ready():
            d = chan.recv(65535).decode(errors='replace')
            buf += d
            emit(d)
            last_data = time.time()
        else:
            time.sleep(0.4)

        # Only look at content AFTER search_pos
        slice_to_search = buf[search_pos:]
        if not slice_to_search.strip():
            continue

        # Try to match a prompt in the new content
        # Wait briefly for prompt to settle (no data for 0.6s)
        if time.time() - last_data < 0.6:
            continue

        pat, response, hide, m = find_match(slice_to_search)
        if pat:
            # Drain a tiny bit more in case more chars are coming
            time.sleep(0.3)
            while chan.recv_ready():
                d2 = chan.recv(65535).decode(errors='replace')
                buf += d2
                emit(d2)

            # Send response
            disp = '*' * len(response) if hide else response
            emit(f"\n[ANSWER: ({pat[:50]}) → {disp!r}]\n")
            chan.send(response + '\n')
            # Advance search position past the match (use match end relative to slice)
            search_pos = search_pos + m.end()
            last_data = time.time()
            continue

        # Detect long stalls and shell prompt return (= done or aborted)
        if time.time() - last_data > 30:
            tail = buf[-300:]
            if re.search(r'\[admin@vms-1.*\]\s*\$\s*$', tail.strip()):
                emit("\n[DONE — back at shell prompt]\n")
                break
            if re.search(r'Operation Aborted|aborted', tail, re.I):
                emit("\n[ERROR — Operation Aborted detected]\n")
                break
        if time.time() - last_data > no_data_break:
            emit(f"\n[STALL >{no_data_break}s — aborting]\n")
            break

    # vsh status as final check
    emit("\n[CMD] vsh status\n")
    chan.send('vsh status\n')
    end = time.time() + 60
    while time.time() < end:
        if chan.recv_ready():
            d = chan.recv(65535).decode(errors='replace')
            emit(d)
        else:
            time.sleep(0.5)

    chan.close()
    s.close()
    log.close()
    print(f"\n[Done. Log saved at {log_path}]")

if __name__ == '__main__':
    main()
