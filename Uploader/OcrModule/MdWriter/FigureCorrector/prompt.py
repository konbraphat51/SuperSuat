"""The instructions the grounding model redraws a page's figure boxes with."""

CORRECTION_PROMPT = """You correct the figure boxes of one document page. A layout detector boxed the figures of the page, and a transcriber reading the page found the boxes wrong; its request says what is wrong.

You are given the page twice: first with the current boxes drawn on in red, each labeled with its id, then as scanned. The current boxes are also listed in <current_figures>.

Rules:
- A figure is a picture, photograph, diagram, chart, plot or drawing. Tables, formulas and text are not figures and get no box.
- A figure's box holds the whole figure: every part of the drawing, with its axes, tick labels, legend and the labels drawn in or around it, but not its caption (such as "Figure 3: ...") and not the body text around it.
- Give each figure one box. Panels printed together under one caption are one figure.
- Do what the request asks, and keep every other box as it is, with its id.
- Coordinates are on the page as scanned: [x1, y1, x2, y2], the top-left and bottom-right corners, scaled to 0-1000 of the page's width and height.

Answer with JSON only, no explanation and no code fence, listing every figure of the page after the correction:
{"figures": [{"id": 3, "bbox_2d": [x1, y1, x2, y2]}, {"id": null, "bbox_2d": [x1, y1, x2, y2]}]}
- "id" is the id of a current box you keep or redraw, or null for a figure that had no box.
- Leave a box out to remove it. Answer {"figures": []} when the page holds no figure at all.
"""
