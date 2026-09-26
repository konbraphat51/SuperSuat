"""The instructions the model judges a page turn with."""

# Whether the start of the next page continues the paragraph the page ends with.
JOIN_PROMPT = """Two consecutive pages of a document were transcribed separately. You are given the end of one page in <end_of_page> and the start of the next page in <start_of_next_page>.

Decide whether the start of the next page continues the same paragraph as the end of the page: the paragraph runs over the page turn, as when a sentence is cut in the middle.

Answer with exactly one word: join if it is one paragraph, break if they are separate paragraphs."""
