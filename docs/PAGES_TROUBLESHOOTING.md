# GitHub Pages Troubleshooting

## Error: "Get Pages site failed" / HttpError: Not Found

This error occurs when `actions/configure-pages@v4` cannot find or access the Pages configuration.

### Common Causes

| Cause | Fix Location |
|-------|--------------|
| Pages not enabled | GitHub UI |
| Source not set to "GitHub Actions" | GitHub UI |
| Org policy blocks Pages | Org admin |
| Missing workflow permissions | Workflow YAML |
| Private repo without Pro/Team | Upgrade plan |

### Fix #1: Enable Pages in Repository Settings

1. Go to **Settings** → **Pages**
2. Under "Build and deployment":
   - **Source**: Select **"GitHub Actions"**
3. Click **Save**
4. Re-run the workflow

### Fix #2: Check Workflow Permissions

Ensure your workflow has these permissions:

```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

### Fix #3: Check Organization Policy

If this is an organization repository:

1. Go to **Organization Settings** → **Actions** → **General**
2. Ensure "Allow GitHub Actions to create and approve pull requests" is enabled
3. Go to **Organization Settings** → **Pages**
4. Ensure Pages is allowed for this repository

### Fix #4: Use `enablement: true`

The workflow can attempt to enable Pages automatically:

```yaml
- name: Setup Pages
  uses: actions/configure-pages@v4
  with:
    enablement: true
```

**Note**: This may fail if blocked by org policy.

### Fix #5: Private Repository Limitations

GitHub Pages for private repos requires:
- GitHub Pro, Team, or Enterprise plan
- Or make the repository public

## Required Settings Checklist

- [ ] Repository Settings → Pages → Source = "GitHub Actions"
- [ ] Workflow has `pages: write` permission
- [ ] Workflow has `id-token: write` permission
- [ ] `github-pages` environment exists (auto-created on first deploy)
- [ ] (Org repos) Organization allows Pages for this repo

## Workflow Permissions Explained

| Permission | Purpose |
|------------|---------|
| `contents: read` | Checkout repository code |
| `pages: write` | Deploy to GitHub Pages |
| `id-token: write` | OIDC token for Pages deployment |

## Debugging Steps

1. **Check Actions tab**: Look for the failing workflow run
2. **Expand "Setup Pages" step**: See the actual error message
3. **Verify Settings → Pages**: Ensure source is "GitHub Actions"
4. **Check environment**: Settings → Environments → `github-pages` should exist

## After Fixing

1. Go to **Actions** tab
2. Select the failed workflow
3. Click **Re-run all jobs**

Or trigger manually:

```bash
gh workflow run pages.yml
```

## Successful Deployment

After successful deployment:
- URL: `https://<username>.github.io/<repo>/`
- Check Settings → Pages for the live URL
