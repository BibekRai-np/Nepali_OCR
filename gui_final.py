import asyncio
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import io
import os
from chrome_lens_py import LensAPI

# Optional docx support
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# ---------- Theme Configurations ----------
THEMES = {
    "light": {
        "bg_main": "#F4F7FF", "card_bg": "#FFFFFF", "text": "#2C3E50",
        "sub_text": "#6B7280", "border": "#D1D8E0", "textarea": "#F9FAFB"
    },
    "dark": {
        "bg_main": "#1A1B1E", "card_bg": "#25262B", "text": "#E9ECEF",
        "sub_text": "#A1A1AA", "border": "#373A40", "textarea": "#2C2E33"
    }
}
ACCENT_BLUE = "#5C7CFA"
NEPALI_RED = "#E63946"
DISABLED_FG = "#A5AABF"

# ---------- Async OCR Logic ----------
async def ocr_image(image_bytes):
    api = LensAPI()
    try:
        result = await api.process_image(image_path=image_bytes, output_format='text')
        return result.get("ocr_text", "No text detected.")
    except Exception as e:
        return f"Error: {str(e)}"

# ---------- Main Application ----------
class NepaliOCRUpgrade:
    def __init__(self, root):
        self.root = root
        self.root.title("नेपाली OCR CONVERTER")
        self.root.geometry("1200x800")   # initial size, but user can resize
        self.root.minsize(800, 600)       # prevent collapse

        self.mode = "light"
        self.image_data = None
        self.photo = None
        self.current_zoom = 12

        self.setup_styles()
        self.create_layout()
        self.apply_theme()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("Action.TButton", font=("Poppins", 10, "bold"), padding=10, borderwidth=0)
        self.style.map("Action.TButton", 
                       background=[('active', '#4263EB'), ('!disabled', ACCENT_BLUE), ('disabled', '#E0E7FF')],
                       foreground=[('disabled', DISABLED_FG), ('!disabled', 'white')])
        
        self.style.configure("Tool.TButton", font=("Poppins", 8), padding=4, borderwidth=0)
        self.style.map("Tool.TButton",
                       background=[('active', '#E2E8F0'), ('!disabled', '#EFF3F8')],
                       foreground=[('!disabled', '#2C3E50')])

    def create_layout(self):
        # Use grid for root to keep credit at bottom
        self.root.grid_rowconfigure(0, weight=0)   # header
        self.root.grid_rowconfigure(1, weight=1)   # main container
        self.root.grid_rowconfigure(2, weight=0)   # credit
        self.root.grid_columnconfigure(0, weight=1)

        # --- Header Section (row 0) ---
        self.header = tk.Frame(self.root)
        self.header.grid(row=0, column=0, sticky="ew", pady=(10, 0))

        self.title_frame = tk.Frame(self.header)
        self.title_frame.pack()
        self.lbl_nep = tk.Label(self.title_frame, text="नेपाली", font=("Poppins", 32, "bold"), fg=NEPALI_RED)
        self.lbl_nep.pack(side=tk.LEFT)
        self.lbl_ocr = tk.Label(self.title_frame, text=" OCR CONVERTER", font=("Poppins", 32, "bold"))
        self.lbl_ocr.pack(side=tk.LEFT)

        self.lbl_slogan = tk.Label(self.header, text="नेपालीको लागि, नेपाली हस्तलेखनकै लागि बनेको पहिलो पावरफुल OCR", font=("Poppins", 11))
        self.lbl_slogan.pack(pady=2)

        self.btn_theme = ttk.Button(self.header, text="⚫ Dark Mode", command=self.toggle_theme)
        self.btn_theme.pack(pady=2)

        # --- Main Split Container (row 1) ---
        self.main_container = tk.Frame(self.root)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=4)
        self.main_container.grid_columnconfigure(1, weight=6)

        left_side = tk.Frame(self.main_container)
        left_side.grid(row=0, column=0, sticky="nsew", padx=5)

        right_side = tk.Frame(self.main_container)
        right_side.grid(row=0, column=1, sticky="nsew", padx=5)

        # --- LEFT CARD (Upload) ---
        self.input_card = tk.Frame(left_side, highlightthickness=1)
        self.input_card.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.lbl_step1 = tk.Label(self.input_card, text="1. UPLOAD IMAGE", font=("Poppins", 11, "bold"))
        self.lbl_step1.pack(pady=10)

        img_outer = tk.Frame(self.input_card)
        img_outer.pack(expand=True, fill=tk.BOTH, padx=20, pady=5)
        
        self.img_canvas = tk.Canvas(img_outer, highlightthickness=0)
        self.img_vbar = ttk.Scrollbar(img_outer, orient="vertical", command=self.img_canvas.yview)
        self.img_scroll_window = tk.Frame(self.img_canvas)
        
        self.img_canvas.create_window((0, 0), window=self.img_scroll_window, anchor="nw", width=380)
        self.img_canvas.configure(yscrollcommand=self.img_vbar.set)
        
        self.img_canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.img_vbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.img_display = tk.Label(self.img_scroll_window, text="No Image Selected")
        self.img_display.pack(expand=True, fill=tk.BOTH, pady=100)

        input_btn_frame = tk.Frame(self.input_card)
        input_btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=25, pady=20)
        self.btn_upload = ttk.Button(input_btn_frame, text="Browse Image +", style="Action.TButton", command=self.load_image)
        self.btn_upload.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.btn_gen = ttk.Button(input_btn_frame, text="Generate ⚡", style="Action.TButton", command=self.process_image, state=tk.DISABLED)
        self.btn_gen.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        # --- RIGHT CARD (Result) ---
        self.result_card = tk.Frame(right_side, highlightthickness=1)
        self.result_card.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.result_card.grid_rowconfigure(0, weight=0)
        self.result_card.grid_rowconfigure(1, weight=0)
        self.result_card.grid_rowconfigure(2, weight=1)
        self.result_card.grid_rowconfigure(3, weight=0)
        self.result_card.grid_columnconfigure(0, weight=1)

        self.lbl_step2 = tk.Label(self.result_card, text="2. RESULT", font=("Poppins", 11, "bold"))
        self.lbl_step2.grid(row=0, column=0, sticky="n", pady=(15, 5))

        self.tool_bar = tk.Frame(self.result_card)
        self.tool_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        self.btn_remove_enter = ttk.Button(self.tool_bar, text="Remove Enter ↵", style="Tool.TButton", command=self.remove_enter)
        self.btn_remove_enter.pack(side=tk.LEFT, padx=2)
        self.btn_zoom_plus = ttk.Button(self.tool_bar, text="Zoom +", style="Tool.TButton", command=lambda: self.adjust_zoom(1))
        self.btn_zoom_plus.pack(side=tk.LEFT, padx=2)
        self.btn_zoom_minus = ttk.Button(self.tool_bar, text="Zoom -", style="Tool.TButton", command=lambda: self.adjust_zoom(-1))
        self.btn_zoom_minus.pack(side=tk.LEFT, padx=2)

        txt_frame = tk.Frame(self.result_card)
        txt_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        txt_frame.grid_rowconfigure(0, weight=1)
        txt_frame.grid_columnconfigure(0, weight=1)

        self.text_output = tk.Text(txt_frame, font=("Noto Sans Devanagari", self.current_zoom), relief=tk.FLAT, padx=15, pady=15)
        self.txt_vbar = ttk.Scrollbar(txt_frame, orient="vertical", command=self.text_output.yview)
        self.text_output.configure(yscrollcommand=self.txt_vbar.set)
        self.text_output.grid(row=0, column=0, sticky="nsew")
        self.txt_vbar.grid(row=0, column=1, sticky="ns")

        self.footer_actions = tk.Frame(self.result_card)
        self.footer_actions.grid(row=3, column=0, sticky="ew", padx=20, pady=20)
        self.footer_actions.columnconfigure(0, weight=1)
        self.footer_actions.columnconfigure(1, weight=1)
        self.footer_actions.columnconfigure(2, weight=1)

        self.btn_copy = ttk.Button(self.footer_actions, text="Copy", style="Action.TButton", command=self.copy_to_clipboard, state=tk.DISABLED)
        self.btn_copy.grid(row=0, column=0, padx=5, sticky="ew")
        self.btn_docx = ttk.Button(self.footer_actions, text="Save .docx", style="Action.TButton", command=self.save_as_docx, state=tk.DISABLED)
        self.btn_docx.grid(row=0, column=1, padx=5, sticky="ew")
        self.btn_txt = ttk.Button(self.footer_actions, text="Save .txt", style="Action.TButton", command=self.save_as_txt, state=tk.DISABLED)
        self.btn_txt.grid(row=0, column=2, padx=5, sticky="ew")

        # --- Credit Label (row 2) ---
        self.lbl_dev = tk.Label(self.root, text="●  For Personal Use Only  ●  Developed by Bibek Rai | All rights reserved © 2026", font=("Inter", 9))
        self.lbl_dev.grid(row=2, column=0, sticky="s", pady=(0, 10))

    # ---------- Theme & Logic ----------
    def toggle_theme(self):
        self.mode = "dark" if self.mode == "light" else "light"
        self.btn_theme.config(text="☀️ Light Mode" if self.mode == "dark" else "⚫ Dark Mode")
        self.apply_theme()

    def apply_theme(self):
        c = THEMES[self.mode]
        self.root.configure(bg=c["bg_main"])
        for widget in [self.header, self.title_frame, self.lbl_nep, self.main_container]:
            widget.configure(bg=c["bg_main"])
        
        self.lbl_ocr.configure(bg=c["bg_main"], fg=c["text"])
        self.lbl_slogan.configure(bg=c["bg_main"], fg=c["sub_text"])
        self.lbl_dev.configure(bg=c["bg_main"], fg=c["sub_text"])
        
        self.input_card.configure(bg=c["card_bg"], highlightbackground=c["border"])
        self.result_card.configure(bg=c["card_bg"], highlightbackground=c["border"])
        self.lbl_step1.configure(bg=c["card_bg"], fg=c["text"])
        self.lbl_step2.configure(bg=c["card_bg"], fg=c["text"])

        self.img_canvas.configure(bg=c["textarea"])
        self.img_scroll_window.configure(bg=c["textarea"])
        self.img_display.configure(bg=c["textarea"], fg=c["sub_text"])
        
        self.tool_bar.configure(bg=c["card_bg"])
        self.text_output.configure(bg=c["textarea"], fg=c["text"], insertbackground=c["text"])
        self.footer_actions.configure(bg=c["card_bg"])

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if file_path:
            with open(file_path, 'rb') as f: self.image_data = f.read()
            img = Image.open(io.BytesIO(self.image_data))
            
            target_w = 360
            ratio = target_w / float(img.size[0])
            target_h = int(float(img.size[1]) * ratio)
            
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            self.img_display.config(image=self.photo, text="")
            self.img_display.pack(pady=10)
            
            self.img_scroll_window.update_idletasks()
            self.img_canvas.config(scrollregion=self.img_canvas.bbox("all"))
            self.btn_gen.config(state=tk.NORMAL)

    def process_image(self):
        self.btn_gen.config(state=tk.DISABLED)
        self.text_output.delete(1.0, tk.END)
        self.text_output.insert(tk.END, "परिवर्तन भइरहेको छ...")
        threading.Thread(target=self.run_async_ocr, daemon=True).start()

    def run_async_ocr(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ocr_image(self.image_data))
        self.root.after(0, self.on_complete, result)

    def on_complete(self, text):
        self.text_output.delete(1.0, tk.END)
        self.text_output.insert(tk.END, text)
        self.btn_gen.config(state=tk.NORMAL)
        for btn in [self.btn_copy, self.btn_docx, self.btn_txt]:
            btn.config(state=tk.NORMAL)

    def adjust_zoom(self, delta):
        self.current_zoom += delta
        if self.current_zoom < 8:
            self.current_zoom = 8
        elif self.current_zoom > 24:
            self.current_zoom = 24
        self.text_output.configure(font=("Noto Sans Devanagari", self.current_zoom))

    def remove_enter(self):
        content = self.text_output.get(1.0, tk.END).strip()
        cleaned = " ".join(content.splitlines())
        self.text_output.delete(1.0, tk.END)
        self.text_output.insert(tk.END, cleaned)

    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text_output.get(1.0, tk.END).strip())
        messagebox.showinfo("Success", "Copied to clipboard!")

    def save_as_txt(self):
        text = self.text_output.get(1.0, tk.END).strip()
        if not text or text == "परिवर्तन भइरहेको छ..." or text.startswith("Error"):
            messagebox.showinfo("No text", "There is no valid extracted text to save.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="Result_OCR.txt"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                messagebox.showinfo("Success", f"Text saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")

    def save_as_docx(self):
        if not DOCX_AVAILABLE:
            messagebox.showerror("Missing Library", 
                "python-docx is not installed. Please install it with:\npip install python-docx")
            return
        text = self.text_output.get(1.0, tk.END).strip()
        if not text or text == "प्रक्रिया भइरहेको छ..." or text.startswith("Error"):
            messagebox.showinfo("No text", "There is no valid extracted text to save.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")],
            initialfile="Result_OCR.docx"
        )
        if file_path:
            try:
                doc = Document()
                doc.add_paragraph(text)
                doc.save(file_path)
                messagebox.showinfo("Success", f"Text saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save document:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NepaliOCRUpgrade(root)
    root.mainloop()