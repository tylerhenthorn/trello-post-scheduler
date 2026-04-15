"""
Integration test for the Bluesky AspectRatio model path.

The original bug used models.AppBskyEmbedImages.AspectRatio, which does not
exist in the atproto SDK. The correct class is models.AppBskyEmbedDefs.AspectRatio.

This test loads the *real* atproto model classes directly from their source
files (bypassing atproto_client/__init__.py and its broken crypto chain) so
that any future regression to the wrong attribute path causes an immediate
failure here rather than at runtime.
"""

import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock


def _find_atproto_client_root() -> Path:
    """Locate the atproto_client package directory on disk."""
    for path in sys.path:
        candidate = Path(path) / "atproto_client"
        if (candidate / "exceptions.py").exists():
            return candidate
    raise RuntimeError("atproto_client package not found on sys.path")


def _load_from_file(dotted_name: str, file_path: Path, module_store: dict):
    """Load a module directly from its file, adding it to module_store."""
    spec = importlib.util.spec_from_file_location(dotted_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    module_store[dotted_name] = mod
    spec.loader.exec_module(mod)
    return mod


@contextmanager
def _real_embed_modules():
    """
    Context manager that temporarily installs the real atproto embed model
    modules into sys.modules, then restores the previous state on exit.

    This works around atproto_client/__init__.py pulling in the broken
    cryptography native extension, by loading only the model files we need.
    """
    root = _find_atproto_client_root()

    names_to_patch = [
        "atproto_client",
        "atproto_client.exceptions",
        "atproto_client.models",
        "atproto_client.models.base",
        "atproto_client.models.blob_ref",
        "atproto_client.models.string_formats",
        "atproto_client.models.app",
        "atproto_client.models.app.bsky",
        "atproto_client.models.app.bsky.embed",
        "atproto_client.models.app.bsky.embed.defs",
        "atproto_client.models.app.bsky.embed.images",
    ]
    saved = {n: sys.modules.get(n) for n in names_to_patch}

    real: dict[str, types.ModuleType] = {}

    # 1. Bare package stubs for the hierarchy (no __init__ executed)
    for pkg_name in [
        "atproto_client",
        "atproto_client.models",
        "atproto_client.models.app",
        "atproto_client.models.app.bsky",
        "atproto_client.models.app.bsky.embed",
    ]:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(root)] if pkg_name == "atproto_client" else []
        pkg.__package__ = pkg_name
        real[pkg_name] = pkg

    sys.modules.update(real)

    # 2. Real leaf modules (dependency order matters)
    try:
        _load_from_file("atproto_client.exceptions", root / "exceptions.py", real)
        sys.modules["atproto_client.exceptions"] = real["atproto_client.exceptions"]

        _load_from_file("atproto_client.models.base", root / "models" / "base.py", real)
        sys.modules["atproto_client.models.base"] = real["atproto_client.models.base"]

        _load_from_file(
            "atproto_client.models.blob_ref",
            root / "models" / "blob_ref.py",
            real,
        )
        sys.modules["atproto_client.models.blob_ref"] = real["atproto_client.models.blob_ref"]

        _load_from_file(
            "atproto_client.models.string_formats",
            root / "models" / "string_formats.py",
            real,
        )
        sys.modules["atproto_client.models.string_formats"] = real["atproto_client.models.string_formats"]

        defs_mod = _load_from_file(
            "atproto_client.models.app.bsky.embed.defs",
            root / "models" / "app" / "bsky" / "embed" / "defs.py",
            real,
        )
        sys.modules["atproto_client.models.app.bsky.embed.defs"] = defs_mod

        images_mod = _load_from_file(
            "atproto_client.models.app.bsky.embed.images",
            root / "models" / "app" / "bsky" / "embed" / "images.py",
            real,
        )
        sys.modules["atproto_client.models.app.bsky.embed.images"] = images_mod

        # Resolve pydantic forward references so models are fully usable.
        # images.py declares BlobRef and models.AppBskyEmbedDefs.AspectRatio
        # as forward-reference strings; we supply the real objects here.
        blob_ref_cls = real["atproto_client.models.blob_ref"].BlobRef

        class _FakeModels:
            AppBskyEmbedDefs = defs_mod
            AppBskyEmbedImages = images_mod

        ns = {"BlobRef": blob_ref_cls, "models": _FakeModels}
        images_mod.Image.model_rebuild(_types_namespace=ns)
        images_mod.Main.model_rebuild(_types_namespace=ns)

        yield defs_mod, images_mod, real["atproto_client.models.blob_ref"]

    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_aspect_ratio_exists_on_embed_defs():
    """AppBskyEmbedDefs must expose an AspectRatio class."""
    with _real_embed_modules() as (defs_mod, _, _blob):
        assert hasattr(defs_mod, "AspectRatio"), (
            "atproto_client.models.app.bsky.embed.defs has no AspectRatio — "
            "the SDK may have moved it; update bluesky.py accordingly"
        )


