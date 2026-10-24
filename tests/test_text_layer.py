from lanes.text_layer import check_text


def test_clean_text_passes():
    assert not check_text("Pressure 50 % point reading 5.01 bar 4.98 5.02").broken


def test_soft_hyphen_and_zero_width_are_flagged():
    assert check_text("Pre­sion de aj​uste").broken
    assert check_text("a‌b").reasons


def test_mostly_non_word_tokens_are_flagged():
    assert check_text("���  ### ### ~~~ ~~~ @@@").broken
