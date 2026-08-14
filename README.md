# studio-uptime

Off-box uptime monitor for the studio's live flagship domains. Runs on GitHub
Actions every 30 minutes (minutes :13 and :43 UTC) so an outage is detected even
when the studio workstation itself is down — the workstation's own canaries
can't report an outage they're part of.

- Probes each domain with curl (follows redirects, 20s timeout, one retry).
- Any non-200 after retry fails the run; GitHub emails the account on the
  first failure of a scheduled workflow.
- A once-a-month keepalive commit prevents GitHub's 60-day scheduled-workflow
  auto-disable on quiet repos.
- Public repo on purpose: public repos get unlimited free Actions minutes and
  the workflow contains only public URLs.

Domain list lives in `.github/workflows/uptime.yml`. `budhub.online` is
intentionally excluded while the Apparatus umbrella retirement is in progress
(its 404 is deliberate).

Maintained by the studio agents; created 2026-07-05.

MIT licensed. Built by [Nymrel](https://nymrel.com).