def test_aspect_ratio_not_on_embed_images():
    """AppBskyEmbedImages must NOT have AspectRatio (it lives in EmbedDefs)."""
    with _real_embed_modules() as (_, images_mod, _blob):
        assert not hasattr(images_mod, "AspectRatio"), (
            "AspectRatio appeared on embed.images — the code in bluesky.py "
            "may need to be updated if the SDK restructured its models"
        )


def test_aspect_ratio_is_constructable_with_correct_dimensions():
    """AspectRatio can be instantiated and stores width/height correctly."""
    with _real_embed_modules() as (defs_mod, _, _blob):
        ar = defs_mod.AspectRatio(width=800, height=1200)
        assert ar.width == 800
        assert ar.height == 1200


def test_bluesky_poster_passes_aspect_ratio_to_send_post():
    """
    End-to-end unit test: BlueskyPoster.post() must call send_post (not
    send_image) and the embed must carry the correct AspectRatio dimensions
    derived from the real image bytes.
    """
    import io
    from PIL import Image as PilImage

    # Build a real 80×120 PNG in memory (2:3 ratio)
    buf = io.BytesIO()
    PilImage.new("RGB", (80, 120), color=(255, 0, 0)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    with _real_embed_modules() as (defs_mod, images_mod, blob_ref_mod):
        # Mirror the atproto models namespace (Client is separately mocked)
        class _FakeModels:
            AppBskyEmbedDefs = defs_mod
            AppBskyEmbedImages = images_mod

        fake_models = _FakeModels()

        # upload_blob must return a real BlobRef — pydantic strict mode rejects MagicMocks
        fake_blob = blob_ref_mod.BlobRef(mime_type="image/png", size=len(png_bytes), ref="bafytest")
        mock_client = MagicMock()
        mock_client.upload_blob.return_value = MagicMock(blob=fake_blob)
        mock_client.send_post.return_value = MagicMock(uri="at://did:plc:test/post/1")

        # Patch Client and models in bluesky's namespace, then call post()
        from unittest.mock import patch
        from trello_post_scheduler.trello import CardPost

        with (
            patch("trello_post_scheduler.platforms.bluesky.Client", return_value=mock_client),
            patch("trello_post_scheduler.platforms.bluesky.models", fake_models),
        ):
            from trello_post_scheduler.config import BlueskyConfig
            from trello_post_scheduler.platforms.bluesky import BlueskyPoster

            poster = BlueskyPoster(BlueskyConfig(handle="h.bsky.social", password="pw"))
            result = poster.post(
                CardPost(text="hello", image_bytes=png_bytes, image_mime="image/png", alt_text="red square")
            )

        assert result.success is True
        mock_client.send_image.assert_not_called()
        mock_client.send_post.assert_called_once()

        embed = mock_client.send_post.call_args[1]["embed"]

        # The embed must contain a real AppBskyEmbedImages.Main instance
        assert isinstance(embed, images_mod.Main)

        img_entry = embed.images[0]
        assert isinstance(img_entry, images_mod.Image)
        assert img_entry.alt == "red square"
        assert img_entry.image is fake_blob

        # The aspect ratio must be a real AspectRatio with the correct dims
        ar = img_entry.aspect_ratio
        assert isinstance(ar, defs_mod.AspectRatio), (
            f"aspect_ratio is {type(ar)}, expected defs_mod.AspectRatio — "
            "bluesky.py is probably using the wrong model class"
        )
        assert ar.width == 80
        assert ar.height == 120
