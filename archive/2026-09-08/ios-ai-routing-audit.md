# iOS AI routing revision — 2026-09-08

Archived historical report. The installation/update instructions below describe
the earlier experiment; use the current root url-set-ios.conf for active iOS.

Import as a new profile:

https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios-ai-routing.conf

This profile includes the user's 13:22:40 export from September 8.
AI is select,FINLAND; FINLAND has seven candidates with ALL VPN first and
policy-select-name set to ALL VPN. The user's own update-url points to this file.
The other groups, DNS, IPv6 and external sources are retained.
Early blocks add ChatGPT routing and inline Apple/known Russian DIRECT coverage.
Russian domain-zone DIRECT rules move to the early block. The original snapshot
and the main iOS/macOS/fallback files are unchanged.
Existing remote RULE-SET sources remain external.

## Evidence from the three supplied request journals

Times below are timestamps stored in the journals.

| Export | Records | Observed routing |
| --- | ---: | --- |
| 12:40:43 | 99 | 50 global PROXY; 46 DST-PORT; 2 domain; 1 FINAL |
| 12:45:15 | 14 | 12 DST-PORT; 2 domain |
| 12:45:32 | 0 | SQLite contains no logging table |

At 12:44:29 the route changes from global PROXY with node
`🇫🇮 Финляндия` to `DST-PORT,443,FINLAND` with
`🇫🇮 ALL VPN | Финляндия`. At 12:44:38 the latter rule resolves to
`🇫🇮 Финляндия` instead. The journals cannot distinguish an automatic group
switch from a manual selection or profile change.

The broad destination-port rule handles real requests, including OpenAI,
Spotify, iCloud, and Russian services. The earlier suggestion that it was
merely a synthetic Test Rule display is contradicted by these records.
`mesu.apple.com` and `ocsp2.apple.com` also hit this port rule in the later
export rather than the supplied working profile's explicit DIRECT routes.

The exact broad rule is absent from the published working snapshot, its
currently fetched remote lists, and the locally available Git history.
The running phone configuration therefore differs from those published rules,
or has another rule source/override. These exports do not identify that source.

Observed ChatGPT hosts use port 443. The database contains URL, user-agent,
rule result, routing type and timestamp; it has no TCP/UDP discriminator,
authenticated response, actual egress IP or complete selected-node parameters.
It does not prove a missing Cloudflare port, a Russian egress, or the cause
of the regional response.

## Changes and limits

- Apple/iCloud and known Russian service domains are inline DIRECT before remote
  lists; Russian suffix rules move here as well. Non-Russian domain zones used by
  known Russian services are copied from the existing Russian domain list.
  This preserves the requested distinction: AI and Spotify use their Finnish
  pools while iCloud and Russian services use DIRECT.
- Inline OpenAI/ChatGPT domain routes precede remote lists and GEOIP, so core
  routing does not depend on downloading the AI RULE-SET.
- Auxiliary destinations are mapped to the same AI group using the
  [OpenAI network guidance](https://help.openai.com/en/articles/9247338),
  plus the Sentry US endpoint seen in earlier user logs and the ChatGPT LiveKit
  namespace. Shared providers use exact hosts where possible.
- Apple device verification, including humb.apple.com, retains the existing
  Apple/system route. This is not a promise that every OpenAI-related request
  uses FINLAND. Other Voice IP destinations are not inferred from port numbers.
- Four domain-scoped UDP/443 reject rules request a TCP fallback for core
  ChatGPT/OpenAI/static/file domains. This is a diagnostic restriction;
  these journals do not establish QUIC as the cause of regional errors.
  See [Cloudflare HTTP/3 troubleshooting](https://developers.cloudflare.com/ssl/troubleshooting/err-ssl-protocol-error/).
- There is no universal DST-PORT rule. HTTPS for other services retains its
  original routing, including Russian DIRECT.
- FINLAND uses the user's seven-candidate automatic pool. Its latency probe
  measures gstatic reachability, not OpenAI regional acceptance. A node label
  does not establish its egress IP, and the profile cannot change a provider's
  server-side egress.

## Device verification

Import the new URL as a separate profile, activate it, select global routing
Config, reconnect VPN and restart ChatGPT. Test a message immediately and
again after a pause. In the request log, core ChatGPT and OpenAI hosts should
match an inline DOMAIN-SUFFIX rule with policy AI and the selected FINLAND node.
The scoped QUIC guards may appear as REJECT-NO-DROP before TCP succeeds.

If the log still shows `DST-PORT,443,FINLAND`, another profile, local rule
or override remains active; updating this remote file cannot remove it.
If AI selects the expected node but regional errors persist, record that
request's displayed IP and selected node before changing settings again.

Static validation verifies scope and rule declarations, not the Shadowrocket
engine or successful authenticated ChatGPT sessions. GitHub Actions stay
manually disabled.
