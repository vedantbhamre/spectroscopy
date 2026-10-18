import pytest

from app.schemas import Citation
from app.services.citations import normalise, page_numbers, verify

# Quotes used in the frontend demo, checked against the materials.
REAL = [
    ("S01", "9", "Vibrational spectroscopy in the mid-IR range (4000–400 cm-1) is one of the most informative methods of chemical analysis."),
    ("S02", "7", "Robust 100-300m cables made with Silica fibers of low OH-content"),
    ("S02", "13", "Application: measurement of water content in petroleum"),
    ("S01", "16", "NIR spectroscopy is effective for tracking major components like glucose or glycerol in the millimolar range"),
    ("S01", "5", "NIR, UV, and fluorescence spectra contain broad, highly overlapping signals"),
    ("S03", "2", "seven pairs each of tumor and normal in vitro clinical samples from different patients"),
    ("S03", "9", "histologically observed tumor discrimination"),
    ("S01", "14", "specifically in the feed frame of a rotary tablet press"),
    ("S01", "15", "By combining Raman and NIR, these models can predict API potency or coating thickness with higher accuracy and robustness than single-method models."),
]


@pytest.mark.parametrize("source,page,quote", REAL)
def test_real_quotes_verify(source, page, quote):
    assert verify(Citation(source=source, page=page, quote=quote)).check == "verified"


def test_visual_note_is_labelled():
    c = verify(Citation(source="S02", page="6", quote="standard and Al/Cu-coated VIS-NIR silica fibers 350–2400 nm"))
    assert c.check == "visual_note"


def test_page_range_matches_either_page():
    assert verify(Citation(source="S01", page="14–15", quote="specifically in the feed frame of a rotary tablet press")).check == "verified"


def test_wrong_page_fails():
    assert verify(Citation(source="S01", page="3", quote="specifically in the feed frame of a rotary tablet press")).check == "failed"


def test_invented_quote_fails():
    assert verify(Citation(source="S01", page="15", quote="Raman guarantees a valid calibration for any new formulation")).check == "failed"


def test_missing_page_fails():
    assert verify(Citation(source="S04", page="99", quote="anything at all here")).check == "failed"


def test_no_quote_is_unverified():
    assert verify(Citation(source="S01", page="10")).check == "unverified"


def test_normalise_handles_breaks_and_dashes():
    assert normalise("fiber -optic\nprobe – NIR") == normalise("fiber-optic probe - NIR")


def test_page_numbers():
    assert page_numbers("14–15") == [14, 15]
    assert page_numbers("Table 1 (p.6)") == [6]
    assert page_numbers("10") == [10]


def test_ellipsis_and_quote_style():
    from app.schemas import Citation
    from app.services.citations import verify

    ok = verify(Citation(source="S01", page="5", quote="NIR spectroscopy, with its relatively large penetration depth..."))
    assert ok.check == "verified"
    gap = verify(Citation(source="S01", page="17", quote="The use of Near-Infrared (NIR) spectroscopy ... modern dairy 'Process Analytical Technology'"))
    assert gap.check == "verified"
    wrong = Citation(source="S01", page="17", quote="modern dairy ... The use of Near-Infrared (NIR) spectroscopy")
    assert verify(wrong, allow_snap=False).check == "failed"
    snapped = verify(wrong)  # near-verbatim: replaced by the exact page passage it reproduces
    assert snapped.check == "verified" and snapped.quote != wrong.quote


def test_invented_quote_is_not_snapped():
    from app.schemas import Citation
    from app.services.citations import verify

    assert verify(Citation(source="S02", page="13", quote="Silica fibres transmit the full mid-IR range without loss")).check == "failed"
    near = verify(Citation(source="S01", page="10", quote="NIR spectra (780–2500 nm) contain predominantly overtones and combination bands"))
    assert near.check == "verified" and near.quote.startswith("NIR spectra")


def test_trailing_full_stop_where_the_sentence_continues():
    from app.schemas import Citation
    from app.services.citations import verify

    q = "The difference in operating wavelength ranges—from 360 nm to 25,000 nm (400 cm-1)—requires the use of different light sources, optics, and detectors."
    assert verify(Citation(source="S01", page="4", quote=q)).check == "verified"
