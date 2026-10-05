from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    add_book_name = State()

    add_unit_choose_book = State()
    add_unit_number = State()

    add_word_choose_book = State()
    add_word_choose_unit = State()
    add_word_text = State()
    add_word_translation = State()
    add_word_translation_ru = State()

    browse_choose_book = State()
    browse_choose_unit = State()

    edit_word_text = State()
    edit_word_translation = State()
    edit_word_translation_ru = State()

    bulk_import_choose_book = State()
    bulk_import_choose_unit = State()
    bulk_import_wait_file = State()
    bulk_import_pdf_confirm = State()
