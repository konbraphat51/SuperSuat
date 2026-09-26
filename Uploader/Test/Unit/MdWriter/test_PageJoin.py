"""Tests for deciding which page turns split a paragraph."""

from FakeModel import RecordingFakeModel

from OcrModule.MdWriter.Syntax.Markers import ContinuationSplit
from OcrModule.MdWriter.Assembly.PageJoin import JoinJudge, decide_joins


def page(body: str, starts: bool = False, ends: bool = False) -> ContinuationSplit:
    return ContinuationSplit(
        body=body, continues_previous=starts, continued_by_next=ends
    )


def test_pages_that_agree_decide_without_the_judge():
    model = RecordingFakeModel.replying()
    pages = [page("a", ends=True), page("b", starts=True), page("c")]

    assert decide_joins(pages, JoinJudge(model)) == [True, False]
    assert model.requests == []


def test_the_judge_settles_a_turn_the_pages_disagree_on():
    model = RecordingFakeModel.replying("join")
    pages = [page("the text", ends=True), page("runs on")]

    joins = decide_joins(pages, JoinJudge(model))

    assert joins == [True]
    sent = str(model.requests[0][1].content)
    assert "<end_of_page>\nthe text\n</end_of_page>" in sent
    assert "<start_of_next_page>\nruns on\n" in sent


def test_without_a_judge_a_sentence_left_open_is_joined():
    pages = [
        page("the text", ends=True),
        page("runs on"),
        page("to its end."),
        page("next", starts=True),
    ]

    assert decide_joins(pages) == [True, False, False]


def test_a_heading_never_continues_a_paragraph():
    model = RecordingFakeModel.replying()

    joins = decide_joins(
        [page("a", ends=True), page("## b", starts=True)], JoinJudge(model)
    )

    assert joins == [False]


def test_a_figure_at_the_turn_is_looked_past():
    pages = [
        page("the text\n\n![a](figure:0)", ends=True),
        page("runs on", starts=True),
    ]

    assert decide_joins(pages) == [True]


def test_a_table_of_contents_over_a_turn_is_never_joined():
    pages = [
        page(":::toc\n- 1 | A | 1\n:::", ends=True),
        page(":::toc\n- 2 | B | 9\n:::", starts=True),
    ]

    assert decide_joins(pages) == [False]
