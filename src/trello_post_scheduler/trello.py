from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from trello import TrelloClient as _TrelloClient

from trello_post_scheduler.config import TrelloConfig
from trello_post_scheduler.exceptions import TrelloError

log = logging.getLogger(__name__)

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _parse_newlines(text: str) -> str:
    r"""Replace literal \n sequences in text with actual newline characters."""
    return text.replace("\\n", "\n")


@dataclass
class CardPost:
    text: str
    image_bytes: bytes | None = None
    image_mime: str | None = None
    alt_text: str | None = None


class TrelloClient:
    def __init__(self, cfg: TrelloConfig):
        self.cfg = cfg
        self.client = _TrelloClient(api_key=cfg.api_key, token=cfg.api_token)
        self._board = self.client.get_board(cfg.board_id)

    def _find_list(self, name: str):
        for lst in self._board.list_lists():
            if lst.name == name:
                return lst
        raise TrelloError(f"list not found: {name!r}")

    def get_cards(self, *, limit: int = 1):
        """Fetch unposted cards from the source list."""
        source = self._find_list(self.cfg.source_list)
        cards = source.list_cards()
        if not cards:
            return []
        return cards[:limit]

    def card_to_post(self, card) -> CardPost:
        """Extract post content from a Trello card, including image if attached."""
        attachments = card.get_attachments()
        image_att = None
        for att in attachments:
            if att.is_upload and att.mime_type in SUPPORTED_IMAGE_TYPES:
                image_att = att
                break

        if image_att:
            # Trello attachment downloads require OAuth header on api.trello.com
            download_url = image_att.url.replace(
                "https://trello.com/", "https://api.trello.com/",
            )
            auth_header = (
                f'OAuth oauth_consumer_key="{self.cfg.api_key}", '
                f'oauth_token="{self.cfg.api_token}"'
            )
            resp = requests.get(
                download_url,
                headers={"Authorization": auth_header},
                timeout=30,
            )
            resp.raise_for_status()
            alt = (card.description or "").strip() or None
            return CardPost(
                text=_parse_newlines(card.name),
                image_bytes=resp.content,
                image_mime=image_att.mime_type,
                alt_text=alt,
            )

        # No image — existing behavior
        desc = (card.description or "").strip()
        return CardPost(text=desc if desc else _parse_newlines(card.name))

    def delete_card(self, card) -> None:
        """Delete a card after successful posting."""
        card.delete()
        log.info("deleted card %s", card.name)
