# Hostnames and TLS

| Host | Serves |
| --- | --- |
| `cedarpress.ai` | The static client: the door, the tribal data request policy and research access, plus the gated app. |
| `app.cedarpress.ai` | 301 to the same path on `cedarpress.ai` until the subscriber API has a host. |
| `www.cedarpress.ai` | 301 to the same path on `cedarpress.ai`. |

## AWS (account `teim-prod`, us-east-1)

- **Certificate**: ACM `4ed65c4b-c538-42fe-ac20-b4f6b87417ee`, covers `cedarpress.ai`, `app.cedarpress.ai` and `www.cedarpress.ai`, DNS-validated. The earlier two-name certificate `4fb7a4d8-…` is unused. Renews itself while the validation CNAMEs stay in the zone.
- **CloudFront**: distribution `E3AEMUAUDGWNTQ` (`dmcyj50itww17.cloudfront.net`), all three hosts as aliases, HTTP redirects to HTTPS, unknown paths return `404.html` with a 404.
- **Origin**: private S3 bucket `cedarpress-ai-site-502309351676`, read through an origin access control.
- **Viewer-request function** `cedarpress-router`: redirects `app.` and `www.` to the apex and maps `/path` to `/path/index.html`, which is how the prerendered public pages resolve.
- **DNS**: Route 53 hosted zone `Z07251432LVISIVE32FRN`. A and AAAA aliases for the apex, `app` and `www`, the ACM validation CNAMEs, and `_dmarc`.
- **Registrar**: GoDaddy, nameservers set to the four Route 53 servers in the zone.

## Publishing

`deploy.yml` builds, then syncs `dist-site/` to the bucket and invalidates the distribution, assuming IAM role `cedarpress-site-deploy` through GitHub OIDC. The role trusts only `refs/heads/main` of this repository and can write to the bucket and create invalidations on this distribution. GitHub Pages still receives the same artifact.

## Open items

- Point `app.cedarpress.ai` at the API host, and set `vars.VITE_API_URL`, once the subscriber API is deployed.
