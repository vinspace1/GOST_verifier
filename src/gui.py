import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List


class VerifierGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Верификатор КД по ГОСТ')
        self.geometry('800x600')

        # Core path frame
        frame_core = tk.Frame(self)
        frame_core.pack(fill='x', padx=8, pady=6)

        tk.Label(frame_core, text='Path to validation core (CLI):').pack(side='left')
        self.entry_core = tk.Entry(frame_core)
        self.entry_core.pack(side='left', fill='x', expand=True, padx=6)
        default_core = os.path.join(os.path.dirname(__file__), 'core_stub.py')
        self.entry_core.insert(0, default_core)
        tk.Button(frame_core, text='Browse', command=self.browse_core).pack(side='left')

        # File selection
        frame_file = tk.Frame(self)
        frame_file.pack(fill='x', padx=8, pady=6)
        tk.Label(frame_file, text='Document to check:').pack(side='left')
        self.entry_file = tk.Entry(frame_file)
        self.entry_file.pack(side='left', fill='x', expand=True, padx=6)
        tk.Button(frame_file, text='Browse', command=self.browse_file).pack(side='left')

        # Controls
        frame_ctrl = tk.Frame(self)
        frame_ctrl.pack(fill='x', padx=8, pady=6)
        tk.Button(frame_ctrl, text='Run Checks', command=self.run_checks).pack(side='left')
        tk.Button(frame_ctrl, text='Export JSON', command=self.export_json).pack(side='left', padx=6)

        # Results
        tk.Label(self, text='Result (JSON):').pack(anchor='w', padx=8)
        self.txt = tk.Text(self, wrap='none')
        self.txt.pack(fill='both', expand=True, padx=8, pady=6)

        self.result = None

    def browse_core(self):
        p = filedialog.askopenfilename(title='Select core executable or script')
        if p:
            self.entry_core.delete(0, tk.END)
            self.entry_core.insert(0, p)

    def browse_file(self):
        p = filedialog.askopenfilename(title='Select document', filetypes=[('PDF files', '*.pdf'), ('Word documents', '*.docx'), ('All files', '*.*')])
        if p:
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, p)

    def run_parsers_for_docx(self, doc_path: str) -> List[str]:
        """Run available parser scripts for the given DOCX and return list of produced JSON paths."""
        # Parsers are in parser/src and we will call their core functions with
        # an absolute path so this works even when the document is on another drive.
        parsers = [
            ('parser/src/get_header_numbers.py', 'header_numbers.json'),
            ('parser/src/get_tables.py', 'tables.json'),
            ('parser/src/get_images.py', 'images.json'),
            ('parser/src/get_content_tree.py', 'content_tree.json'),
        ]

        produced = []
        abs_doc = os.path.abspath(doc_path)

        for relp, outname in parsers:
            abs_p = os.path.join(os.getcwd(), relp)
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location('parser_module', abs_p)
                mod = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(mod)
                except ModuleNotFoundError as me:
                    # Friendly error: missing dependency in parser module
                    msg = (
                        f"Parser requires module '{me.name}' which is not installed.\n"
                        f"Install required packages for this Python executable:\n\n"
                        f"{sys.executable} -m pip install python-docx pillow lxml"
                    )
                    try:
                        messagebox.showerror('Parser error', msg)
                    except Exception:
                        print('Parser error:', msg)
                    return produced

                outpath = os.path.join('parser', 'results', outname)

                # Call parser functions directly when available
                if hasattr(mod, 'build_tree_by_numbering'):
                    tree = mod.build_tree_by_numbering(abs_doc)
                    with open(outpath, 'w', encoding='utf-8') as f:
                        json.dump(tree, f, ensure_ascii=False, indent=2)
                    produced.append(outpath)
                elif hasattr(mod, 'check_tables_captions'):
                    res = mod.check_tables_captions(abs_doc)
                    # if module exposes results_to_dict, use it
                    if hasattr(mod, 'results_to_dict'):
                        payload = mod.results_to_dict(res)
                    else:
                        payload = res
                    with open(outpath, 'w', encoding='utf-8') as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    produced.append(outpath)
                elif hasattr(mod, 'extract_images_to_folder_and_json'):
                    payload = mod.extract_images_to_folder_and_json(abs_doc, json_path=outpath)
                    # function already writes json when called normally, but ensure file exists
                    with open(outpath, 'w', encoding='utf-8') as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    produced.append(outpath)
                elif hasattr(mod, 'split_by_sections_with_nesting_text_numbering'):
                    tree = mod.split_by_sections_with_nesting_text_numbering(abs_doc)
                    with open(outpath, 'w', encoding='utf-8') as f:
                        json.dump(tree, f, ensure_ascii=False, indent=2)
                    produced.append(outpath)
                else:
                    # fallback: try get_results/get_result/get_results
                    if hasattr(mod, 'get_results'):
                        mod.get_results(abs_doc)
                    elif hasattr(mod, 'get_result'):
                        mod.get_result(abs_doc)
                    elif hasattr(mod, 'get_results'):
                        mod.get_results(abs_doc)
                    if os.path.exists(outpath):
                        produced.append(outpath)

            except Exception as e:
                print('Parser', relp, 'failed:', e)

        return produced

    def run_checks(self):
        core = self.entry_core.get().strip()
        doc = self.entry_file.get().strip()
        if not core or not doc:
            messagebox.showwarning('Missing', 'Please set core path and document path')
            return
        # If the selected document is a JSON file, run validators in-process
        # (avoids subprocess import issues and is faster for testing)
        if doc.lower().endswith('.json'):
            try:
                with open(doc, encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                messagebox.showerror('Read error', f'Failed to read JSON: {e}')
                return

            # If parser produced a list (e.g. list of sections), wrap it into dict expected by validators
            if isinstance(data, list):
                data = {"sections": data, "file": os.path.abspath(doc)}

            # Load validators.py relative to this file
            try:
                import importlib.util
                validators_path = os.path.join(os.path.dirname(__file__), 'validators.py')
                spec = importlib.util.spec_from_file_location('validators', validators_path)
                validators = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(validators)
                out = validators.run_all_checks(data)
                self.result = out
                pretty = json.dumps(out, ensure_ascii=False, indent=2)
            except Exception as e:
                messagebox.showerror('Validator error', str(e))
                return

            self.txt.delete('1.0', tk.END)
            self.txt.insert('1.0', pretty)
            return

        # If the selected document is a DOCX file, run parsers first and then
        # run validators against each parser output JSON where applicable.
        if doc.lower().endswith('.docx'):
            try:
                parsed_jsons = self.run_parsers_for_docx(doc)
            except Exception as e:
                messagebox.showerror('Parser error', str(e))
                return

            # load validators and map parser result files to validator functions
            try:
                import importlib.util
                validators_path = os.path.join(os.path.dirname(__file__), 'validators.py')
                spec = importlib.util.spec_from_file_location('validators', validators_path)
                validators = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(validators)
            except Exception as e:
                messagebox.showerror('Validator import error', str(e))
                return

            # mapping from parser result filename to validator function names
            mapping = {
                'header_numbers.json': [validators.check_sections_presence_and_order, validators.check_section_numbering_format],
                'tables.json': [validators.check_tables_format],
                'images.json': [validators.check_figures_format],
                'content_tree.json': [validators.check_sections_presence_and_order, validators.check_section_numbering_format],
            }

            per_file_results = []
            for jpath in parsed_jsons:
                name = os.path.basename(jpath)
                funcs = mapping.get(name)
                if not funcs:
                    continue
                try:
                    with open(jpath, encoding='utf-8') as f:
                        pdata = json.load(f)
                except Exception:
                    continue

                for fn in funcs:
                    try:
                        res = fn(pdata)
                    except Exception as e:
                        res = [{"rule": "internal_error", "message": str(e), "severity": "error"}]
                    per_file_results.append({"source": name, "validator": fn.__name__, "issues": res})

            # Also produce the combined run_all_checks for overall report
            try:
                combined = validators.run_all_checks({'file': doc, 'sections': []})
            except Exception:
                combined = {}

            out = {'per_file': per_file_results, 'combined': combined}
            pretty = json.dumps(out, ensure_ascii=False, indent=2)
            self.txt.delete('1.0', tk.END)
            self.txt.insert('1.0', pretty)
            self.result = out
            return

        # Fallback: execute core as external process
        if core.lower().endswith('.py'):
            cmd = [sys.executable, core, doc]
        else:
            cmd = [core, doc]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
        except Exception as e:
            messagebox.showerror('Run error', str(e))
            return

        if proc.returncode != 0:
            messagebox.showwarning('Core returned error', proc.stderr[:1000] or 'Non-zero exit code')

        try:
            self.result = json.loads(proc.stdout)
            pretty = json.dumps(self.result, ensure_ascii=False, indent=2)
        except Exception:
            # If output is not JSON, show raw stdout
            pretty = proc.stdout
            self.result = None

        self.txt.delete('1.0', tk.END)
        self.txt.insert('1.0', pretty)

    def export_json(self):
        if not self.result:
            messagebox.showwarning('No data', 'No parsed JSON result available to export')
            return
        p = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if not p:
            return
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(self.result, f, ensure_ascii=False, indent=2)
        messagebox.showinfo('Saved', f'JSON saved to {p}')


def main():
    app = VerifierGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
