# iOS Apple Watch local-route A/B test

`url-set-ios-watch-apple-bypass-test.conf` is a temporary diagnostic profile. It is copied from the current iOS profile and keeps its proxy groups and rules unchanged.

The canary changes only two local-network inputs:

- Apple and iCloud hostnames are added to `skip-proxy`, so Shadowrocket does not apply proxy processing to those hostnames.
- IPv6 loopback and link-local traffic are excluded from the tunnel. IPv6 mDNS (`ff02::fb/128`) is retained.

The broad `fc00::/7` exclusion is intentionally not added: the VPN MIR screenshot shows a ULA address on that app's own tunnel, so excluding the whole ULA range in Shadowrocket could bypass or disrupt private VPN routes without proving that it is the Apple Watch path.

The profile has no `update-url`, so a refresh of the primary profile cannot overwrite the A/B test while it is being checked.

Raw URL:

`https://raw.githubusercontent.com/squazaryu/sr-config/main/archive/2026-09-11/url-set-ios-watch-apple-bypass-test.conf`

Suggested check: import this URL, connect Shadowrocket, fully reconnect the VPN, then test Watch weather and update discovery with VPN on. Repeat the same actions with VPN off and compare. If this changes the symptom, the likely fault is local iPhone-to-Watch/TUN handling rather than the remote Finnish node; it is still an A/B signal, not a final root-cause proof.
