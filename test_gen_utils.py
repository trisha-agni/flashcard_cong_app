import json
import re
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ai_utils import AIChatbot
from test_stats import TestStats
from datetime import datetime

class TestGenerator:
    def __init__(self, manager):
        self.manager = manager
        self.ai = AIChatbot()
        self.responses = {}
        self.remaining_seconds = 0
        self.generated_questions = []   # raw lines from AI
        self.parsed_mcqs = []           # list of dicts with parsed MCQ info
        self.test_submitted = False
        self._stats = TestStats()
        self.current_card_name = None
        self.current_length = None
        self.current_test_type = None

    # ----------- Test Config Popup ----------- #
    def open_test_config(self, parent, selected_card):
        popup = ttk.Toplevel(parent)
        popup.title("Generate Test")
        popup.geometry("350x250")

        ttk.Label(popup, text="Select Test Length:").pack(pady=5)
        time_var = tk.StringVar(value="15 min")
        ttk.Combobox(popup, textvariable=time_var, values=["15 min", "1 hour"]).pack(pady=5)

        ttk.Label(popup, text="Select Test Type:").pack(pady=5)
        type_var = tk.StringVar(value="MCQ")
        ttk.Combobox(popup, textvariable=type_var, values=["MCQ", "FRQ"]).pack(pady=5)

        def create_test():
            self._create_test_window(parent, selected_card, time_var.get(), type_var.get())
            popup.destroy()

        ttk.Button(popup, text="Generate", bootstyle=SUCCESS, command=create_test).pack(pady=15)

    # ----------- Build Test Window ----------- #
    def _create_test_window(self, parent, selected_card, length, test_type):
        test_popup = ttk.Toplevel(parent)
        test_popup.title(f"{test_type} Test ({length})")
        test_popup.state("zoomed")

        # store metadata for saving later
        self.current_card_name = selected_card.get("name") if isinstance(selected_card, dict) else None
        self.current_length = length
        self.current_test_type = test_type

        # --- Set countdown time ---
        self.remaining_seconds = 900 if length == "15 min" else 3600
        self.test_submitted = False

        # --- Timer label ---
        self.timer_label = ttk.Label(test_popup, text="", bootstyle="inverse-primary", font=("Helvetica", 12, "bold"))
        self.timer_label.pack(pady=5)
        self._update_timer(test_popup)

        # --- Get AI-generated questions ---
        terms = selected_card.get("terms", [])
        prompt = (
            f"Generate {test_type} style AP-level test questions using ONLY these terms: {terms}. "
            f"For MCQ: Each question starts with a number and a period (ex: 1.) followed by the question text. "
            f"Each option starts with a capital letter (A-D) followed by a period and a space followed by the option text. "
            f"For FRQ: provide an open-ended question. Return one question per line. "
            f"Do not mix formats—only {test_type} questions."
        )

        raw = self.ai.generate_test(prompt)
        questions = [q.strip() for q in raw.split("\n") if q.strip()]
        self.generated_questions = questions
        self.parsed_mcqs = []   # reset parsed storage
        if not questions:
            ttk.Label(test_popup, text="No questions generated.", bootstyle="danger").pack(pady=20)
            return

        # --- Scrollable frame ---
        canvas = tk.Canvas(test_popup)
        scrollbar = ttk.Scrollbar(test_popup, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        wrap_width = test_popup.winfo_screenwidth() - 300

        self.responses.clear()

        def group_mcq_blocks(lines):
            blocks = []
            current = []
            for line in lines:
                if re.match(r"^\d+\.", line):
                    if current:
                        blocks.append(current)
                    current = [line]
                else:
                    if current:
                        current.append(line)
            if current:
                blocks.append(current)
            return blocks

        if test_type == "MCQ":
            # Parse and display MCQ blocks; store structured info for grading
            mcq_blocks = group_mcq_blocks(questions)
            for idx, block in enumerate(mcq_blocks, start=1):
                if not block:
                    continue
                question_display = block[0].strip()
                ttk.Label(scroll_frame, text=question_display, bootstyle="primary", wraplength=wrap_width).pack(anchor="w", pady=5)

                # parse options lines into (letter, option_text)
                options = []
                for line in block[1:]:
                    m = re.match(r"^\s*([A-D])\.\s*(.*)", line)
                    if m:
                        letter = m.group(1)
                        text = m.group(2).strip()
                        options.append((letter, text))

                # create radiobuttons; responses mapped by integer index
                var = tk.StringVar()
                for letter, text in options:
                    ttk.Radiobutton(
                        scroll_frame,
                        text=f"{letter}. {text}",
                        variable=var,
                        value=letter,
                        bootstyle="primary"
                    ).pack(anchor="w", padx=20, pady=1, fill="x")

                self.responses[idx] = var

                # store parsed MCQ for grading
                full_block_text = "\n".join(block)
                opts_dict = {letter: text for (letter, text) in options}
                self.parsed_mcqs.append({
                    "index": idx,
                    "display": question_display,
                    "options": opts_dict,
                    "full_text": full_block_text
                })

        elif test_type == "FRQ":
            for i, q in enumerate(questions, start=1):
                ttk.Label(scroll_frame, text=q, bootstyle="primary", wraplength=wrap_width).pack(anchor="w", pady=5)
                entry = ttk.Entry(scroll_frame, width=80)
                entry.pack(anchor="w", pady=5, fill="x")
                self.responses[f"FRQ_{i}"] = entry

        ttk.Button(
            scroll_frame,
            text="Submit Test",
            bootstyle=SUCCESS,
            command=lambda: self._submit_test(test_popup)
        ).pack(pady=15)

    # ----------- Timer Update ----------- #
    def _update_timer(self, window):
        if self.test_submitted:
            return
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.config(text=f"Time Remaining: {minutes:02d}:{seconds:02d}")
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            window.after(1000, lambda: self._update_timer(window))
        else:
            self._submit_test(window)

    # ----------- Utility: extract JSON array substring ----------- #
    def _extract_json_array(self, text):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return None

    # ----------- Submit Handler (MCQ + FRQ) ----------- #
    def _submit_test(self, window):
        # ---------------- Collect Answers ---------------- #
        answers = {}
        for key, widget in self.responses.items():
            try:
                if isinstance(widget, tk.StringVar):
                    answers[key] = widget.get().strip()
                else:
                    answers[key] = widget.get()
            except Exception:
                answers[key] = repr(widget)

        print("DEBUG: Collected Answers:", answers)

        # ---------------- Build result dict ---------------- #
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_type": self.current_test_type or "Unknown",
            "card_name": self.current_card_name,
            "length": self.current_length,
            "responses": answers,
            "parsed_mcqs": getattr(self, "parsed_mcqs", None),
            "score": None,
            "max_score": None,
        }

        # ---------------- MCQ Grading ---------------- #
        if self.current_test_type == "MCQ" and self.parsed_mcqs:
            grading_prompt = (
                "You are an expert AP-style multiple-choice grader. "
                "For each question below (stem and options), determine the single best correct choice letter (A-D) "
                "and provide a 1-2 sentence explanation. "
                "Return JSON array of objects with fields: "
                '{"q": <index>, "correct": "<A-D>", "explanation": "..."}.\n\n'
            )
            for q in self.parsed_mcqs:
                grading_prompt += q["full_text"] + "\n\n"

            ai_response = self.ai.generate_test(grading_prompt)
            json_text = self._extract_json_array(ai_response)
            grading_map = {}
            if json_text:
                try:
                    parsed = json.loads(json_text)
                    for obj in parsed:
                        idx = int(obj.get("q"))
                        correct_letter = str(obj.get("correct", "")).upper()
                        explanation = obj.get("explanation", "").strip()
                        grading_map[idx] = {"correct": correct_letter, "explanation": explanation}
                except Exception:
                    pass

            total_correct = 0
            for item in self.parsed_mcqs:
                idx = item["index"]
                gm = grading_map.get(idx)
                if gm:
                    item["answer"] = gm["correct"]
                student_choice = answers.get(idx, "")
                if gm and student_choice == gm["correct"]:
                    total_correct += 1

            result["score"] = total_correct
            result["max_score"] = len(self.parsed_mcqs)

            # ---------------- Show MCQ Results ---------------- #
            result_popup = ttk.Toplevel(window)
            result_popup.title("MCQ Results")
            result_popup.state("zoomed")
            canvas = tk.Canvas(result_popup)
            scrollbar = ttk.Scrollbar(result_popup, orient="vertical", command=canvas.yview)
            frame = ttk.Frame(canvas, padding=10)
            frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            for item in self.parsed_mcqs:
                idx = item["index"]
                student_choice = answers.get(idx, "")
                gm = grading_map.get(idx)
                if not gm:
                    ttk.Label(frame, text=f"Q{idx}: No grading info from AI.", bootstyle="warning", wraplength=760).pack(anchor="w", pady=6)
                    continue
                correct_letter = gm["correct"]
                explanation = gm["explanation"]
                correct_text = item["options"].get(correct_letter, "(option text unavailable)")
                is_correct = (student_choice == correct_letter)
                color = "success" if is_correct else "danger"
                icon = "✔" if is_correct else "✖"
                display_text = (
                    f"Q{idx} {icon}\n"
                    f"  Question: {item['display']}\n"
                    f"  Your answer: {student_choice if student_choice else '(no answer)'}\n"
                    f"  Correct: {correct_letter}. {correct_text}\n"
                    f"  Explanation: {explanation}"
                )
                ttk.Label(frame, text=display_text, bootstyle=color, wraplength=760, justify="left").pack(anchor="w", pady=8)

            ttk.Label(frame, text=f"Total Correct: {total_correct}/{len(self.parsed_mcqs)}",
                    bootstyle="info", font=("Helvetica", 14, "bold")).pack(anchor="center", pady=10)

        # ---------------- FRQ Grading ---------------- #
        elif self.current_test_type == "FRQ":
            frq_keys = [k for k in answers.keys() if str(k).startswith("FRQ_")]
            if frq_keys:
                frq_prompt = "You are an AP-style FRQ grader. Grade each response out of 5 points and provide 1-2 sentence feedback. Return JSON array [{\"q\": <index>, \"score\": <points>, \"feedback\": \"...\"}]\n\n"
                frq_questions = {}
                for key in frq_keys:
                    idx = int(key.split("_")[1])
                    question_text = next((line for line in self.generated_questions if line.startswith(f"{idx}.")), f"Question {idx}")
                    student_answer = answers.get(key, "")
                    frq_questions[idx] = question_text
                    frq_prompt += f"Question {idx}: {question_text}\nStudent answer: {student_answer}\n\n"

                ai_response = self.ai.generate_test(frq_prompt)
                json_text = self._extract_json_array(ai_response)
                parsed = []
                if json_text:
                    try:
                        parsed = json.loads(json_text)
                    except Exception:
                        parsed = []

                total_score = 0
                max_score = len(parsed)*5 if parsed else len(frq_keys)*5

                result_popup = ttk.Toplevel(window)
                result_popup.title("FRQ Results")
                result_popup.state("zoomed")
                canvas = tk.Canvas(result_popup)
                scrollbar = ttk.Scrollbar(result_popup, orient="vertical", command=canvas.yview)
                frame = ttk.Frame(canvas, padding=10)
                frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                canvas.create_window((0, 0), window=frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")

                for item in parsed:
                    idx = int(item.get("q", 0))
                    score = int(item.get("score", 0))
                    feedback = item.get("feedback", "")
                    total_score += score
                    student_answer = answers.get(f"FRQ_{idx}", "")
                    question_text = frq_questions.get(idx, f"Question {idx}")
                    color = "success" if score >= 3 else "danger"
                    display_text = (
                        f"Q{idx}\n"
                        f"  Question: {question_text}\n"
                        f"  Your answer: {student_answer}\n"
                        f"  Score: {score}/5\n"
                        f"  Feedback: {feedback}"
                    )
                    ttk.Label(frame, text=display_text, bootstyle=color, wraplength=760, justify="left").pack(anchor="w", pady=8)

                ttk.Label(frame, text=f"Total Score: {total_score}/{max_score}", bootstyle="info",
                        font=("Helvetica", 14, "bold")).pack(anchor="center", pady=10)

                result["score"] = total_score
                result["max_score"] = max_score

        # ---------------- Final Save to TestStats ---------------- #
        try:
            self._stats.add_result(
                test_type=self.current_test_type,
                card_name=self.current_card_name,
                length=self.current_length,
                responses=answers,
                parsed_mcqs=getattr(self, "parsed_mcqs", None),
                score=result["score"],
                max_score=result["max_score"]
            )
            ttk.Label(window,
                    text="Test submitted successfully!" if self.remaining_seconds > 0 else "Time's up! Test submitted!",
                    bootstyle="success").pack(pady=10)
            print("Saved test result to test_results.json")
        except Exception as e:
            print(f"Error saving test result: {e}")

'''import json
import re
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ai_utils import AIChatbot


class TestGenerator:
    def __init__(self, manager):
        self.manager = manager
        self.ai = AIChatbot()
        self.responses = {}
        self.remaining_seconds = 0
        self.generated_questions = []   # raw lines from AI
        self.parsed_mcqs = []           # list of dicts with parsed MCQ info
        self.test_submitted = False

    # ----------- Test Config Popup ----------- #
    def open_test_config(self, parent, selected_card):
        popup = ttk.Toplevel(parent)
        popup.title("Generate Test")
        popup.geometry("300x180")

        ttk.Label(popup, text="Select Test Length:").pack(pady=5)
        time_var = tk.StringVar(value="15 min")
        ttk.Combobox(popup, textvariable=time_var, values=["15 min", "1 hour"]).pack(pady=5)

        ttk.Label(popup, text="Select Test Type:").pack(pady=5)
        type_var = tk.StringVar(value="MCQ")
        ttk.Combobox(popup, textvariable=type_var, values=["MCQ", "FRQ"]).pack(pady=5)

        def create_test():
            self._create_test_window(parent, selected_card, time_var.get(), type_var.get())
            popup.destroy()

        ttk.Button(popup, text="Generate", bootstyle=SUCCESS, command=create_test).pack(pady=15)

    # ----------- Build Test Window ----------- #
    def _create_test_window(self, parent, selected_card, length, test_type):
        test_popup = ttk.Toplevel(parent)
        test_popup.title(f"{test_type} Test ({length})")
        test_popup.geometry("750x550")

        # --- Set countdown time ---
        self.remaining_seconds = 900 if length == "15 min" else 3600
        self.test_submitted = False

        # --- Timer label ---
        self.timer_label = ttk.Label(test_popup, text="", bootstyle="inverse-primary", font=("Helvetica", 12, "bold"))
        self.timer_label.pack(pady=5)
        self._update_timer(test_popup)

        # --- Get AI-generated questions ---
        terms = selected_card.get("terms", [])
        prompt = (
            f"Generate {test_type} style AP-level test questions using ONLY these terms: {terms}. "
            f"For MCQ: Each question starts with a number and a period (ex: 1.) followed by the question text. "
            f"Each option starts with a capital letter (A-D) followed by a period and a space followed by the option text. "
            f"For FRQ: provide an open-ended question. Return one question per line. "
            f"Do not mix formats—only {test_type} questions."
        )

        raw = self.ai.generate_test(prompt)
        questions = [q.strip() for q in raw.split("\n") if q.strip()]
        self.generated_questions = questions
        self.parsed_mcqs = []   # reset parsed storage
        if not questions:
            ttk.Label(test_popup, text="No questions generated.", bootstyle="danger").pack(pady=20)
            return

        # --- Scrollable frame ---
        canvas = tk.Canvas(test_popup)
        scrollbar = ttk.Scrollbar(test_popup, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.responses.clear()

        def group_mcq_blocks(lines):
            blocks = []
            current = []
            for line in lines:
                if re.match(r"^\d+\.", line):
                    if current:
                        blocks.append(current)
                    current = [line]
                else:
                    if current:
                        current.append(line)
            if current:
                blocks.append(current)
            return blocks

        if test_type == "MCQ":
            # Parse and display MCQ blocks; store structured info for grading
            mcq_blocks = group_mcq_blocks(questions)
            for idx, block in enumerate(mcq_blocks, start=1):
                if not block:
                    continue
                question_display = block[0].strip()
                ttk.Label(scroll_frame, text=question_display, bootstyle="primary", wraplength=700).pack(anchor="w", pady=5)

                # parse options lines into (letter, option_text)
                options = []
                for line in block[1:]:
                    m = re.match(r"^\s*([A-D])\.\s*(.*)", line)
                    if m:
                        letter = m.group(1)
                        text = m.group(2).strip()
                        options.append((letter, text))

                # create radiobuttons; responses mapped by integer index
                var = tk.StringVar()
                for letter, text in options:
                    ttk.Radiobutton(
                        scroll_frame,
                        text=f"{letter}. {text}",
                        variable=var,
                        value=letter,
                        bootstyle="primary"
                    ).pack(anchor="w", padx=20, pady=1)

                self.responses[idx] = var

                # store parsed MCQ for grading
                full_block_text = "\n".join(block)
                opts_dict = {letter: text for (letter, text) in options}
                self.parsed_mcqs.append({
                    "index": idx,
                    "display": question_display,
                    "options": opts_dict,
                    "full_text": full_block_text
                })

        elif test_type == "FRQ":
            for i, q in enumerate(questions, start=1):
                ttk.Label(scroll_frame, text=q, bootstyle="primary", wraplength=700).pack(anchor="w", pady=5)
                entry = ttk.Entry(scroll_frame, width=80)
                entry.pack(anchor="w", pady=5)
                self.responses[f"FRQ_{i}"] = entry

        ttk.Button(
            scroll_frame,
            text="Submit Test",
            bootstyle=SUCCESS,
            command=lambda: self._submit_test(test_popup)
        ).pack(pady=15)

    # ----------- Timer Update ----------- #
    def _update_timer(self, window):
        if self.test_submitted:
            return
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.config(text=f"Time Remaining: {minutes:02d}:{seconds:02d}")
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            window.after(1000, lambda: self._update_timer(window))
        else:
            self._submit_test(window)

    # ----------- Utility: extract JSON array substring ----------- #
    def _extract_json_array(self, text):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return None

    # ----------- Submit Handler (MCQ + FRQ) ----------- #
    def _submit_test(self, window):
        self.test_submitted = True
        answers = {}
        for key, widget in self.responses.items():
            if isinstance(widget, tk.StringVar):
                answers[key] = widget.get().strip().upper()
            else:
                answers[key] = widget.get()

        ttk.Label(window,
                  text="Time's up! Test submitted!" if self.remaining_seconds <= 0 else "Test submitted!",
                  bootstyle="success").pack(pady=10)

        # ---------------- MCQ Grading ---------------- #
        if self.parsed_mcqs:
            # Build grading prompt
            grading_prompt = (
                "You are an expert AP-style multiple-choice grader. "
                "For each question below (stem and options), determine the single best correct choice letter (A-D) "
                "and provide a 1-2 sentence explanation for why that choice is correct. "
                "Return results as a JSON array of objects with fields: "
                "{\"q\": <question_index>, \"correct\": \"<A-D>\", \"explanation\": \"...\"}.\n\n"
            )

            for item in self.parsed_mcqs:
                grading_prompt += f"Question {item['index']}:\n{item['full_text']}\n\n"

            ai_response = self.ai.generate_test(grading_prompt)
            json_text = self._extract_json_array(ai_response)
            parsed = []
            if json_text:
                try:
                    parsed = json.loads(json_text)
                except Exception:
                    parsed = []

            grading_map = {}
            for obj in parsed:
                try:
                    qnum = int(obj.get("q"))
                    correct_letter = str(obj.get("correct", "")).upper()
                    m = re.search(r"[A-D]", correct_letter)
                    correct_letter = m.group(0) if m else correct_letter
                    explanation = obj.get("explanation", "").strip()
                    grading_map[qnum] = {"correct": correct_letter, "explanation": explanation}
                except Exception:
                    continue

            # Show MCQ results
            result_popup = ttk.Toplevel(window)
            result_popup.title("MCQ Results")
            result_popup.geometry("820x600")

            canvas = tk.Canvas(result_popup)
            scrollbar = ttk.Scrollbar(result_popup, orient="vertical", command=canvas.yview)
            frame = ttk.Frame(canvas, padding=10)
            frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            total_correct = 0
            for item in self.parsed_mcqs:
                idx = item["index"]
                student_choice = answers.get(idx, "")
                grade_info = grading_map.get(idx)
                if not grade_info:
                    ttk.Label(frame, text=f"Q{idx}: No grading info from AI.", bootstyle="warning", wraplength=760).pack(anchor="w", pady=6)
                    continue
                correct_letter = grade_info["correct"]
                explanation = grade_info["explanation"]
                correct_text = item["options"].get(correct_letter, "(option text unavailable)")
                is_correct = (student_choice == correct_letter)
                if is_correct:
                    total_correct += 1
                icon = "✔" if is_correct else "✖"
                color = "success" if is_correct else "danger"

                display_text = (
                    f"Q{idx} {icon}\n"
                    f"  Question: {item['display']}\n"
                    f"  Your answer: {student_choice if student_choice else '(no answer)'}\n"
                    f"  Correct: {correct_letter}. {correct_text}\n"
                    f"  Explanation: {explanation}"
                )
                ttk.Label(frame, text=display_text, bootstyle=color, wraplength=760, justify="left").pack(anchor="w", pady=8)

            ttk.Label(frame, text=f"Total Correct: {total_correct}/{len(self.parsed_mcqs)}", bootstyle="info", font=("Helvetica", 14, "bold")).pack(anchor="center", pady=10)

        # ---------------- FRQ Grading ---------------- #
        frq_keys = [k for k in self.responses.keys() if str(k).startswith("FRQ_")]
        if frq_keys:
            frq_prompt = "You are an AP-style FRQ grader. Grade each response out of 5 points and provide 1-2 sentence feedback. Return JSON array [{\"q\": <index>, \"score\": <points>, \"feedback\": \"...\"}]\n\n"
            frq_questions = {}
            for key in frq_keys:
                idx = int(key.split("_")[1])
                # get corresponding question text
                question_text = next((line for line in self.generated_questions if line.startswith(f"{idx}.")), f"Question {idx}")
                frq_questions[idx] = question_text
                student_answer = answers.get(key, "")
                frq_prompt += f"Question {idx}: {question_text}\nStudent answer: {student_answer}\n\n"

            ai_response = self.ai.generate_test(frq_prompt)
            json_text = self._extract_json_array(ai_response)
            parsed = []
            if json_text:
                try:
                    parsed = json.loads(json_text)
                except Exception:
                    parsed = []

            result_popup = ttk.Toplevel(window)
            result_popup.title("FRQ Results")
            result_popup.geometry("820x600")

            canvas = tk.Canvas(result_popup)
            scrollbar = ttk.Scrollbar(result_popup, orient="vertical", command=canvas.yview)
            frame = ttk.Frame(canvas, padding=10)
            frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            total_score = 0
            max_score = len(parsed)*5 if parsed else len(frq_keys)*5

            for item in parsed:
                idx = int(item.get("q", 0))
                score = int(item.get("score", 0))
                feedback = item.get("feedback", "")
                total_score += score
                student_answer = answers.get(f"FRQ_{idx}", "")
                question_text = frq_questions.get(idx, f"Question {idx}")
                color = "success" if score >= 3 else "danger"

                display_text = (
                    f"Q{idx}\n"
                    f"  Question: {question_text}\n"
                    f"  Your answer: {student_answer}\n"
                    f"  Score: {score}/5\n"
                    f"  Feedback: {feedback}"
                )
                ttk.Label(frame, text=display_text, bootstyle=color, wraplength=760, justify="left").pack(anchor="w", pady=8)

            ttk.Label(frame, text=f"Total Score: {total_score}/{max_score}", bootstyle="info", font=("Helvetica", 14, "bold")).pack(anchor="center", pady=10)'''