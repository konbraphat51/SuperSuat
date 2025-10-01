"""GUI wrapper for PDF Document Layout Analysis service endpoints.

This simple desktop utility replicates the curl commands from the layout-analysis
README, allowing users to:
 - Select a PDF file
 - Choose an endpoint (analyze, text, toc, markdown, html, visualize, ocr, info, health)
 - Provide optional parameters (fast, parse_tables_and_math, extract_toc, types, language, dpi, output_file)
 - Submit request and view JSON/text response or save binary output (zip/pdf)

Assumptions:
 - Service is running locally on http://localhost:5060 (user can change base URL)
 - Only a subset of endpoints is exposed for simplicity; extend ENDPOINT_SPECS to add more.
"""

from __future__ import annotations

import io
import json
import mimetypes
import os
import threading
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

import requests


DEFAULT_BASE_URL = "http://localhost:5060"


@dataclass
class ParamSpec:
    name: str
    label: str
    param_type: str  # 'bool', 'text', 'int', 'choice'
    default: Any = None
    choices: Optional[List[str]] = None
    placeholder: str | None = None
    required: bool = False
    help: str = ""


@dataclass
class EndpointSpec:
    path: str
    method: str  # GET or POST
    description: str
    needs_file: bool = False
    params: List[ParamSpec] = field(default_factory=list)
    binary_response: bool = False  # if True, offer save dialog directly


