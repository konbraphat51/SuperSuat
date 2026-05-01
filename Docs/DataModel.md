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

#### ./{chapter_num}/

- `chapter_num`(int): Chapter number (starting from 1)

##### ./text.
