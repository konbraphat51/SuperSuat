# StructureOrganizer

Step 3 of the blocked OCR pipeline (see [Plan.md](Plan.md)): the blocks a `Blocker`
found and a `Transcriber` read are settled into a document structure — each text
block's type, each heading's level in the hierarchy, each figure's caption, and the
reading order — one page at a time, by a multimodal model.

日本語版: [StructureOrganizer.ja.md](StructureOrganizer.ja.md)

## Structure

```mermaid
classDiagram
    class Organizer {
        -organizer_model: BaseChatModel
        +organize(all_page_images, all_page_images_rendered, blocker_result, transcription_result) OcrResult
        -_scan_page(page_index, all_page_images, page_image_rendered, processing_blocks)
    }
    class OrganizerAgent {
        -organizer_model: Runnable
        +scan_page(page_index, all_page_images, page_image_rendered, processing_blocks)
        -_request_orders(messages, page_index, batch_number) OrderBatch
        -_build_messages(page_index, all_page_images, page_image_rendered, processing_blocks) list[BaseMessage]
    }
    class OrderBatch {
        +orders: list[AnyOrder]
        +is_last_batch: bool
    }
    class Order {
        +order_label: ORDER_LABELS
    }
    class ProcessingBlock {
        +block_id: int
        +page_index: int
        +recognized_blocker_type: BlockType
        +new_type: str | None
        +have_been_labeled: bool
        +have_been_checked: bool
    }
    class ProcessingBlockText {
        +text: str
        +have_been_edited: bool
        +merging_previous_page: bool
    }
    class ProcessingBlockTextHeading {
        +heading_level: int | None
    }
    class ProcessingBlockFigure {
        +bounding_box: tuple
        +have_caption_checked: bool
        +caption_text_block_id: int | None
    }
    class DataExporter {
        +export_processing_blocks_to_ocr_result(processing_blocks) OcrResult
    }
    Organizer ..> OrganizerAgent
    Organizer ..> DataExporter
    DataExporter ..> OcrResult
    OrganizerAgent ..> OrderBatch
    OrderBatch *-- Order
    Order <|-- OrderSetBlockType
    Order <|-- OrderSetHeadingLevel
    Order <|-- OrderReorder
    Order <|-- OrderDeleteBlock
    Order <|-- OrderEditBlock
    Order <|-- OrderSetCaption
    Order <|-- OrderSetMergingPreviousPage
    ProcessingBlock <|-- ProcessingBlockText
    ProcessingBlock <|-- ProcessingBlockFigure
    ProcessingBlockText <|-- ProcessingBlockTextHeading
    OrganizerAgent ..> ProcessingBlock
```

The model never edits the blocks itself: it answers with an `OrderBatch`, and
`execute_orders()` is the only code that changes a `ProcessingBlock`. Which order a
piece of JSON is, is decided by its `order_label`, which pydantic uses as the union
discriminator, so each order arrives already validated against its own schema.

## Page scan

```mermaid
sequenceDiagram
    participant Organizer
    participant OrganizerAgent
    participant Model
    participant Executor as execute_orders
    Organizer->>OrganizerAgent: scan_page(page_index, all_page_images, page_image_rendered, processing_blocks)
    OrganizerAgent->>OrganizerAgent: _build_messages (prompt + page images + block state)
    loop until is_last_batch, at most MAX_BATCH_COUNT
        OrganizerAgent->>Model: invoke(messages)
        Model-->>OrganizerAgent: OrderBatch
        OrganizerAgent->>OrganizerAgent: deepcopy(processing_blocks)
        OrganizerAgent->>Executor: execute_orders(order_batch, copy)
        alt an order could not be applied
            Executor-->>OrganizerAgent: ValueError / TypeError
            OrganizerAgent->>OrganizerAgent: append rejection message, copy discarded
        else applied
            Executor-->>OrganizerAgent: copy, edited
            OrganizerAgent->>OrganizerAgent: write the copy back into processing_blocks
            opt not the last batch
                OrganizerAgent->>OrganizerAgent: append the updated block state
            end
        end
    end
    OrganizerAgent-->>Organizer: processing_blocks, edited in place
```

