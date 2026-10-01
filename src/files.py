import os
import shutil

from markitdown import MarkItDown
from PyPDF2 import PdfReader, PdfWriter

from src import DATA_DIR, SOURCES_DIR, WIKI_DIR

PAGES_DIR = SOURCES_DIR / "pages"


def setup_structure():
    if not os.path.isdir(DATA_DIR):
        os.mkdir(DATA_DIR)
    if not os.path.isdir(WIKI_DIR):
        os.mkdir(WIKI_DIR)
    if not os.path.isdir(SOURCES_DIR):
        os.mkdir(SOURCES_DIR)
    if not os.path.isdir(PAGES_DIR):
        os.mkdir(PAGES_DIR)

def get_file_name(full_path: str):
    return os.path.basename(full_path).split("/")[-1].replace(" ", "_")

def copy_to_sources(file):
    filename = get_file_name(file)
    dest_path = SOURCES_DIR / filename
    shutil.copy(file, dest_path)

def page_pdf_file(pdf_file):
    md_converter = MarkItDown()
    list_names = []
    filename = get_file_name(pdf_file)
    with open(pdf_file, "rb") as f:
        reader = PdfReader(f)
        for i in range(len(reader.pages)):
            page_name = f"page_{i}_{filename}"
            output_name = PAGES_DIR / page_name.replace(".pdf", ".md")
            if not os.path.isfile(output_name):
                output = PdfWriter()
                output.add_page(reader.pages[i])
                with open(output_name, "wb") as outputStream:
                    output.write(outputStream)

                markdown = md_converter.convert(output_name).markdown
                output_name.write_text(
                    markdown,
                    encoding="utf-8"
                )
            list_names.append(str(output_name))
    return list_names