"""اختبارات التجزئة وكشف التكرار."""

from shared.hashing import sha256_hex, stable_record_key


def test_sha256_hex_deterministic():
    assert sha256_hex("نص") == sha256_hex("نص")
    assert sha256_hex("نص") != sha256_hex("نص آخر")


def test_sha256_hex_known_value():
    assert sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_stable_record_key_stable_across_calls():
    key1 = stable_record_key("sistani.org", "https://x/book/1/", "https://x/book/1/2/", 33)
    key2 = stable_record_key("sistani.org", "https://x/book/1/", "https://x/book/1/2/", 33)
    assert key1 == key2


def test_stable_record_key_differs_for_different_issue_numbers():
    key33 = stable_record_key("sistani.org", "book", "section", 33)
    key34 = stable_record_key("sistani.org", "book", "section", 34)
    assert key33 != key34


def test_stable_record_key_handles_none_issue_number():
    key = stable_record_key("sistani.org", "book", "section", None)
    assert len(key) == 32
