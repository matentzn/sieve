"""The Streamlit app module imports cleanly (no old-model references)."""


def test_app_imports():
    import sieve.app as app

    assert hasattr(app, "main")
    assert hasattr(app, "render_packet_detail")
