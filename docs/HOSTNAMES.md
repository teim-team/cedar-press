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

### The S3 publish has never run

Measured 2026-09-20 against the workflow's own run history. The two AWS steps
arrived with #87 (run 103, 20 September 04:19). Runs 103-108 all failed earlier
in the job — 103 at `ruff check server`, the rest at the Python gates — so the
steps were skipped, not attempted. Run 109 is the first run in which they were
reached, and it failed:

```
Run aws-actions/configure-aws-credentials@v4
  role-to-assume: arn:aws:iam::502309351676:role/cedarpress-site-deploy
  aws-region: us-east-1
  audience: sts.amazonaws.com
Assuming role with OIDC          (x12, backing off over 2m06s)
##[error]Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

So `aws s3 sync` has not executed once. Whatever `cedarpress.ai` serves today was
put in the bucket by some other means, and every merge since 19 September has
changed `main` without changing the site. The GitHub Pages job is no substitute:
`public/CNAME` claims `cedarpress.ai`, but the apex now resolves to CloudFront,
so the Pages copy is published where nobody reaches it.

This is an AWS-side fix; nothing in this repository can make it pass. STS refuses
the exchange before the role's permissions are consulted, which narrows it to two
causes:

1. Account `502309351676` has no IAM OIDC identity provider for
   `token.actions.githubusercontent.com` (thumbprint aside, the provider must
   exist and list `sts.amazonaws.com` as a client ID), or
2. `cedarpress-site-deploy` does not exist, or its trust policy does not match the
   token this workflow presents.

The token a push to `main` presents carries `aud = sts.amazonaws.com` and
`sub = repo:teim-team/cedar-press:ref:refs/heads/main`. A trust policy that
accepts exactly that, and nothing wider:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::502309351676:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:teim-team/cedar-press:ref:refs/heads/main"
      }
    }
  }]
}
```

Whoever holds AWS access for `teim-prod` can confirm which of the two it is with
`aws iam list-open-id-connect-providers` and
`aws iam get-role --role-name cedarpress-site-deploy`. Until then a merge to
`main` is not a deploy, and the workflow will stay red at that step — correctly,
because publication really is failing.

## Open items

- Point `app.cedarpress.ai` at the API host, and set `vars.VITE_API_URL`, once the subscriber API is deployed.
- Fix the OIDC trust above. It blocks every publish to `cedarpress.ai`.
