from types import SimpleNamespace as NS

from app.engine.validator import Ctx, r_duplicate_document


def document(**kwargs):
    values = dict(id=1, doc_type="LAND_DOCUMENT", sha256="a", phash="0000000000000000",
                  reference_no="REF/A", extracted_fields={}, ocr_text="", infra=None, file_name="land.pdf")
    return NS(**(values | kwargs))


def evaluate(mine, other, name="Applicant", campus=None, other_campus=None):
    ctx = Ctx.__new__(Ctx)
    ctx.inst = NS(id=1, name=name, campus_gps=campus)
    ctx.docs = [mine]
    ctx.records_checked = {}
    ctx.db = NS(execute=lambda statement: NS(all=lambda: [(other, NS(application_no="OTHER/1"),
                                    NS(name="Original Owner", permanent_id="2", campus_gps=other_campus))]))
    rule = {"id": "R-DUP-001", "severity": "CRITICAL", "kind": "DUPLICATE", "name": "Duplicate"}
    return r_duplicate_document(rule, ctx)


def test_same_layout_with_distinct_references_is_not_duplicate():
    assert evaluate(document(), document(id=2, sha256="b", reference_no="REF/B")).failed == 0


def test_identical_file_claimed_by_different_institution_is_detected():
    assert evaluate(document(), document(id=2)).failed == 1


def test_near_duplicate_requires_matching_content():
    assert evaluate(document(), document(id=2, sha256="b")).failed == 1


def test_identifiable_original_owner_is_not_penalised():
    own = document(extracted_fields={"institutionName": {"value": "Applicant"}})
    assert evaluate(own, document(id=2)).failed == 0


def test_geotagged_original_photo_owner_is_not_penalised():
    gps = {"lat": 22.299, "lng": 73.357}
    other = {"lat": 29.7, "lng": 76.9}
    photo = document(doc_type="INFRA_PHOTO_CLASSROOM", infra={"exif": {"gps": gps}})
    assert evaluate(photo, document(id=2), campus=gps, other_campus=other).failed == 0
