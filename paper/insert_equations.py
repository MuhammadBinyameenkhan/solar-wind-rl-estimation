"""Replace the equation placeholders written by make_proposal.js / make_irea_pwp.js with Word equations.

The builders write each equation as a paragraph containing @@EQ|<key>|<number>@@. This script swaps that
paragraph for a borderless three-column table: empty cell, centred Word (OMML) equation, number at the right.
The OMML comes from paper/equations/omml.json, produced by make_equations.py, so no pandoc is needed here.

Usage: python paper/insert_equations.py <file.docx> <text width in DXA> <font size in half-points>
"""
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OMML = json.loads((HERE / "equations" / "omml.json").read_text(encoding="utf8"))
NO_BORDER = "".join(f'<w:{s} w:val="nil"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))


def styled(omml, size):
    """Give every math run the Cambria Math font at the document's body size."""
    rpr = (f'<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>'
           f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>')
    omml = re.sub(r"(<m:r>(?:<m:rPr>.*?</m:rPr>)?)", lambda m: m.group(1) + rpr, omml)
    return omml


def table(omml, number, width, size):
    side = 350 if width < 6000 else 1100
    mid = width - 2 * side
    cell = lambda w, body: (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>{body}</w:tc>')
    num = (f'<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:jc w:val="right"/></w:pPr>'
           f'<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="{size}"/>'
           f'</w:rPr><w:t>({number})</w:t></w:r></w:p>')
    eq = (f'<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:jc w:val="center"/></w:pPr>'
          f'{styled(omml, size)}</w:p>')
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{width}" w:type="dxa"/><w:jc w:val="center"/>'
            f'<w:tblBorders>{NO_BORDER}</w:tblBorders><w:tblLayout w:type="fixed"/>'
            f'<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="{side}"/><w:gridCol w:w="{mid}"/><w:gridCol w:w="{side}"/></w:tblGrid>'
            f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{cell(side, "<w:p/>")}{cell(mid, eq)}{cell(side, num)}</w:tr></w:tbl>')


def main(path, width, size):
    path = Path(path)
    zin = zipfile.ZipFile(path)
    xml = zin.read("word/document.xml").decode("utf8")
    pat = re.compile(r"<w:p[ >](?:(?!<w:p[ >]).)*?@@EQ\|([^|]+)\|([^@]+)@@.*?</w:p>", re.S)
    done = []

    def sub(m):
        key, number = m.group(1), m.group(2)
        if key not in OMML:
            raise KeyError(f"no equation {key} in omml.json; run make_equations.py")
        done.append(key)
        return table(OMML[key], number, width, size)

    xml = pat.sub(sub, xml)
    if "@@EQ|" in xml:
        raise RuntimeError("an equation placeholder was not replaced")
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            zout.writestr(it, xml.encode("utf8") if it.filename == "word/document.xml" else zin.read(it.filename))
    zin.close()
    tmp.replace(path)
    print(f"inserted {len(done)} Word equations into {path.name}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
