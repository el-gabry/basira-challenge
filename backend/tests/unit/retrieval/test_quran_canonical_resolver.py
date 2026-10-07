from types import SimpleNamespace

from basira.retrieval.quran_canonical_resolver import (
    resolve_canonical_quran_point,
)


class FakeQuranRepository:
    def __init__(self) -> None:
        self._verses = {
            (2, 1): SimpleNamespace(
                surah_number=2,
                ayah_number=1,
                surah_name_ar="البقرة",
                surah_name_en="Al-Baqarah",
                text_search="الم",
            ),
            (2, 255): SimpleNamespace(
                surah_number=2,
                ayah_number=255,
                surah_name_ar="البقرة",
                surah_name_en="Al-Baqarah",
                text_search=(
                    "وسع كرسيه السماوات والأرض"
                ),
            ),
            (49, 1): SimpleNamespace(
                surah_number=49,
                ayah_number=1,
                surah_name_ar="الحجرات",
                surah_name_en="Al-Hujurat",
                text_search=(
                    "يا أيها الذين آمنوا لا تقدموا"
                ),
            ),
            (49, 10): SimpleNamespace(
                surah_number=49,
                ayah_number=10,
                surah_name_ar="الحجرات",
                surah_name_en="Al-Hujurat",
                text_search=(
                    "إنما المؤمنون إخوة"
                ),
            ),
            (94, 1): SimpleNamespace(
                surah_number=94,
                ayah_number=1,
                surah_name_ar="الشرح",
                surah_name_en="Ash-Sharh",
                text_search=(
                    "ألم نشرح لك صدرك"
                ),
            ),
            (94, 5): SimpleNamespace(
                surah_number=94,
                ayah_number=5,
                surah_name_ar="الشرح",
                surah_name_en="Ash-Sharh",
                text_search=(
                    "فإن مع العسر يسرا"
                ),
            ),
            (94, 6): SimpleNamespace(
                surah_number=94,
                ayah_number=6,
                surah_name_ar="الشرح",
                surah_name_en="Ash-Sharh",
                text_search=(
                    "إن مع العسر يسرا"
                ),
            ),
        }

    def get(
        self,
        surah_number: int,
        ayah_number: int,
    ):
        return self._verses.get(
            (
                surah_number,
                ayah_number,
            )
        )


def test_resolves_canonical_numeric_reference() -> None:
    result = resolve_canonical_quran_point(
        question=(
            "ما معنى الآية 2:255؟"
        ),
        repository=FakeQuranRepository(),
    )

    assert result is not None
    assert result.reference == "2:255"


def test_resolves_arabic_surah_name_and_ayah() -> None:
    result = resolve_canonical_quran_point(
        question=(
            "ما نص الآية 10 من سورة الحجرات؟"
        ),
        repository=FakeQuranRepository(),
    )

    assert result is not None
    assert result.reference == "49:10"


def test_resolves_english_surah_name_and_ayah() -> None:
    result = resolve_canonical_quran_point(
        question=(
            "What is verse 10 of Surah Al-Hujurat?"
        ),
        repository=FakeQuranRepository(),
    )

    assert result is not None
    assert result.reference == "49:10"


def test_resolves_partial_quran_text() -> None:
    result = resolve_canonical_quran_point(
        question=(
            "ما تفسير قوله تعالى "
            "إن مع العسر يسرا؟"
        ),
        repository=FakeQuranRepository(),
    )

    assert result is not None
    assert result.reference == "94:6"


def test_resolves_ayat_al_kursi_partial_text() -> None:
    result = resolve_canonical_quran_point(
        question=(
            "ما معنى قوله تعالى "
            "وسع كرسيه السماوات والأرض؟"
        ),
        repository=FakeQuranRepository(),
    )

    assert result is not None
    assert result.reference == "2:255"


def test_ambiguous_partial_text_fails_closed() -> None:
    repo = FakeQuranRepository()

    repo._verses[
        (3, 1)
    ] = SimpleNamespace(
        surah_number=3,
        ayah_number=1,
        surah_name_ar="آل عمران",
        surah_name_en="Ali-Imran",
        text_search=(
            "وسع كرسيه السماوات والأرض"
        ),
    )

    result = resolve_canonical_quran_point(
        question=(
            "ما معنى قوله تعالى "
            "وسع كرسيه السماوات والأرض؟"
        ),
        repository=repo,
    )

    assert result is None


def test_surah_name_prefix_collision_does_not_create_ambiguity() -> None:
    repo = FakeQuranRepository()

    repo._verses[
        (15, 1)
    ] = SimpleNamespace(
        surah_number=15,
        ayah_number=1,
        surah_name_ar="الحجر",
        surah_name_en="Al-Hijr",
        text_search=(
            "الر تلك آيات الكتاب وقرآن مبين"
        ),
    )

    result = resolve_canonical_quran_point(
        question=(
            "ما نص الآية 10 من سورة الحجرات؟"
        ),
        repository=repo,
    )

    assert result is not None
    assert result.reference == "49:10"
