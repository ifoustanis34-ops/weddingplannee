from staff.badges import fit, text_width, two_lines


def test_two_lines_splits_like_the_reference() -> None:
    assert two_lines("Ensemble, construisons un avenir digital.") == [
        "Ensemble, construisons",
        "un avenir digital.",
    ]
    assert two_lines("Bienvenue") == ["Bienvenue"]


def test_fit_keeps_the_reference_size_when_the_text_fits() -> None:
    assert fit("Canopy House SARL", "700-normal", 6.8, 31.5) == "6.80pt"


def test_fit_shrinks_a_long_text_to_its_box() -> None:
    size = fit("Maison Élégance Events SARL", "700-normal", 6.8, 31.5)
    assert float(size[:-2]) < 6.8
    assert text_width("Maison Élégance Events SARL", "700-normal", float(size[:-2])) <= 31.6
