import json
import os

class FlashcardManager:
    def __init__(self, filepath='flashcards.json'):
        self.filepath = filepath
        self.flashcards = self.load()

    def load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                return json.load(f)
        return []

    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.flashcards, f, indent=4)

    def add_flashcard(self, name):
        if not any(fc['name'] == name for fc in self.flashcards):
            self.flashcards.append({'name': name, 'terms': []})
    
    def delete_flashcard(self, name):
        self.flashcards = [fc for fc in self.flashcards if fc['name'] != name]

    def get_flashcard_names(self):
        return [fc['name'] for fc in self.flashcards]

    def get_flashcard(self, name):
        for fc in self.flashcards:
            if fc['name'] == name:
                return fc
        return None

    def add_term(self, card_name, term):
        card = self.get_flashcard(card_name)
        if card and term not in card['terms']:
            card['terms'].append(term)

    def delete_term(self, card_name, term):
        card = self.get_flashcard(card_name)
        if card and term in card['terms']:
            card['terms'].remove(term)