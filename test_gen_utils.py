import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ai_utils import AIChatbot


class TestGenerator:
    def __init__(self, manager):
        self.manager = manager
        self.ai = AIChatbot()

    def open_test_config(self, parent):
        # Popup window for selecting test options
        popup = ttk.Toplevel(parent)
        popup.title("Generate Test")
        popup.geometry("300x200")

        # Time length selector
        ttk.Label(popup, text="Select Test Length:").pack(pady=5)
        time_var = tk.StringVar(value="15 min")
        ttk.Combobox(popup, textvariable=time_var, values=["15 min", "1 hour"]).pack(pady=5)

        # Test type selector
        ttk.Label(popup, text="Select Test Type:").pack(pady=5)
        type_var = tk.StringVar(value="MCQ")
        ttk.Combobox(popup, textvariable=type_var, values=["MCQ", "FRQ", "Mixed (MCQ + FRQ)"]).pack(pady=5)

        # Generate button
        def create_test():
            length = time_var.get()
            test_type = type_var.get()
            self._create_test_window(parent, length, test_type)
            popup.destroy()

        ttk.Button(popup, text="Generate", bootstyle=SUCCESS, command=create_test).pack(pady=15)

    def _create_test_window(self, parent, length, test_type):
        # Creates and displays the generated test in a new window
        test_popup = ttk.Toplevel(parent)
        test_popup.title(f"{test_type} Test ({length})")
        test_popup.geometry("600x400")

        # Get terms from flashcards
        terms = []
        for card in self.manager.flashcards:
            terms.extend(card.get("terms", []))

        # Ask AI to generate AP-style test
        prompt = (
            f"Generate a {test_type} style test with AP-level questions "
            f"using the following terms: {terms}. "
            f"The test should take about {length}."
            f"Don't include equations in questions."
        )
        questions = self.ai.generate_test(prompt)

        # Display test text
        text = tk.Text(test_popup, wrap="word")
        text.insert("1.0", questions)
        text.config(state="disabled")
        text.pack(fill="both", expand=True, padx=10, pady=10)