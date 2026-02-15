from __future__ import annotations

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from core.config_loader import ConfigError
from core.default_configs import restore_default_configs
from core.version import APP_NAME, APP_VERSION
from main import run_vattool


def _base_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def _default_output_root() -> Path:
    documents = Path.home() / "Documents"
    if documents.exists() and documents.is_dir():
        return documents / "vattool_19"
    return Path.home() / "vattool_19"


def _open_output_folder(path: str) -> None:
    if os.name == "nt":
        os.startfile(path)


class VATToolUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.app_title = f"{APP_NAME} v{APP_VERSION}"
        self.root.title(self.app_title)

        self.input_csv_var = tk.StringVar()
        self.output_root_var = tk.StringVar(value=str(_default_output_root()))
        self.submitter_person_var = tk.StringVar()
        self.submitter_egn_var = tk.StringVar()

        self._build_layout()

    def _build_layout(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.grid(row=0, column=0, sticky="nsew")

        tk.Label(frame, text=self.app_title).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        tk.Label(frame, text="Input ledger CSV:").grid(row=1, column=0, sticky="w", pady=(0, 6))
        tk.Entry(frame, textvariable=self.input_csv_var, width=60).grid(row=2, column=0, sticky="we", padx=(0, 8))
        tk.Button(frame, text="Browse...", command=self._browse_input).grid(row=2, column=1, sticky="e")

        tk.Label(frame, text="Output root folder:").grid(row=3, column=0, sticky="w", pady=(10, 6))
        tk.Entry(frame, textvariable=self.output_root_var, width=60).grid(row=4, column=0, sticky="we", padx=(0, 8))
        tk.Button(frame, text="Browse...", command=self._browse_output).grid(row=4, column=1, sticky="e")

        tk.Label(frame, text="Submitter person (optional):").grid(row=5, column=0, sticky="w", pady=(10, 6))
        tk.Entry(frame, textvariable=self.submitter_person_var, width=60).grid(row=6, column=0, columnspan=2, sticky="we")

        tk.Label(frame, text="Submitter EGN (optional):").grid(row=7, column=0, sticky="w", pady=(10, 6))
        tk.Entry(frame, textvariable=self.submitter_egn_var, width=60).grid(row=8, column=0, columnspan=2, sticky="we")

        tk.Button(frame, text="Run", command=self._run).grid(row=9, column=0, columnspan=2, pady=(14, 0), sticky="we")

        frame.columnconfigure(0, weight=1)

    def _browse_input(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select ledger CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.input_csv_var.set(selected)

    def _browse_output(self) -> None:
        selected = filedialog.askdirectory(title="Select output root folder")
        if selected:
            self.output_root_var.set(selected)

    def _run(self) -> None:
        input_csv = self.input_csv_var.get().strip()
        output_root = self.output_root_var.get().strip()
        submitter_person = self.submitter_person_var.get().strip()
        submitter_egn = self.submitter_egn_var.get().strip()

        if not input_csv or not Path(input_csv).exists():
            messagebox.showerror("VATTool v19", "Please choose a valid input ledger CSV file.")
            return

        if not output_root:
            messagebox.showerror("VATTool v19", "Please choose a valid output root folder.")
            return

        try:
            output_dir, warnings_count = self._run_with_config_recovery(
                input_csv=input_csv,
                output_root=output_root,
                submitter_person=submitter_person,
                submitter_egn=submitter_egn,
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("VATTool v19", f"Run failed:\n{exc}")
            return

        warning_text = "Warnings: YES (see run_summary.txt)" if warnings_count > 0 else "Warnings: NO"
        open_folder = messagebox.askyesno(
            "VATTool v19",
            f"Completed successfully.\n{warning_text}\n\nOpen output folder?",
        )
        if open_folder:
            _open_output_folder(output_dir)

    def _run_with_config_recovery(
        self,
        input_csv: str,
        output_root: str,
        submitter_person: str,
        submitter_egn: str,
    ) -> tuple[str, int]:
        try:
            return run_vattool(
                input_csv=input_csv,
                output_root=output_root,
                submitter_person=submitter_person,
                submitter_egn=submitter_egn,
            )
        except ConfigError as exc:
            should_restore = messagebox.askyesno(
                "VATTool v19",
                f"Config error:\n{exc}\n\nRestore default configs and retry?",
            )
            if not should_restore:
                raise

            restore_default_configs(str(_base_dir()))
            return run_vattool(
                input_csv=input_csv,
                output_root=output_root,
                submitter_person=submitter_person,
                submitter_egn=submitter_egn,
            )


def main() -> None:
    root = tk.Tk()
    VATToolUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