A batch is applied to a copy of the blocks, so a batch that fails partway leaves the
blocks exactly as they were and the model is told so before it tries again. The model
sets `is_last_batch` when the page is done; `MAX_BATCH_COUNT` only guards against a
model that never does.

Saying the page is done does not make it so: `_is_able_to_finish()` checks every block
on the page for a block_type, a heading for its level, and a figure for its caption
check, and a page still missing any of them goes back to the model with the blocks at
fault named. Once the page passes, its blocks are marked `have_been_checked`.

## Context given to the model

Every page scan resends the whole context, so it is kept to what the page needs:

- The page image of each heading the page still sits under, outermost first — the
  innermost heading open when the previous page ended, then the heading above it, up
  to the document's level 1 title. This is what keeps heading levels consistent across
  a long document: if the previous page ended under an H3, the pages of that H3, its
  H2, and the H1 are shown. Headings that share a page are named together on that one
  page image, which is sent once.
- The `RECENT_PAGE_COUNT` pages just before this one, for blocks that continue across
  a page boundary. A page already shown as a heading page is not sent twice.
- The page itself, as scanned.
- The page again, with each block outlined and labeled with its `block_id`, as
  `BlockRenderer` draws it (see [Blocker.md](Blocker.md)).
- The `ProcessingBlock` state of this page and the page before it, as JSON, in
  current order. One page back is all a block spanning a page boundary needs, and
  everything earlier is settled and is left out.

## Orders

| Order | Effect |
| --- | --- |
| `set_block_type` | Labels a text block with one of the `TEXT_BLOCK_TYPES`. |
| `set_heading_level` | Gives a heading its level, and labels it a heading. |
| `reorder` | Moves a block immediately in front of another. |
| `delete_block` | Removes a block, and clears any caption pointing at it. |
| `edit_block` | Changes only the fields it fills in: label, text, heading level. |
| `set_caption` | Ties a figure to its caption block, or to null for a figure that has none. Either way the figure counts as checked. |
| `set_merging_previous_page` | Marks a block as the rest of a block the previous page broke off. The join itself happens on export. |

Orders apply in list order, each one acting on the state the previous ones left. A
text block becomes a `ProcessingBlockTextHeading` as soon as it is labeled a heading
or given a level.

## Export

Once every page has been scanned, `export_processing_blocks_to_ocr_result()` turns the
flat list of blocks into the `OcrResult` tree, walking it in reading order:

- A heading opens a section, nested under the innermost open section of a lower level,
  and the heading itself becomes that section's first block. A heading of the same or
  a lower level closes the sections it is not inside, so `1.1` under `1.` nests, and a
  following `2.` becomes `1.`'s sibling.
- Anything else is appended to the section currently open. Blocks before the first
  heading land in the root section, which is the document itself.
- A figure's caption block is folded into the figure's `caption` and is not emitted as
  a block of its own, so the caption text appears once.
- A block marked `merging_previous_page` is folded into the last block of the previous
  page carrying the same label, and its page joins that block's `existing_pages`. The
  fold follows a chain, so a paragraph running over three pages ends up as one block.
  The two texts are joined with a space only where both sides of the join are ASCII -
  a space-separated script - and directly otherwise, since the line break the page
  forced was never part of the text. A word the page split across a hyphen keeps its
  hyphen, because dropping one the author wrote cannot be undone.
- Each section's `existing_pages` is the union of its contents', and `block_index` is
  handed out in document order, the root taking 0.

Nothing here rejects a document. A block the organizer never labeled is written down
as a `paragraph`, a heading left without a level opens no section, and a caption
pointing at a block that is not there is dropped - each with a warning in the log,
since losing a whole run over one block is worse than a document with one odd block
in it.

## Conventions

- A block the Blocker detected as an image or a table starts out labeled `figure` or
  `table`: that detection settles the type, so the organizer is left with the blocks
  it can actually judge.
- Every page held in a variable is an index counting from 0, named `page_index`:
  `scan_page`'s argument and `ProcessingBlock.page_index` alike. The `+ 1` happens
  only where a page number is shown - the prompt, the image labels, the block state
  JSON, and the logs - since a reader counts pages from 1. That is also why the JSON
  the model sees calls the field `page_number`.
- The model is given only ids that exist in the JSON it was shown, and an order
  naming an unknown id is rejected rather than ignored.
- All prompts and model-facing text are English.
