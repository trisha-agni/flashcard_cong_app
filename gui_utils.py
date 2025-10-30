import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox
from ttkbootstrap.constants import *
from fc_utils import FlashcardManager
from ai_utils import AIChatbot
from test_gen_utils import TestGenerator
from test_stats import TestStats # newwwwwwwwwwwwwww


class FlashcardGUI:
    def __init__(self, manager: FlashcardManager):
        self.manager = manager
        self.ai = AIChatbot()
        self.test_gen = TestGenerator(manager)
        self._stats = TestStats()

        # Themed Window
        self.root = ttk.Window(title="Flashify", themename="minty")
        self.root.state("zoomed")

        # Main Canvas
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0, bg="white")
        self.bg_canvas.pack(fill="both", expand=True)

        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()

        # Red horizontal line near top (flashcard style)
        top_line_y = int(height * 0.1)
        self.bg_canvas.create_line(20, top_line_y, width - 20, top_line_y, fill="red", width=2)

        # Middle section: faint blue horizontal lines for ruled effect
        middle_top = top_line_y + 20
        middle_bottom = height - 100  # leave bottom margin
        for y in range(middle_top, middle_bottom, 30):
            self.bg_canvas.create_line(20, y, width - 20, y, fill="#add8e6")  # light blue lines

        # Center Frame for listboxes, entry, and buttons
        self.center_frame = ttk.Frame(self.bg_canvas, style="Card.TFrame")
        self.bg_canvas.create_window(width // 2, height // 2, window=self.center_frame, anchor="center")

        # Make the grid expand properly
        self.center_frame.columnconfigure(0, weight=1)
        self.center_frame.columnconfigure(1, weight=1)

        # Listbox labels
        flashcard_label = ttk.Label(self.center_frame, text="Flashcards", bootstyle="primary")
        flashcard_label.grid(row=0, column=0, pady=(0, 5), sticky="n")

        term_label = ttk.Label(self.center_frame, text="Terms", bootstyle="primary")
        term_label.grid(row=0, column=1, pady=(0, 5), sticky="n")

        # Flashcard List
        self.flashcard_list = tk.Listbox(
            self.center_frame,
            selectmode="browse",
            exportselection=False,
            bg="white",
            borderwidth=1,
            relief="solid",
            width=25,
            height=20,
            font=("Helvetica", 14)
        )
        self.flashcard_list.grid(row=0, column=0, padx=20, pady=20)
        self.flashcard_list.bind("<<ListboxSelect>>", self._on_flashcard_select)

        # Term List
        self.term_list = tk.Listbox(
            self.center_frame,
            selectmode="browse",
            exportselection=False,
            bg="white",
            borderwidth=1,
            relief="solid",
            width=50,
            height=20,
            font=("Comic Sans MS", 14)
        )
        self.term_list.grid(row=0, column=1, padx=20, pady=20)
        self.term_list.bind("<Double-Button-1>", lambda e: self.explain_term())

        # Entry Field
        self.entry = ttk.Entry(self.center_frame, bootstyle="info", width=80)
        self.entry.grid(row=1, column=0, columnspan=2, pady=10)

        # Buttons
        button_frame = ttk.Frame(self.center_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Create Flashcard", bootstyle=PRIMARY,
                   command=self.create_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Flashcard", bootstyle=DANGER,
                   command=self.delete_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Add Term", bootstyle=PRIMARY,
                   command=self.add_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Term", bootstyle=DANGER,
                   command=self.delete_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Explain Term", bootstyle=INFO,
                   command=self.explain_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Generate Test", bootstyle=SECONDARY,
                   command=self._generate_test_for_selected).pack(side="left", padx=5)
        ttk.Button(button_frame, text="View Test Stats", bootstyle=INFO,
                   command=self._show_stats).pack(side="left", padx=5)

        self._update_flashcard_list()

    # Flashcard Methods
    def create_flashcard(self):
        name = self.entry.get().strip()
        if name:
            self.manager.add_flashcard(name)
            self.manager.save()
            self._update_flashcard_list()
            self.entry.delete(0, "end")

    def delete_flashcard(self):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self.manager.flashcards = [fc for fc in self.manager.flashcards if fc["name"] != name]
            self.manager.save()
            self._update_flashcard_list()

    # Term Methods
    def add_term(self):
        selection = self.flashcard_list.curselection()
        if selection:
            card_name = self.flashcard_list.get(selection[0])
            term = self.entry.get().strip()
            if term:
                self.manager.add_term(card_name, term)
                self.manager.save()
                self._update_term_list(card_name)
                self.entry.delete(0, "end")

    def delete_term(self):
        card_sel = self.flashcard_list.curselection()
        term_sel = self.term_list.curselection()
        if card_sel and term_sel:
            card_name = self.flashcard_list.get(card_sel[0])
            term = self.term_list.get(term_sel[0])
            self.manager.delete_term(card_name, term)
            self.manager.save()
            self._update_term_list(card_name)

    def explain_term(self):
        term_sel = self.term_list.curselection()
        if not term_sel:
            ttk.messagebox.showwarning("Warning", "Please select a term to explain.")
            return

        term = self.term_list.get(term_sel[0])
        explanation = self.ai.explain_term(term)

        popup = ttk.Toplevel(self.root)
        popup.title(f"Explanation for {term}")
        msg = tk.Message(popup, text=explanation, width=500)
        msg.pack(padx=10, pady=10)

    # Generate Test
    def _generate_test_for_selected(self):
        selection = self.flashcard_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a flashcard first.")
            return

        card_name = self.flashcard_list.get(selection[0])
        selected_card = self.manager.get_flashcard(card_name)

        if not selected_card:
            messagebox.showerror("Error", f"Flashcard '{card_name}' not found.")
            return

        # Open the test configuration popup
        self.test_gen.open_test_config(self.root, selected_card)
    
    def _show_stats(self):
        try:
            # opens the score-over-time plot window (uses TestStats)
            self._stats.plot_score_over_time(parent=self.root)
        except Exception as e:
            messagebox.showerror("Stats Error", f"Could not show stats:\n{e}")

    # Update UI
    def _update_flashcard_list(self):
        self.flashcard_list.delete(0, "end")
        for name in self.manager.get_flashcard_names():
            self.flashcard_list.insert("end", name)

    def _update_term_list(self, card_name):
        self.term_list.delete(0, "end")
        card = self.manager.get_flashcard(card_name)
        if card:
            for term in card["terms"]:
                self.term_list.insert("end", term)

    # Event Handlers
    def _on_flashcard_select(self, event):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self._update_term_list(name)

    # Main Loop
    def run(self):
        self.root.mainloop()


'''import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox
from ttkbootstrap.constants import *
from fc_utils import FlashcardManager
from ai_utils import AIChatbot
from test_gen_utils import TestGenerator
from test_stats import TestStats # newwwwwwwwwwwwwww


class FlashcardGUI:
    def __init__(self, manager: FlashcardManager):
        self.manager = manager
        self.ai = AIChatbot()
        self.test_gen = TestGenerator(manager)
        self._stats = TestStats()  # newwwwwwwwwwwwwww

        # Themed Window
        self.root = ttk.Window(title="Flashify", themename="minty")
        self.root.state("zoomed")

        # Flashcard List
        self.flashcard_list = tk.Listbox(self.root, selectmode="browse", exportselection=False)
        self.flashcard_list.pack(side="left", fill="y", padx=10, pady=10)
        self.flashcard_list.bind("<<ListboxSelect>>", self._on_flashcard_select)

        # Term List
        self.term_list = tk.Listbox(self.root, selectmode="browse", exportselection=False)
        self.term_list.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.term_list.bind("<Double-Button-1>", lambda e: self.explain_term())

        # Entry Field
        self.entry = ttk.Entry(self.root, bootstyle="info")
        self.entry.pack(fill="x", padx=10, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Create Flashcard", bootstyle=PRIMARY, command=self.create_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Flashcard", bootstyle=DANGER, command=self.delete_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Add Term", bootstyle=PRIMARY, command=self.add_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Term", bootstyle=DANGER, command=self.delete_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Explain Term", bootstyle=INFO, command=self.explain_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Generate Test", bootstyle=SECONDARY, command=self._generate_test_for_selected).pack(side="left", padx=5)
        ttk.Button(button_frame, text="View Test Stats", bootstyle=INFO, command=self._show_stats).pack(side="left", padx=5)
        self._update_flashcard_list()

    # Flashcard Methods
    def create_flashcard(self):
        name = self.entry.get().strip()
        if name:
            self.manager.add_flashcard(name)
            self.manager.save()
            self._update_flashcard_list()
            self.entry.delete(0, "end")

    def delete_flashcard(self):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self.manager.flashcards = [fc for fc in self.manager.flashcards if fc["name"] != name]
            self.manager.save()
            self._update_flashcard_list()

    # Term Methods
    def add_term(self):
        selection = self.flashcard_list.curselection()
        if selection:
            card_name = self.flashcard_list.get(selection[0])
            term = self.entry.get().strip()
            if term:
                self.manager.add_term(card_name, term)
                self.manager.save()
                self._update_term_list(card_name)
                self.entry.delete(0, "end")

    def delete_term(self):
        card_sel = self.flashcard_list.curselection()
        term_sel = self.term_list.curselection()
        if card_sel and term_sel:
            card_name = self.flashcard_list.get(card_sel[0])
            term = self.term_list.get(term_sel[0])
            self.manager.delete_term(card_name, term)
            self.manager.save()
            self._update_term_list(card_name)

    def explain_term(self):
        term_sel = self.term_list.curselection()
        if not term_sel:
            ttk.messagebox.showwarning("Warning", "Please select a term to explain.")
            return

        term = self.term_list.get(term_sel[0])
        explanation = self.ai.explain_term(term)

        popup = ttk.Toplevel(self.root)
        popup.title(f"Explanation for {term}")
        msg = tk.Message(popup, text=explanation, width=500)
        msg.pack(padx=10, pady=10)

    # Generate Test
    def _generate_test_for_selected(self):
        selection = self.flashcard_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a flashcard first.")
            return

        card_name = self.flashcard_list.get(selection[0])
        selected_card = self.manager.get_flashcard(card_name)

        if not selected_card:
            messagebox.showerror("Error", f"Flashcard '{card_name}' not found.")
            return

        # Open the test configuration popup
        self.test_gen.open_test_config(self.root, selected_card)
    
    def _show_stats(self):
        try:
            # opens the score-over-time plot window (uses TestStats)
            self._stats.plot_score_over_time(parent=self.root)
        except Exception as e:
            messagebox.showerror("Stats Error", f"Could not show stats:\n{e}")

    # Update UI
    def _update_flashcard_list(self):
        self.flashcard_list.delete(0, "end")
        for name in self.manager.get_flashcard_names():
            self.flashcard_list.insert("end", name)

    def _update_term_list(self, card_name):
        self.term_list.delete(0, "end")
        card = self.manager.get_flashcard(card_name)
        if card:
            for term in card["terms"]:
                self.term_list.insert("end", term)

    # Event Handlers
    def _on_flashcard_select(self, event):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self._update_term_list(name)

    # Main Loop
    def run(self):
        self.root.mainloop()'''

'''import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox
from ttkbootstrap.constants import *
from fc_utils import FlashcardManager
from ai_utils import AIChatbot
from test_gen_utils import TestGenerator


class FlashcardGUI:
    def __init__(self, manager: FlashcardManager):
        self.manager = manager
        self.ai = AIChatbot()
        self.test_gen = TestGenerator(manager)

        # Themed Window
        self.root = ttk.Window(title="Flashcard App", themename="minty")
        self.root.geometry("600x400")

        # Flashcard List
        self.flashcard_list = tk.Listbox(self.root, selectmode="browse", exportselection=False)
        self.flashcard_list.pack(side="left", fill="y", padx=10, pady=10)
        self.flashcard_list.bind("<<ListboxSelect>>", self._on_flashcard_select)

        # Term List
        self.term_list = tk.Listbox(self.root, selectmode="browse", exportselection=False)
        self.term_list.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.term_list.bind("<Double-Button-1>", lambda e: self.explain_term())

        # Entry Field
        self.entry = ttk.Entry(self.root, bootstyle="info")
        self.entry.pack(fill="x", padx=10, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Create Flashcard", bootstyle=PRIMARY, command=self.create_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Flashcard", bootstyle=DANGER, command=self.delete_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Add Term", bootstyle=PRIMARY, command=self.add_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Term", bootstyle=DANGER, command=self.delete_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Explain Term", bootstyle=INFO, command=self.explain_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Generate Test", bootstyle=SECONDARY, command=self._generate_test_for_selected).pack(side="left", padx=5)

        self._update_flashcard_list()

    # Flashcard Methods
    def create_flashcard(self):
        name = self.entry.get().strip()
        if name:
            self.manager.add_flashcard(name)
            self.manager.save()
            self._update_flashcard_list()
            self.entry.delete(0, "end")

    def delete_flashcard(self):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self.manager.flashcards = [fc for fc in self.manager.flashcards if fc["name"] != name]
            self.manager.save()
            self._update_flashcard_list()

    # Term Methods
    def add_term(self):
        selection = self.flashcard_list.curselection()
        if selection:
            card_name = self.flashcard_list.get(selection[0])
            term = self.entry.get().strip()
            if term:
                self.manager.add_term(card_name, term)
                self.manager.save()
                self._update_term_list(card_name)
                self.entry.delete(0, "end")

    def delete_term(self):
        card_sel = self.flashcard_list.curselection()
        term_sel = self.term_list.curselection()
        if card_sel and term_sel:
            card_name = self.flashcard_list.get(card_sel[0])
            term = self.term_list.get(term_sel[0])
            self.manager.delete_term(card_name, term)
            self.manager.save()
            self._update_term_list(card_name)

    def explain_term(self):
        term_sel = self.term_list.curselection()
        if not term_sel:
            ttk.messagebox.showwarning("Warning", "Please select a term to explain.")
            return

        term = self.term_list.get(term_sel[0])
        explanation = self.ai.explain_term(term)

        popup = ttk.Toplevel(self.root)
        popup.title(f"Explanation for {term}")
        msg = tk.Message(popup, text=explanation, width=500)
        msg.pack(padx=10, pady=10)

    # Generate Test
    def _generate_test_for_selected(self):
        selection = self.flashcard_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a flashcard first.")
            return

        card_name = self.flashcard_list.get(selection[0])
        selected_card = self.manager.get_flashcard(card_name)

        if not selected_card:
            messagebox.showerror("Error", f"Flashcard '{card_name}' not found.")
            return

        # Open the test configuration popup
        self.test_gen.open_test_config(self.root, selected_card)

    # Update UI
    def _update_flashcard_list(self):
        self.flashcard_list.delete(0, "end")
        for name in self.manager.get_flashcard_names():
            self.flashcard_list.insert("end", name)

    def _update_term_list(self, card_name):
        self.term_list.delete(0, "end")
        card = self.manager.get_flashcard(card_name)
        if card:
            for term in card["terms"]:
                self.term_list.insert("end", term)

    # Event Handlers
    def _on_flashcard_select(self, event):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self._update_term_list(name)

    # Main Loop
    def run(self):
        self.root.mainloop()'''


'''import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox
from ttkbootstrap.constants import *
from fc_utils import FlashcardManager
from ai_utils import AIChatbot
from test_gen_utils import TestGenerator

class FlashcardGUI:
    def __init__(self, manager: FlashcardManager):
        self.manager = manager
        self.ai = AIChatbot()
        self.test_gen = TestGenerator(manager)

        # Themed Window
        self.root = ttk.Window(title="Flashcard App", themename="minty")
        self.root.geometry("600x400")

        # Flashcard List
        self.flashcard_list = tk.Listbox(self.root, selectmode="browse", exportselection=False)
        self.flashcard_list.pack(side="left", fill="y", padx=10, pady=10)
        self.flashcard_list.bind("<<ListboxSelect>>", self._on_flashcard_select)

        # Term List
        self.term_list = tk.Listbox(self.root, selectmode="browse", exportselection=False)
        self.term_list.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.term_list.bind("<Double-Button-1>", lambda e: self.explain_term())

        # Entry Field
        self.entry = ttk.Entry(self.root, bootstyle="info")
        self.entry.pack(fill="x", padx=10, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Create Flashcard", bootstyle=PRIMARY, command=self.create_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Flashcard", bootstyle=DANGER, command=self.delete_flashcard).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Add Term", bootstyle=PRIMARY, command=self.add_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Term", bootstyle=DANGER, command=self.delete_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Explain Term", bootstyle=INFO, command=self.explain_term).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Generate Test", bootstyle=SECONDARY, command=lambda: self._generate_test_for_selected()).pack(side="left", padx=5)

        self._update_flashcard_list()

    # Flashcard Methods
    def create_flashcard(self):
        name = self.entry.get().strip()
        if name:
            self.manager.add_flashcard(name)
            self.manager.save()
            self._update_flashcard_list()
            self.entry.delete(0, "end")

    def delete_flashcard(self):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self.manager.flashcards = [fc for fc in self.manager.flashcards if fc["name"] != name]
            self.manager.save()
            self._update_flashcard_list()

    # Term Methods
    def add_term(self):
        selection = self.flashcard_list.curselection()
        if selection:
            card_name = self.flashcard_list.get(selection[0])
            term = self.entry.get().strip()
            if term:
                self.manager.add_term(card_name, term)
                self.manager.save()
                self._update_term_list(card_name)
                self.entry.delete(0, "end")

    def delete_term(self):
        card_sel = self.flashcard_list.curselection()
        term_sel = self.term_list.curselection()
        if card_sel and term_sel:
            card_name = self.flashcard_list.get(card_sel[0])
            term = self.term_list.get(term_sel[0])
            self.manager.delete_term(card_name, term)
            self.manager.save()
            self._update_term_list(card_name)

    def explain_term(self):
        term_sel = self.term_list.curselection()
        if not term_sel:
            ttk.messagebox.showwarning("Warning", "Please select a term to explain.")
            return

        term = self.term_list.get(term_sel[0])
        explanation = self.ai.explain_term(term)

        popup = ttk.Toplevel(self.root)
        popup.title(f"Explanation for {term}")
        msg = tk.Message(popup, text=explanation, width=500)
        msg.pack(padx=10, pady=10)

    def _generate_test_for_selected(self):
        selection = self.flashcard_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a flashcard first.")
            return

        # Get the selected card name
        card_name = self.flashcard_list.get(selection[0])

        # Retrieve the full flashcard dictionary
        selected_card = self.manager.get_flashcard(card_name)

        if not selected_card:
            messagebox.showerror("Error", f"Flashcard '{card_name}' not found.")
            return

        # Pass the dictionary, not the string name
        self.test_gen.open_test_config(self.root, selected_card)

    # Update UI
    def _update_flashcard_list(self):
        self.flashcard_list.delete(0, "end")
        for name in self.manager.get_flashcard_names():
            self.flashcard_list.insert("end", name)

    def _update_term_list(self, card_name):
        self.term_list.delete(0, "end")
        card = self.manager.get_flashcard(card_name)
        if card:
            for term in card["terms"]:
                self.term_list.insert("end", term)

    # Event Handlers
    def _on_flashcard_select(self, event):
        selection = self.flashcard_list.curselection()
        if selection:
            name = self.flashcard_list.get(selection[0])
            self._update_term_list(name)

    # Main Loop
    def run(self):
        self.root.mainloop()'''