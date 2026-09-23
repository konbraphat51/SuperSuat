- Write SOLID, readable, and maintainable code
- Write comments in English
  - Comments should be concise. Should be only single line per topic. Do not alterline comments even if they are long.
    - There is NO need to leave comments for each code update.
      - ex: "This code is left because of..."
      - ex: "This code is deleted because of..."
    - Be aware if the code readers would prefer to read your comments, or it is just noise for them.
  - Write comments for the responsibility of the file itself at the top
  - Write comments for each public class/method/variable
    - If Python, write in docstring format
    - If C#, write in XML format
    - If TypeScript, write in TSDoc format

```python:sample.py
def transcribe(
    self,
    all_pages: list[Image],
    blocker_result: BlockerResult,
) -> TranscriptionResult:
    """Transcribes every TEXT block of blocker_result, cropped from all_pages.

    Args:
        all_pages: Every page image, indexed by Block.page_number.
        blocker_result: The blocks detected by a Blocker, to be transcribed.
    """
    transcriptions: list[TranscriptionBlock] = []

    # for each block...
    for block in blocker_result.blocks:
        # ...OCR the block

        # skip if the block is not text
        if block.block_type != BlockType.TEXT:
            continue

        # image extraction
        block_image = self._extract_block_image(all_pages[block.page_number], block)

        # transcribe the block image
        text = self._ocr_block_image(block_image)
        transcriptions.append(TranscriptionBlock(block, text))

    return TranscriptionResult(transcriptions)
```

- Prepare English and Japanese versions for all documents.
- all in-UI text should be in English by default, but support Japanese localization.
- Everytime updated the code, check all documents and update them if necessary.
- Debug the frontend by yourself
- Make granular commits for each unit of implementation. One commit per small, self-contained
  unit. Do not bundle a whole subsystem into one commit. Commit each unit as soon as its checks pass.
- If you use Python
  - Use `uv` for package management
  - Enable strict typing
  - Add appropriate package for better code/quality
- If you use JavaScript/TypeScript
  - Use `pnpm` for package management
  - Add appropriate package for better code/quality
  - Use Vue for frontend
    - Granular components are preferred.
  - Write in Single File Component style, such as

```vue
<template>HTML</template>
<script>
export default {
  name:...
}
</script>
<style scoped></style>
```

- Write documents to understand the code architecture. Such as: class diagram, sequence diagram...
