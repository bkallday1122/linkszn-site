# LINKSZN

Astro static deals site for https://linkszn.com. Contact: linkszn@fastmail.com.

## Development

```sh
npm ci
npm run dev -- --host 127.0.0.1
npm run build
python3 -m unittest discover -s tests
```

## Cloudflare Pages

Connect this repository with production branch `main`, build command `npm run build`, output directory `dist`, and Node.js 22. Configure both `linkszn.com` and `www.linkszn.com` as custom domains. Do not use the GitHub Pages A records with Cloudflare Pages. Copy existing DNS records before changing nameservers, including mail and verification records.

Hosting/domain setup is not yet complete. The CNAME file records the intended domain; it does not configure DNS or certificates by itself.

## Publish a verified deal

Use an isolated clean checkout on `main`. Authenticate Git with a fine-grained personal access token limited to this repository, with Contents read/write and Metadata read. Never put a token in a remote URL, JSON file, command argument, or repository. Credential provisioning is not yet complete.

```sh
python3 publish_deal.py /absolute/path/to/deal.json --dry-run
python3 publish_deal.py /absolute/path/to/deal.json
```

The script validates input, takes a local lock, pulls main with fast-forward only, writes one file in `deals/`, commits only that file, and pushes. A successful push queues the hosting build; it does not prove deployment is live. Check the Cloudflare deployment and public URL. If a push fails after committing, rerun the same input after resolving connectivity; identical content is safe to retry. Concurrent remote updates may require a normal Git rebase before retrying.

Required fields: `title`, `woot_url`, `image`, `price`, `comparisons`, `pct_below`, `posted_at`, `checked_at`, `writeup`. Each comparison needs `store`, `price`, `url`, `checked_at`, `notes`, `available: true`, and `matching: true`. Use timezone-aware ISO timestamps and numeric USD prices. Optional fields: `category`, `condition`, `notes`, `expires_at`. Existing deals illustrate the format.

`pct_below` is the whole percentage rounded down against the **lowest** qualifying comparison. All checks must be within 24 hours. A publisher's assertions cannot replace actually checking matching model, variant, pack size, condition and availability. Compare current sale prices, account for advertised promotions, and disclose shipping and warranty differences. Do not use inflated MSRP as market price. The publisher rejects savings below 40%.

Supply `expires_at` whenever an offer has a scheduled end. The browser changes its badge and buy label after this timestamp; the detail page also shows the scheduled end without JavaScript. Stock can run out sooner. Review and update expired or changed offers; no automated stock checker is configured in this repository.

The external Woot alert process can call this script after its own verification passes. No existing alert service has been connected yet. Regular product URLs are used until affiliate approvals and tracking identifiers are available.

## Review readiness

About, Contact, Affiliate Disclosure, Privacy, Terms, sitemap and robots are included. Affiliate approval remains a decision of each program. Current seed content is incomplete: three verified offers, with a target of 10–15. Do not submit the unfinished site as fully launched.
