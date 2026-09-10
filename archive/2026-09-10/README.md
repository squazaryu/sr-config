# iOS hybrid A/B test

`url-set-ios-hybrid-test.conf` combines the General section from the user-provided
`Russia DIRECT` profile with the current iOS `[Proxy Group]` and `[Rule]`
sections from `url-set-ios.conf` at commit `b83a987`.

Purpose: isolate whether the practical difference comes from DNS, IPv6,
DNS hijacking, or other General settings while retaining our current service
and group routing. It is a test profile and does not replace the main iOS
configuration. It has no `update-url` and contains no proxy credentials.

Raw URL:

https://raw.githubusercontent.com/squazaryu/sr-config/main/archive/2026-09-10/url-set-ios-hybrid-test.conf

The test keeps our AI group and Finnish candidates. It does not prove the
provider's egress country; use Cloudflare trace or a route log for that.
