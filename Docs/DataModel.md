# Data Models

## Database Models

AWS S3 is used for storing all data.

### meta/papers.jsonl

Meta data for each paper.

- `paper_id`(int): UUID
- `title`(string): Title of the paper
- `authors`(string[]): List of authors
- `description`({string, string}): Very short description of the paper. Lang -> description.
- `tags`(string[]): List of tags
- `original_url`(string): Original URL of the paper
- `created_at`(int): Created at timestamp (unix time)
- `updated_at`(int): Updated at timestamp (unix time)

### papers/{paper_id}/

#### ./meta.json

- `chapters`(int): Number of chapters in the paper
- `languages_available`(string[]): List of languages available for translation and summary data.
- `original_language`(string): Original language of the paper.

#### ./{chapter_num}/

- `chapter_num`(int): Chapter number (starting from 1)

##### ./text.json

- `structure`(object): Structure information of the text
  - `sections`(object[]): List of sections in the chapter
    - `section_id`(int): Section unique number (starting from 1)
    - `title`(string): Title of the section
    - `blocks`(object[]): Text content of the section
      - `block_id`(int): Block unique number (starting from 1)
      - `type`("text", "equation", "figure", "table")
      - `content`(string)
        - Markdown format for "text", "table" type
        - LaTeX format for "equation" type
        - S3 key for "figure" type
      - `caption`(string|null): Caption for the block (only for "figure" and "table" type)
    - `children`(object[]): List of children sections
      - (recursive definition of section object)

##### ./translation/{language}.jsonl

- `block_id`(int): Block unique number (same as block_id in text.json)
- `content`(string): Translated patch
- `caption`(string|null): Translated caption (only for "figure" and "table" type)

##### ./summary.md

- Summary of the chapter in Markdown format.

##### ./highlights.jsonl

- `highlight_id`(int): Highlight unique number (starting from 1)
- `block_id_start`(int): Block unique number starting to annotate (same as block_id in text.json)
- `block_id_end`(int): Block unique number ending to annotate (same as block_id in text.json)
- `offset_start`(int): Offset in the starting block
- `offset_end`(int): Offset in the ending block
- `comment`(string): Comment for the highlight in Markdown format.
- `created_at`(int): Created at timestamp (unix time)
- `updated_at`(int): Updated at timestamp (unix time)
- `color`(string): color tag for the highlight
