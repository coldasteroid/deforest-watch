"""Replace the paper's TBD results cells with an honest pending-results table."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf import PageObject
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


SOURCE = Path(r"C:\Users\ADITYA SHARMA\Downloads\Deforest Watch, Paper Draft 1-1.pdf")
OUTPUT = Path("output/pdf/DeforestWatch_Paper_Filled.pdf")


def _pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_overlay() -> PageObject:
    page = PageObject.create_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
    })
    commands: list[str] = []

    def text(x: float, y: float, value: str, size: float, *, center: float | None = None) -> None:
        if center is not None:
            x = center - len(value) * size * 0.25
        commands.append(f"BT /F1 {size} Tf {x:.2f} {y:.2f} Td ({_pdf_text(value)}) Tj ET")

    def line(x1: float, y1: float, x2: float, y2: float) -> None:
        commands.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    commands += ["q", "1 1 1 rg", "40 488 270 116 re f", "Q", "0 0 0 rg", "0 0 0 RG", "0.35 w"]

    # Table IV occupies the top of the left IEEE column on page 5. Cover only
    # that table and redraw it with compact, non-fabricated status values.
    text(175, 590, "TABLE IV", 7.5, center=175)
    text(175, 580, "Synthetic Demonstration Results - Pair 01", 6.0, center=175)

    x0, y0 = 42, 566
    widths = [82, 28, 28, 28, 28, 32, 34]
    row_h = 15
    headers = ["Method", "Prec.", "Rec.", "F1", "IoU", "Pix. Acc.", "Latency"]
    rows = [
        ["NDVI threshold only", "1.00", "1.00", "1.00", "1.00", "1.00", "116.6 ms"],
        ["U-Net only", "N/A", "N/A", "N/A", "N/A", "N/A", "Not run"],
        ["NDVI + U-Net", "N/A", "N/A", "N/A", "N/A", "N/A", "Not run"],
        ["Attention U-Net", "N/A", "N/A", "N/A", "N/A", "N/A", "Not run"],
    ]
    total_w = sum(widths)
    commands += ["0.94 0.94 0.94 rg", f"{x0} {y0 - row_h} {total_w} {row_h} re f", "0 0 0 rg"]
    commands.append(f"{x0} {y0 - row_h * (len(rows) + 1)} {total_w} {row_h * (len(rows) + 1)} re S")
    for row in range(len(rows) + 2):
        y = y0 - row * row_h
        line(x0, y, x0 + total_w, y)
    x = x0
    for width in widths:
        line(x, y0, x, y0 - row_h * (len(rows) + 1))
        x += width
    line(x, y0, x, y0 - row_h * (len(rows) + 1))

    x = x0
    for label, width in zip(headers, widths):
        text(x + width / 2, y0 - 10, label, 5.8, center=x + width / 2)
        x += width
    for row_index, values in enumerate(rows, 1):
        x = x0
        baseline = y0 - row_index * row_h - 10
        for value, width in zip(values, widths):
            if x == x0:
                text(x + 2, baseline, value, 5.5)
            else:
                text(x + width / 2, baseline, value, 5.5, center=x + width / 2)
            x += width

    text(42, 491, "Pair 01 uses synthetic ground truth; neural-network rows were not run and must not be read as measured accuracy.", 5.0)
    content = DecodedStreamObject()
    content.set_data("\n".join(commands).encode("latin-1"))
    page[NameObject("/Contents")] = content
    return page


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(SOURCE))
    overlay = build_overlay()
    reader.pages[4].merge_page(overlay)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with OUTPUT.open("wb") as handle:
        writer.write(handle)
    print(OUTPUT)


if __name__ == "__main__":
    main()
