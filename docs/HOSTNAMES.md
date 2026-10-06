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

`deploy.yml` — *Publish cedarpress.ai* — runs its gates, builds `dist-site/`
once, and publishes that one build to two destinations in **two independent
jobs**:

| Job | Destination | Needs |
| --- | --- | --- |
| `build` | Gates, then `dist-site/` as two artifacts | — |
| `pages` | GitHub Pages, via `deploy-pages` | `build` |
| `s3` | The bucket, then a CloudFront invalidation | `build` |

`s3` assumes IAM role `cedarpress-site-deploy` through GitHub OIDC. The role
trusts only `refs/heads/main` of this repository and can write to the bucket
and create invalidations on this distribution.

The two publishes were one job until 2026-09-21, and the coupling is what made
the OIDC failure below total rather than partial: the AWS steps ran last inside
`build`, so their failure failed `build`, and the Pages job — `needs: build` —
was skipped along with it. Eleven consecutive runs published to neither
destination and said so as a single red X on a job whose every gate had passed.
`deployGates.test.js` now fails if the two are folded back together, or if
either publish is made to wait on the other.

### Publishing by hand

The workflow is the automated path. Its S3 publish succeeded in
[run 36470140791](https://github.com/teim-team/cedar-press/actions/runs/36470140791):
the credential exchange and S3 synchronization both passed. This was checked
through GitHub on 2026-10-02; the September 21 failure below is historical.
That successful static publish does not establish an API deployment or persistent
subscriber storage. AWS access is currently paused at the owner's request.

With authorized credentials for `teim-prod`, the manual equivalent is:

```
npm ci && npm run build:site
aws s3 sync dist-site s3://cedarpress-ai-site-502309351676 --delete \
  --exclude CNAME --exclude 'assets/*' --cache-control 'public, max-age=600'
aws s3 sync dist-site/assets s3://cedarpress-ai-site-502309351676/assets --delete \
  --cache-control 'public, max-age=31536000, immutable'
aws cloudfront create-invalidation --distribution-id E3AEMUAUDGWNTQ --paths '/*'
```

**`VITE_PRESS_DEMO_ACCOUNTS` has to be in the environment for that build.** It
is a repository secret, so a local build without it is a site that signs nobody
in — the standalone preview account is how the only people outside the team who
have seen Cedar Press get through the door. Confirm afterwards against the build
stamp in Settings, which carries the commit the running bundle was built from.

### Historical OIDC failure, measured September 21

Re-measured 2026-09-21 against the workflow's own run history, through run 113.
The two AWS steps arrived with #87 (run 103, 20 September 04:19). Runs 103-108
all failed earlier in the job — 103 at `ruff check server`, the rest at the
Python gates — so the steps were skipped, not attempted. Run 109 is the first
run in which they were reached. It failed, and so has **every run since**:
109, 110, 111, 112, 113, with 113 (the #102 merge, 21 September 06:31) passing
all fourteen preceding steps — lint, 267 node tests, 143 smoke tests, ruff, 265
Python tests, `build:site`, artifact uploaded — before the same error:

```
Run aws-actions/configure-aws-credentials@v4
  role-to-assume: arn:aws:iam::502309351676:role/cedarpress-site-deploy
  aws-region: us-east-1
  audience: sts.amazonaws.com
Assuming role with OIDC          (x12, backing off over 2m06s)
##[error]Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

At that checkpoint, `aws s3 sync` had not executed. The site's bucket contents
therefore came from another publication path, and those merges had changed
`main` without updating the site through this workflow. The GitHub Pages job was no substitute:
`public/CNAME` claims `cedarpress.ai`, but the apex now resolves to CloudFront,
so the Pages copy is published where nobody reaches it — and until the job split
above, it was not even being published, because the failure below skipped it.

That failure required an AWS-side fix. STS refused the exchange before the
role's permissions were consulted, narrowing the investigation to two causes:

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

If that exact error recurs, an operator with AWS access for `teim-prod` can inspect
`aws iam list-open-id-connect-providers` and
`aws iam get-role --role-name cedarpress-site-deploy`. Use the current run's
result to establish publication; a merge alone is not deployment evidence.

## Workspace routing and API activation

The tracked source for the existing `cedarpress-router` function is
[`infrastructure/cedarpress-router.js`](../infrastructure/cedarpress-router.js).
Its prepared change keeps the `www` redirect and public prerendered pages,
preserves redirect query parameters, and serves registered app routes from the
unprerendered build shell. It does not deploy an API or alter subscriber records.

The live read on 2026-10-02 found one S3 origin, no additional cache behaviors,
and GET/HEAD only. Before changing the public login destination, verify the app
assets and existing login authority. Before enabling `VITE_API_URL`, deploy and
test the persistent Press API: stable signing secret, PostgreSQL subscribers,
exact credentialed CORS origins, and no cache for authenticated API responses.
A separate `/api/*` behavior can use the existing app hostname only with a real
API origin, method/cookie forwarding, disabled caching and one prefix removal
before FastAPI. Changing a request URI alone does not change CloudFront's origin.

Preserve the current LIVE function and distribution configuration for rollback.
Publish the tested function through the existing AWS account with a fresh ETag
after compatibility checks. Confirm apex → app sign-in, deep links, refresh,
wrong-password feedback, and unchanged existing account credentials and tiers.
A code change or static upload alone is not proof of persistent login.

## Open items

- Activate `app.cedarpress.ai` as the workspace and set `vars.VITE_API_URL` only after the persistent subscriber API and existing-account compatibility are verified.
- Verify the selected release's publish result and live build stamp when AWS work resumes. The historical OIDC failure is not a current blocker established by this review.
