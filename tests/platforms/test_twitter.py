from unittest.mock import MagicMock, patch

from trello_post_scheduler.config import TwitterConfig
from trello_post_scheduler.platforms.twitter import TwitterPoster, MAX_CHARS
from trello_post_scheduler.trello import CardPost


def _cfg():
    return TwitterConfig(api_key="k", api_secret="s", access_token="at",
                         access_secret="as", bearer_token="bt")


@patch("trello_post_scheduler.platforms.twitter.tweepy.OAuth1UserHandler")
@patch("trello_post_scheduler.platforms.twitter.tweepy.API")
@patch("trello_post_scheduler.platforms.twitter.tweepy.Client")
def test_post_success(mock_client_cls, mock_api_cls, mock_handler_cls):
    mock_client = mock_client_cls.return_value
    mock_client.create_tweet.return_value = MagicMock(data={"id": "tweet123"})

    poster = TwitterPoster(_cfg())
    result = poster.post(CardPost(text="hello world"))

    assert result.success is True
    assert result.post_id == "tweet123"
    mock_client.create_tweet.assert_called_once_with(text="hello world", media_ids=None)


@patch("trello_post_scheduler.platforms.twitter.tweepy.OAuth1UserHandler")
@patch("trello_post_scheduler.platforms.twitter.tweepy.API")
@patch("trello_post_scheduler.platforms.twitter.tweepy.Client")
def test_post_truncates_long_text(mock_client_cls, mock_api_cls, mock_handler_cls):
    mock_client = mock_client_cls.return_value
    mock_client.create_tweet.return_value = MagicMock(data={"id": "t1"})

    poster = TwitterPoster(_cfg())
    poster.post(CardPost(text="x" * 500))

    call_text = mock_client.create_tweet.call_args[1]["text"]
    assert len(call_text) == MAX_CHARS


@patch("trello_post_scheduler.platforms.twitter.tweepy.OAuth1UserHandler")
@patch("trello_post_scheduler.platforms.twitter.tweepy.API")
@patch("trello_post_scheduler.platforms.twitter.tweepy.Client")
def test_post_failure(mock_client_cls, mock_api_cls, mock_handler_cls):
    import tweepy
    mock_client = mock_client_cls.return_value
    mock_client.create_tweet.side_effect = tweepy.TweepyException("rate limit")

    poster = TwitterPoster(_cfg())
    result = poster.post(CardPost(text="hello"))

    assert result.success is False
    assert "rate limit" in result.error


@patch("trello_post_scheduler.platforms.twitter.tweepy.OAuth1UserHandler")
@patch("trello_post_scheduler.platforms.twitter.tweepy.API")
@patch("trello_post_scheduler.platforms.twitter.tweepy.Client")
def test_post_with_image(mock_client_cls, mock_api_cls, mock_handler_cls):
    mock_client = mock_client_cls.return_value
    mock_api = mock_api_cls.return_value
    mock_client.create_tweet.return_value = MagicMock(data={"id": "t1"})
    mock_api.media_upload.return_value = MagicMock(media_id=999)

    poster = TwitterPoster(_cfg())
    post = CardPost(text="hello", image_bytes=b"imgdata", image_mime="image/jpeg", alt_text="desc")
    result = poster.post(post)

    assert result.success is True
    mock_api.media_upload.assert_called_once()
    mock_client.create_tweet.assert_called_once_with(text="hello", media_ids=[999])
