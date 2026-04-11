from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from trello_post_scheduler.config import TrelloConfig
from trello_post_scheduler.trello import TrelloClient
from trello_post_scheduler.exceptions import TrelloError


@pytest.fixture
def trello_cfg():
    return TrelloConfig(
        api_key="k", api_token="t", board_id="b",
        source_list="Ready",
    )


def _make_card(name="Test Card", description="Hello world", attachments=None):
    card = MagicMock()
    card.name = name
    card.description = description
    card.id = "card123"
    card.get_attachments.return_value = attachments or []
    return card


def _make_list(name, cards=None):
    lst = MagicMock()
    lst.name = name
    lst.id = f"list_{name}"
    lst.list_cards.return_value = cards or []
    return lst


@patch("trello_post_scheduler.trello._TrelloClient")
def test_get_cards_ordered(mock_client_cls, trello_cfg):
    cards = [_make_card(f"Card {i}") for i in range(5)]
    source = _make_list("Ready", cards)

    board = MagicMock()
    board.list_lists.return_value = [source]
    mock_client_cls.return_value.get_board.return_value = board

    client = TrelloClient(trello_cfg)
    result = client.get_cards(limit=2)
    assert len(result) == 2
    assert result[0].name == "Card 0"


@patch("trello_post_scheduler.trello._TrelloClient")
def test_get_cards_empty(mock_client_cls, trello_cfg):
    source = _make_list("Ready", [])
    board = MagicMock()
    board.list_lists.return_value = [source]
    mock_client_cls.return_value.get_board.return_value = board

    client = TrelloClient(trello_cfg)
    assert client.get_cards(limit=1) == []


@patch("trello_post_scheduler.trello._TrelloClient")
def test_list_not_found(mock_client_cls, trello_cfg):
    board = MagicMock()
    board.list_lists.return_value = [_make_list("Other")]
    mock_client_cls.return_value.get_board.return_value = board

    client = TrelloClient(trello_cfg)
    with pytest.raises(TrelloError, match="not found"):
        client.get_cards(limit=1)


@patch("trello_post_scheduler.trello._TrelloClient")
def test_delete_card(mock_client_cls, trello_cfg):
    source = _make_list("Ready")
    board = MagicMock()
    board.list_lists.return_value = [source]
    mock_client_cls.return_value.get_board.return_value = board

    card = _make_card()
    client = TrelloClient(trello_cfg)
    client.delete_card(card)
    card.delete.assert_called_once()



@patch("trello_post_scheduler.trello.requests.get")
@patch("trello_post_scheduler.trello._TrelloClient")
def test_card_to_post_no_attachment(mock_client_cls, mock_get, trello_cfg):
    board = MagicMock()
    board.list_lists.return_value = [_make_list("Ready")]
    mock_client_cls.return_value.get_board.return_value = board

    client = TrelloClient(trello_cfg)
    card = _make_card(name="Title", description="Body text")
    result = client.card_to_post(card)

    assert result.text == "Body text"
    assert result.image_bytes is None
    assert result.alt_text is None
    mock_get.assert_not_called()


@patch("trello_post_scheduler.trello.requests.get")
@patch("trello_post_scheduler.trello._TrelloClient")
def test_card_to_post_no_attachment_no_desc(mock_client_cls, mock_get, trello_cfg):
    board = MagicMock()
    board.list_lists.return_value = [_make_list("Ready")]
    mock_client_cls.return_value.get_board.return_value = board

    client = TrelloClient(trello_cfg)
    card = _make_card(name="Title", description="")
    result = client.card_to_post(card)

    assert result.text == "Title"
    assert result.image_bytes is None


@patch("trello_post_scheduler.trello.requests.get")
@patch("trello_post_scheduler.trello._TrelloClient")
def test_card_to_post_with_image(mock_client_cls, mock_get, trello_cfg):
    board = MagicMock()
    board.list_lists.return_value = [_make_list("Ready")]
    mock_client_cls.return_value.get_board.return_value = board

    mock_resp = MagicMock()
    mock_resp.content = b"imgdata"
    mock_get.return_value = mock_resp

    attachment = SimpleNamespace(
        url="https://trello.com/1/cards/abc/attachments/def/download/img.jpg",
        mime_type="image/jpeg",
        is_upload=True,
        name="img.jpg",
    )
    card = _make_card(name="Title", description="Alt text", attachments=[attachment])

    client = TrelloClient(trello_cfg)
    result = client.card_to_post(card)

    assert result.text == "Title"
    assert result.image_bytes == b"imgdata"
    assert result.image_mime == "image/jpeg"
    assert result.alt_text == "Alt text"
    mock_get.assert_called_once_with(
        "https://api.trello.com/1/cards/abc/attachments/def/download/img.jpg",
        headers={"Authorization": 'OAuth oauth_consumer_key="k", oauth_token="t"'},
        timeout=30,
    )


@patch("trello_post_scheduler.trello.requests.get")
@patch("trello_post_scheduler.trello._TrelloClient")
def test_card_to_post_parses_newlines_in_title(mock_client_cls, mock_get, trello_cfg):
    board = MagicMock()
    board.list_lists.return_value = [_make_list("Ready")]
    mock_client_cls.return_value.get_board.return_value = board

    client = TrelloClient(trello_cfg)
    card = _make_card(name=r"Line one\nLine two\nLine three", description="")
    result = client.card_to_post(card)

    assert result.text == "Line one\nLine two\nLine three"
    assert result.image_bytes is None


@patch("trello_post_scheduler.trello.requests.get")
@patch("trello_post_scheduler.trello._TrelloClient")
def test_card_to_post_parses_newlines_in_title_with_image(
    mock_client_cls, mock_get, trello_cfg,
):
    board = MagicMock()
    board.list_lists.return_value = [_make_list("Ready")]
    mock_client_cls.return_value.get_board.return_value = board

    mock_resp = MagicMock()
    mock_resp.content = b"imgdata"
    mock_get.return_value = mock_resp

    attachment = SimpleNamespace(
        url="https://trello.com/1/cards/abc/attachments/def/download/img.jpg",
        mime_type="image/jpeg",
        is_upload=True,
        name="img.jpg",
    )
    card = _make_card(
        name=r"Hello\nWorld", description="Alt text", attachments=[attachment],
    )

    client = TrelloClient(trello_cfg)
    result = client.card_to_post(card)

    assert result.text == "Hello\nWorld"
    assert result.image_bytes == b"imgdata"


@patch("trello_post_scheduler.trello.requests.get")
@patch("trello_post_scheduler.trello._TrelloClient")
def test_card_to_post_skips_non_image(mock_client_cls, mock_get, trello_cfg):
    board = MagicMock()
    board.list_lists.return_value = [_make_list("Ready")]
    mock_client_cls.return_value.get_board.return_value = board

    attachment = SimpleNamespace(
        url="https://trello.com/doc.pdf",
        mime_type="application/pdf",
        is_upload=True,
        name="doc.pdf",
    )
    card = _make_card(name="Title", description="Body", attachments=[attachment])

    client = TrelloClient(trello_cfg)
    result = client.card_to_post(card)

    assert result.text == "Body"
    assert result.image_bytes is None
    mock_get.assert_not_called()
