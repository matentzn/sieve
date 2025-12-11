"""ORCID OAuth authentication for Sieve."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx
import streamlit as st
import yaml

# ORCID OAuth endpoints
ORCID_SANDBOX_AUTH_URL = "https://sandbox.orcid.org/oauth/authorize"
ORCID_SANDBOX_TOKEN_URL = "https://sandbox.orcid.org/oauth/token"
ORCID_SANDBOX_API_URL = "https://api.sandbox.orcid.org/v3.0"

ORCID_PROD_AUTH_URL = "https://orcid.org/oauth/authorize"
ORCID_PROD_TOKEN_URL = "https://orcid.org/oauth/token"
ORCID_PROD_API_URL = "https://api.orcid.org/v3.0"


@dataclass
class OrcidUser:
    """Authenticated ORCID user."""

    orcid: str
    name: Optional[str] = None
    access_token: Optional[str] = None


@dataclass
class AuthorizedCurator:
    """An authorized curator from the curators.yaml file."""

    orcid: str
    name: Optional[str] = None
    role: str = "curator"  # "admin" or "curator"


# Default path for curators file
CURATORS_FILE_PATH = os.getenv("CURATORS_FILE", "curators.yaml")


@st.cache_data(ttl=60)
def load_authorized_curators() -> dict[str, AuthorizedCurator]:
    """Load authorized curators from curators.yaml file.

    Returns a dict mapping ORCID to AuthorizedCurator.
    Cached for 60 seconds to allow hot-reloading of the file.
    """
    curators_path = Path(CURATORS_FILE_PATH)

    if not curators_path.exists():
        return {}

    with open(curators_path) as f:
        data = yaml.safe_load(f)

    if not data or "curators" not in data:
        return {}

    result = {}
    for curator_data in data["curators"]:
        orcid = curator_data.get("orcid", "").strip()
        if orcid:
            # Normalize ORCID (remove prefix if present)
            if orcid.startswith("orcid:"):
                orcid = orcid[6:]
            result[orcid] = AuthorizedCurator(
                orcid=orcid,
                name=curator_data.get("name"),
                role=curator_data.get("role", "curator"),
            )

    return result


def is_authorized_curator(orcid: Optional[str]) -> bool:
    """Check if the given ORCID is an authorized curator.

    Args:
        orcid: ORCID iD (with or without "orcid:" prefix)

    Returns:
        True if authorized, False otherwise
    """
    if not orcid:
        return False

    # Normalize ORCID
    if orcid.startswith("orcid:"):
        orcid = orcid[6:]

    curators = load_authorized_curators()
    return orcid in curators


def get_curator_role(orcid: Optional[str]) -> Optional[str]:
    """Get the role of an authorized curator.

    Args:
        orcid: ORCID iD (with or without "orcid:" prefix)

    Returns:
        Role string ("admin" or "curator") if authorized, None otherwise
    """
    if not orcid:
        return None

    # Normalize ORCID
    if orcid.startswith("orcid:"):
        orcid = orcid[6:]

    curators = load_authorized_curators()
    if orcid in curators:
        return curators[orcid].role

    return None


def is_admin(orcid: Optional[str]) -> bool:
    """Check if the given ORCID has admin role."""
    return get_curator_role(orcid) == "admin"


def get_orcid_config() -> dict:
    """Get ORCID OAuth configuration from environment variables."""
    use_sandbox = os.getenv("ORCID_SANDBOX", "true").lower() == "true"

    if use_sandbox:
        auth_url = ORCID_SANDBOX_AUTH_URL
        token_url = ORCID_SANDBOX_TOKEN_URL
        api_url = ORCID_SANDBOX_API_URL
    else:
        auth_url = ORCID_PROD_AUTH_URL
        token_url = ORCID_PROD_TOKEN_URL
        api_url = ORCID_PROD_API_URL

    return {
        "client_id": os.getenv("ORCID_CLIENT_ID", ""),
        "client_secret": os.getenv("ORCID_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("ORCID_REDIRECT_URI", "http://localhost:8501/"),
        "auth_url": auth_url,
        "token_url": token_url,
        "api_url": api_url,
        "use_sandbox": use_sandbox,
    }


def is_orcid_configured() -> bool:
    """Check if ORCID OAuth is properly configured."""
    config = get_orcid_config()
    return bool(config["client_id"] and config["client_secret"])


def get_authorization_url() -> str:
    """Generate the ORCID authorization URL."""
    config = get_orcid_config()

    params = {
        "client_id": config["client_id"],
        "response_type": "code",
        "scope": "/authenticate",
        "redirect_uri": config["redirect_uri"],
    }

    return f"{config['auth_url']}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> Optional[OrcidUser]:
    """Exchange authorization code for access token and user info."""
    config = get_orcid_config()

    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config["redirect_uri"],
    }

    headers = {"Accept": "application/json"}

    try:
        with httpx.Client() as client:
            response = client.post(
                config["token_url"],
                data=data,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            token_data = response.json()

            # ORCID returns the ORCID iD and name in the token response
            orcid = token_data.get("orcid")
            name = token_data.get("name")
            access_token = token_data.get("access_token")

            if orcid:
                return OrcidUser(
                    orcid=orcid,
                    name=name,
                    access_token=access_token,
                )
    except httpx.HTTPError as e:
        st.error(f"Failed to authenticate with ORCID: {e}")

    return None


def get_current_user() -> Optional[OrcidUser]:
    """Get the currently logged in user from session state."""
    if "orcid_user" in st.session_state:
        return st.session_state.orcid_user
    return None


def set_current_user(user: OrcidUser):
    """Set the current user in session state."""
    st.session_state.orcid_user = user


def logout():
    """Log out the current user."""
    if "orcid_user" in st.session_state:
        del st.session_state.orcid_user


def handle_oauth_callback():
    """Handle OAuth callback and exchange code for token.

    Returns True if authentication was successful, False otherwise.
    """
    query_params = st.query_params

    if "code" in query_params:
        code = query_params["code"]
        user = exchange_code_for_token(code)

        if user:
            set_current_user(user)
            # Clear the code from URL
            st.query_params.clear()
            return True
        else:
            st.error("Failed to authenticate with ORCID")
            st.query_params.clear()

    return False


def render_login_ui():
    """Render the ORCID login/logout UI in the sidebar."""
    user = get_current_user()

    if user:
        # User is logged in
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Logged in as")
        if user.name:
            st.sidebar.markdown(f"**{user.name}**")
        st.sidebar.markdown(f"[{user.orcid}](https://orcid.org/{user.orcid})")

        # Show authorization status
        role = get_curator_role(user.orcid)
        if role:
            role_badge = "Admin" if role == "admin" else "Curator"
            st.sidebar.success(f"Authorized: {role_badge}")
        else:
            st.sidebar.warning("Read-only (not authorized)")

        if st.sidebar.button("Logout", use_container_width=True):
            logout()
            st.rerun()
    else:
        # User is not logged in
        st.sidebar.markdown("---")

        if is_orcid_configured():
            auth_url = get_authorization_url()
            # Official ORCID sign-in button
            st.sidebar.markdown(
                f'''
                <a href="{auth_url}" style="text-decoration: none;">
                    <img src="https://orcid.org/assets/vectors/orcid.logo.icon.svg"
                         alt="ORCID iD"
                         style="width: 24px; height: 24px; vertical-align: middle; margin-right: 8px;">
                    <span style="
                        display: inline-block;
                        background-color: #a6ce39;
                        color: white;
                        padding: 8px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 14px;
                        vertical-align: middle;
                    ">Sign in with ORCID</span>
                </a>
                ''',
                unsafe_allow_html=True,
            )
        else:
            # Fallback to manual ORCID entry if OAuth not configured
            st.sidebar.markdown("### Curator Info")
            st.sidebar.caption("*ORCID OAuth not configured*")

            curator_orcid = st.sidebar.text_input(
                "Your ORCID",
                value=st.session_state.get("curator_orcid", ""),
                placeholder="0000-0000-0000-0000",
            )
            curator_name = st.sidebar.text_input(
                "Your Name",
                value=st.session_state.get("curator_name", ""),
                placeholder="Dr. Jane Smith",
            )
            st.session_state["curator_orcid"] = curator_orcid
            st.session_state["curator_name"] = curator_name


def get_curator_info() -> tuple[Optional[str], Optional[str]]:
    """Get curator ORCID and name (from OAuth or manual entry).

    Returns:
        Tuple of (orcid, name)
    """
    user = get_current_user()

    if user:
        return f"orcid:{user.orcid}", user.name

    # Fallback to manual entry
    orcid = st.session_state.get("curator_orcid", "")
    name = st.session_state.get("curator_name", "")

    if orcid:
        # Ensure ORCID has prefix
        if not orcid.startswith("orcid:"):
            orcid = f"orcid:{orcid}"
        return orcid, name if name else None

    return None, None
