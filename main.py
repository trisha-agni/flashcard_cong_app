from fc_utils import FlashcardManager
from gui_utils import FlashcardGUI

def main():
    manager = FlashcardManager()
    gui = FlashcardGUI(manager)
    gui.run()

if __name__ == "__main__":
    main()