ENDPOINT_SPECS: Dict[str, EndpointSpec] = {
    "Analyze (/ - POST)": EndpointSpec(
        path="/",
        method="POST",
        description="Analyze PDF layout and extract segments",
        needs_file=True,
        params=[
            ParamSpec("fast", "Fast (LightGBM)", "bool", False, help="Use LightGBM models instead of VGT"),
            ParamSpec("parse_tables_and_math", "Parse tables & math", "bool", False),
        ],
    ),
    "Extract Text (/text)": EndpointSpec(
        path="/text",
        method="POST",
        description="Extract text by content types",
        needs_file=True,
        params=[
            ParamSpec("types", "Types (csv or 'all')", "text", "all", placeholder="title,text,table"),
            ParamSpec("fast", "Fast (LightGBM)", "bool", False),
        ],
    ),
    "TOC (/toc)": EndpointSpec(
        path="/toc", method="POST", description="Extract table of contents", needs_file=True, params=[ParamSpec("fast", "Fast", "bool", False)]
    ),
    "Markdown (/markdown)": EndpointSpec(
        path="/markdown",
        method="POST",
        description="Convert PDF to Markdown (zip)",
        needs_file=True,
        binary_response=True,
        params=[
            ParamSpec("extract_toc", "Extract TOC", "bool", False),
            ParamSpec("output_file", "Output filename", "text", "document.md"),
            ParamSpec("fast", "Fast", "bool", False),
        ],
    ),
    "HTML (/html)": EndpointSpec(
        path="/html",
        method="POST",
        description="Convert PDF to HTML (zip)",
        needs_file=True,
        binary_response=True,
        params=[
            ParamSpec("extract_toc", "Extract TOC", "bool", False),
            ParamSpec("output_file", "Output filename", "text", "document.html"),
            ParamSpec("fast", "Fast", "bool", False),
        ],
    ),
    "Visualize (/visualize)": EndpointSpec(
        path="/visualize",
        method="POST",
        description="Visualize segmentation (pdf)",
        needs_file=True,
        binary_response=True,
        params=[ParamSpec("fast", "Fast", "bool", False)],
    ),
    "OCR (/ocr)": EndpointSpec(
        path="/ocr",
        method="POST",
        description="Apply OCR to PDF (pdf)",
        needs_file=True,
        binary_response=True,
        params=[
            ParamSpec("language", "Language", "text", "en", placeholder="en"),
        ],
    ),
    "Info (/info)": EndpointSpec(path="/info", method="GET", description="Service info"),
    "Health (/ - GET)": EndpointSpec(path="/", method="GET", description="Health check"),
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Layout Analysis Client")
        self.geometry("980x720")
        self.minsize(900, 640)
        self.selected_file: str | None = None
        self.param_widgets: Dict[str, Any] = {}
        self.current_spec: EndpointSpec | None = None

        self._build_ui()
        self._set_status("Ready")

    # UI construction
    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(top, text="Base URL:").grid(row=0, column=0, sticky=tk.W)
        self.base_url_var = tk.StringVar(value=DEFAULT_BASE_URL)
        ttk.Entry(top, textvariable=self.base_url_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=4)

        ttk.Label(top, text="Endpoint:").grid(row=0, column=2, sticky=tk.W, padx=(12, 0))
        self.endpoint_var = tk.StringVar()
        endpoint_menu = ttk.Combobox(top, textvariable=self.endpoint_var, values=list(ENDPOINT_SPECS.keys()), state="readonly", width=32)
        endpoint_menu.grid(row=0, column=3, sticky=tk.W)
        endpoint_menu.bind("<<ComboboxSelected>>", self._on_endpoint_change)
        endpoint_menu.current(0)

        # Parameters container must exist before initial population
        self.params_container = ttk.LabelFrame(self, text="Parameters")
        self.params_container.pack(fill=tk.X, padx=8, pady=6)
        self._on_endpoint_change()  # populate initial params

        file_frame = ttk.Frame(self)
        file_frame.pack(fill=tk.X, padx=8)
        self.file_label_var = tk.StringVar(value="No file selected")
        ttk.Button(file_frame, text="Select PDF", command=self._choose_file).pack(side=tk.LEFT)
        ttk.Label(file_frame, textvariable=self.file_label_var).pack(side=tk.LEFT, padx=8)

        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(action_frame, text="Send Request", command=self._send_request).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="Clear Output", command=self._clear_output).pack(side=tk.LEFT, padx=6)

        output_frame = ttk.LabelFrame(self, text="Response")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.output_text = tk.Text(output_frame, wrap="none")
        self.output_text.pack(fill=tk.BOTH, expand=True)

        status_bar = ttk.Frame(self)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar()
        ttk.Label(status_bar, textvariable=self.status_var, anchor="w").pack(fill=tk.X)

    # Event handlers
    def _on_endpoint_change(self, *_):
        name = self.endpoint_var.get()
        self.current_spec = ENDPOINT_SPECS.get(name)
        for w in self.params_container.winfo_children():
            w.destroy()
        self.param_widgets.clear()
        if not self.current_spec:
            return
        row = 0
        ttk.Label(self.params_container, text=self.current_spec.description).grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(0, 4))
        row += 1
        for spec in self.current_spec.params:
            ttk.Label(self.params_container, text=spec.label + (" *" if spec.required else "")).grid(row=row, column=0, sticky=tk.W)
            if spec.param_type == "bool":
                var = tk.BooleanVar(value=bool(spec.default))
                cb = ttk.Checkbutton(self.params_container, variable=var)
                cb.grid(row=row, column=1, sticky=tk.W)
                self.param_widgets[spec.name] = var
            else:
                var = tk.StringVar(value="" if spec.default is None else str(spec.default))
                entry = ttk.Entry(self.params_container, textvariable=var, width=32)
                entry.grid(row=row, column=1, sticky=tk.W, padx=4)
                if spec.placeholder:
                    entry.insert(0, var.get())
                self.param_widgets[spec.name] = var
            if spec.help:
                ttk.Label(self.params_container, text=spec.help, foreground="#555").grid(row=row, column=2, sticky=tk.W)
            row += 1

    def _choose_file(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if path:
            self.selected_file = path
            self.file_label_var.set(os.path.basename(path))

    def _collect_params(self) -> Dict[str, Any]:
        params = {}
        if not self.current_spec:
            return params
        for spec in self.current_spec.params:
            widget = self.param_widgets.get(spec.name)
            if widget is None:
                continue
            if spec.param_type == "bool":
                val = bool(widget.get())
                if val != spec.default:
                    params[spec.name] = str(val).lower()
            else:
                val = widget.get().strip()
                if val or spec.required:
                    params[spec.name] = val
        return params

    def _send_request(self):
        if not self.current_spec:
            messagebox.showerror("Error", "No endpoint selected")
            return
        if self.current_spec.needs_file and not self.selected_file:
            messagebox.showwarning("File Required", "Please select a PDF file.")
            return
        thread = threading.Thread(target=self._do_request, daemon=True)
        thread.start()

    def _do_request(self):
        spec = self.current_spec
        assert spec is not None
        self._set_status("Sending request...")
        base_url = self.base_url_var.get().rstrip('/')
        url = f"{base_url}{spec.path}"
        params = self._collect_params()
        files = None
        data: Dict[str, Any] = {}

        try:
            if spec.method == "POST":
                if spec.needs_file and self.selected_file:
                    files = {"file": (os.path.basename(self.selected_file), open(self.selected_file, "rb"), "application/pdf")}
                # Distinguish between boolean/text form fields
                data = params
                resp = requests.post(url, files=files, data=data, timeout=3000)
            else:
                resp = requests.get(url, timeout=120)
        except Exception as e:  # broad: we show error to user
            self._append_output(f"Request failed: {e}\n")
            self._set_status("Error")
            if files and "file" in files and not files["file"][1].closed:
                files["file"][1].close()
            return
        finally:
            # Close file handle if used
            if files and "file" in files and not files["file"][1].closed:
                files["file"][1].close()

        self._set_status(f"Status {resp.status_code}")
        ctype = resp.headers.get("Content-Type", "")
        if spec.binary_response or any(x in ctype for x in ["application/zip", "application/pdf"]):
            self._handle_binary_response(resp, spec, ctype)
        else:
            self._handle_textual_response(resp)

    def _handle_textual_response(self, resp: requests.Response):
        try:
            data = resp.json()
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self._append_output(formatted + "\n")
        except ValueError:
            self._append_output(resp.text + "\n")

    def _suggest_extension(self, content_type: str) -> str:
        if "zip" in content_type:
            return ".zip"
        if "pdf" in content_type:
            return ".pdf"
        if "xml" in content_type:
            return ".xml"
        if "json" in content_type:
            return ".json"
        return mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""

    def _handle_binary_response(self, resp: requests.Response, spec: EndpointSpec, content_type: str):
        default_name = "output" + self._suggest_extension(content_type)
        path = filedialog.asksaveasfilename(defaultextension="", initialfile=default_name)
        if not path:
            self._append_output("Save canceled.\n")
            return
        try:
            with open(path, "wb") as f:
                f.write(resp.content)
            self._append_output(f"Saved binary response to {path}\n")
        except OSError as e:
            self._append_output(f"Failed to save file: {e}\n")

    def _clear_output(self):
        self.output_text.delete("1.0", tk.END)

    def _append_output(self, text: str):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def _set_status(self, text: str):
        self.status_var.set(text)


def main():
    print("Launching PDF Layout Analysis GUI client...")
    print("Ensure the backend service is running (e.g., 'make start' in layout-analysis project) at http://localhost:5060")
    print("You can change the Base URL field if the service runs elsewhere.")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
