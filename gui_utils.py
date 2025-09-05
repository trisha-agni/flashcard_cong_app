import ttkbootstrap as ttk
import tkinter as tk
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
        ttk.Button(button_frame, text="Generate Test", bootstyle=SECONDARY, command=lambda: self.test_gen.open_test_config(self.root)).pack(side="left", padx=5)

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