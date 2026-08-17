# ORCID OAuth Setup Guide

This guide will help you set up ORCID authentication for Sieve. ORCID provides OAuth 2.0 authentication that works seamlessly on localhost for development.

## Step 1: Create a Sandbox ORCID Account (for testing)

1. Go to https://sandbox.orcid.org/register
2. Create a test account (this is separate from your real ORCID)
3. Verify your email

> **Note**: The sandbox is completely separate from production ORCID. Any test accounts or credentials created here won't affect your real ORCID record.

## Step 2: Register Your Application

1. Log in to https://sandbox.orcid.org
2. Click your name in the top right → **Developer Tools**
3. If prompted, accept the developer agreement
4. Click **Register for the free ORCID public API**

Fill in the form:
- **Name of your application**: `Sieve Curation App` (or any name you like)
- **Website URL**: `http://localhost:8501`
- **Description**: `Ontology assertion curation tool`
- **Redirect URIs**: `http://localhost:8501/`

  > **Important**: The redirect URI must include the trailing slash and match exactly!

5. Click **Save**

## Step 3: Get Your Credentials

After saving, you'll see your credentials:
- **Client ID**: Looks like `APP-XXXXXXXXXXXXXXXXX`
- **Client Secret**: Click "Show" to reveal it (looks like a UUID)

Copy both of these values.

## Step 4: Configure Sieve

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
ORCID_SANDBOX=true
ORCID_CLIENT_ID=APP-XXXXXXXXXXXXXXXXX
ORCID_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
ORCID_REDIRECT_URI=http://localhost:8501/
```

## Step 5: (Optional) Load the `.env` automatically

The app already loads `.env` on startup (`app.py` calls `load_dotenv(override=True)`), so a `.env` file in the project root is picked up with no extra setup.

Alternatively, you can export the variables in your shell instead of using a `.env` file:

```bash
export ORCID_SANDBOX=true
export ORCID_CLIENT_ID=APP-XXXXXXXXXXXXXXXXX
export ORCID_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
export ORCID_REDIRECT_URI=http://localhost:8501/
```

## Step 6: Run the App

```bash
uv run streamlit run src/sieve/app.py
```

You should see a "Login with ORCID" button in the sidebar. Click it to authenticate with your sandbox ORCID account.

## Switching to Production

When ready to use real ORCID accounts:

1. Register your app at https://orcid.org/developer-tools (same process as sandbox)
2. Update your `.env`:
   ```env
   ORCID_SANDBOX=false
   ORCID_CLIENT_ID=APP-YYYYYYYYYYYYYYYY
   ORCID_CLIENT_SECRET=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
   ```

## Troubleshooting

### "Login with ORCID" button not appearing

If you see the manual ORCID entry fields instead of the login button, the OAuth credentials are not configured. Check:
- The `.env` file exists and has correct values
- The environment variables are loaded (try `python-dotenv` or export manually)

### "Failed to authenticate with ORCID"

- Verify your Client ID and Secret are correct
- Check that the Redirect URI in your `.env` matches exactly what you registered with ORCID (including trailing slash)
- Make sure you're using sandbox credentials with `ORCID_SANDBOX=true`

### Redirect URI mismatch

ORCID is strict about redirect URIs. Ensure:
- You registered `http://localhost:8501/` (with trailing slash)
- Your `ORCID_REDIRECT_URI` env var is `http://localhost:8501/`
- You're accessing the app at `http://localhost:8501` (not `127.0.0.1`)

## Security Notes

- Never commit your `.env` file or expose your Client Secret
- The `.env` file is already in `.gitignore`
- For production, use proper secret management (environment variables, secret managers)
