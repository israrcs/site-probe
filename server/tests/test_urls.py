from app.utils.urls import normalize_url, same_site, slug_for_url, strip_fragment


def test_normalize_adds_scheme():
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url(" http://Example.com/Path ") == "http://example.com/Path"


def test_normalize_strips_fragment():
    assert normalize_url("http://x.com/a#section") == "http://x.com/a"


def test_strip_fragment_keeps_query():
    assert strip_fragment("http://x.com/a?b=1#c") == "http://x.com/a?b=1"


def test_same_site():
    assert same_site("http://a.com/x", "https://a.com/y")
    assert not same_site("http://a.com", "http://b.com")


def test_slug_unique_and_safe():
    used = set()
    s1 = slug_for_url("http://x.com/blog/post", used)
    s2 = slug_for_url("http://x.com/blog/post?ref=x", used)
    s3 = slug_for_url("http://x.com/blog/post?ref=y", used)
    assert s1 != s2 != s3
    assert s1 in used and s2 in used and s3 in used
    assert "/" not in s1
