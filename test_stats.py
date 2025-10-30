import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import tkinter as tk
import ttkbootstrap as ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

RESULTS_PATH = Path(__file__).parent / "test_results.json"


class TestStats:
    def __init__(self, file_path: Path | str = RESULTS_PATH):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            self._save_data([])

    # ---------- JSON helpers ----------
    def _load_data(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_data(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ---------- Save result ----------
    def add_result(self, *, test_type, card_name=None, length=None, responses=None, parsed_mcqs=None, score=None, max_score=None):
        """
        Save a test attempt. responses should be a dict mapping question_display -> answer (e.g. "A" or text).
        parsed_mcqs is optional metadata produced when test was generated.
        """
        data = self._load_data()
        ts = datetime.utcnow().isoformat()
        percent = self._compute_percent(test_type, responses, parsed_mcqs, score, max_score)
        record = {
            "timestamp": ts,
            "test_type": test_type,
            "card_name": card_name or "General",
            "length": length,
            "responses": responses or {},
            "parsed_mcqs": parsed_mcqs,
            "score": score,
            "max_score": max_score,
            "percent": percent,
        }
        data.append(record)
        self._save_data(data)
        return record

    def _compute_percent(self, test_type, responses, parsed_mcqs, score, max_score):
        # explicit score preferred
        try:
            if score is not None and max_score is not None:
                return round(float(score) / float(max_score) * 100.0, 2)
        except Exception:
            pass

        # if parsed_mcqs contains correct keys, compute accuracy
        if parsed_mcqs and isinstance(parsed_mcqs, list):
            correct = 0
            total = 0
            for q in parsed_mcqs:
                # accept 'answer' or 'correct' as key names
                expected = q.get("answer") or q.get("correct")
                qdisplay = q.get("display") or q.get("question")
                if expected is not None and qdisplay is not None:
                    total += 1
                    given = (responses or {}).get(qdisplay)
                    if given is None:
                        continue
                    if isinstance(given, str) and given.strip().upper() == str(expected).strip().upper():
                        correct += 1
            if total > 0:
                return round(correct / total * 100.0, 2)

        # fallback: percent answered (useful when no ground truth)
        if responses:
            total = len(responses)
            if total == 0:
                return 0.0
            answered = sum(1 for v in responses.values() if v not in (None, "", [], {}))
            return round(answered / total * 100.0, 2)

        return 0.0

    # ---------- Plots ----------
    def _embed_figure(self, parent, fig: Figure, title="Plot"):
        win = ttk.Toplevel(parent)
        win.title(title)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)
        return win

    def plot_score_over_time(self, parent=None, card_name=None, recent_n=None):
        data = self._load_data()
        if card_name:
            data = [d for d in data if d.get("card_name") == card_name]
        if not data:
            popup = ttk.Toplevel(parent)
            popup.title("No Data")
            ttk.Label(popup, text="No test results found.", bootstyle="warning").pack(padx=20, pady=20)
            return

        # sort by timestamp
        def _parse_ts(x):
            try:
                return datetime.fromisoformat(x["timestamp"])
            except Exception:
                return datetime.utcnow()

        data.sort(key=_parse_ts)
        if recent_n:
            data = data[-recent_n:]

        times = [_parse_ts(d) for d in data]
        percents = [d.get("percent", 0.0) for d in data]

        fig = Figure(figsize=(7, 3.5), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(times, percents, marker="o", linestyle="-")
        ax.set_title(f"Score / Answered % Over Time ({card_name or 'All'})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Percent (%)")
        ax.set_ylim(0, 100)
        ax.grid(True)

        self._embed_figure(parent or tk._default_root, fig, title="Score Over Time")

    def plot_question_selection_trend(self, question_index=0, parent=None, card_name=None):
        """
        For MCQ tests, plot how many times each option was selected for the given question index
        across attempts (cumulative over time).
        """
        data = self._load_data()
        if card_name:
            data = [d for d in data if d.get("card_name") == card_name]

        # collect selections per timestamp
        times = []
        selections = []
        for d in data:
            if d.get("test_type") != "MCQ":
                continue
            resp = d.get("responses", {})
            keys = list(resp.keys())
            if len(keys) <= question_index:
                continue
            key = keys[question_index]
            val = resp.get(key)
            if val is None:
                continue
            times.append(datetime.fromisoformat(d["timestamp"]) if "timestamp" in d else datetime.utcnow())
            selections.append(val)

        if not selections:
            popup = ttk.Toplevel(parent)
            popup.title("No Data")
            ttk.Label(popup, text="No MCQ selection data found for that question index.", bootstyle="warning").pack(padx=20, pady=20)
            return

        opts = sorted(set(selections))
        cumulative = {o: [] for o in opts}
        counts = Counter()
        timestamps = []
        for t, sel in zip(times, selections):
            counts[sel] += 1
            timestamps.append(t)
            for o in opts:
                cumulative[o].append(counts[o])

        fig = Figure(figsize=(7, 3.5), dpi=100)
        ax = fig.add_subplot(111)
        for o in opts:
            ax.plot(timestamps, cumulative[o], marker="o", label=str(o))
        ax.set_title(f"Selections over time for question #{question_index+1} ({card_name or 'All'})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative selections")
        ax.legend()
        ax.grid(True)

        self._embed_figure(parent or tk._default_root, fig, title="Question Selection Trend")

    # ---------- Utility: return raw results ----------
    def get_all_results(self):
        return self._load_data()