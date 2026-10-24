# -*- coding: utf-8 -*-
"""Builds the revised black book. Run from report/v2:
    python build.py          (writes the .docx)
    powershell -File finalize.ps1   (Word updates the TOC and lists, then exports the PDF)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import appendix
import ch1, ch2, ch3, ch4, ch5, ch6, ch7
import front
import refs
from docbuild2 import Report

OUT = os.path.join(HERE, "Smart_Form_Black_Book_2026-27_v2.docx")

FIGURES = {
    "overview": dict(file="diagrams/overview.png", chapter=3, caption="Two-phase workflow of the proposed solution"),
    "architecture": dict(file="diagrams/architecture.png", chapter=4,
                         caption="End-to-end architecture and data flow, from document upload to reviewed form filling"),
    "dfd1": dict(file="diagrams/dfd1.png", chapter=4, caption="Data-flow diagram, level 1"),
    "er": dict(file="diagrams/er.png", chapter=4, caption="Entity–relationship diagram of the MongoDB collections and the ChromaDB chunk index"),
    "decide": dict(file="diagrams/decide.png", chapter=4, caption="Flowchart of the decide step of the form-filling pipeline"),
    "dashboard": dict(file="shots/dashboard.png", chapter=5, caption="Dashboard overview of the demonstration account"),
    "document_details": dict(file="shots/document_details.png", chapter=5, caption="Facts extracted from the Class 12 mark sheet, with evidence"),
    "profile": dict(file="shots/profile.png", chapter=5, caption="Profile page with the supporting documents of each value"),
    "conflicts": dict(file="shots/conflicts.png", chapter=5, caption="Conflict between two dates found in one certificate"),
    "ask": dict(file="shots/ask.png", chapter=5, caption="Ask Documents: answer with the cited source"),
    "ext_pair": dict(file="shots/ext_pair.png", chapter=5, caption="Extension popup: review before filling (left) and verified result (right)"),
    "form_marks": dict(file="shots/form_marks.png", chapter=5, caption="Filled subject-wise marks on the synthetic Class 12 form"),
}

TABLES = {
    "domains": dict(chapter=1, caption="Application domains of the system"),
    "lit": dict(chapter=2, caption="Summary of the surveyed literature"),
    "compare": dict(chapter=2, caption="Comparison of existing approaches with the proposed system"),
    "existing": dict(chapter=3, caption="Existing practice compared with the proposed system"),
    "freq": dict(chapter=3, caption="Functional requirements"),
    "stack": dict(chapter=3, caption="Technology stack and justification"),
    "eval": dict(chapter=5, caption="Extraction, retrieval and question-answering results (15 synthetic documents)"),
    "autofill": dict(chapter=5, caption="Browser autofill results on 15 synthetic forms"),
    "inventory": dict(chapter=6, caption="Automated test inventory"),
    "cases": dict(chapter=6, caption="Representative test cases"),
    "results": dict(chapter=6, caption="Test results: total, passed and failed test cases"),
    "objectives": dict(chapter=7, caption="Achievement of the objectives"),
    "limits": dict(chapter=7, caption="Limitations and proposed future work"),
    "components": dict(chapter="II", caption="Software components and versions"),
    "commands": dict(chapter="II", caption="Commands that run the automated test suites"),
    "endpoints": dict(chapter="II", caption="Main API endpoints used in the workflow"),
}


def main():
    R = Report(FIGURES, TABLES)
    R.first_section()
    front.cover(R)

    R.new_section("lowerRoman", 2)
    front.certificate(R)
    front.approval(R)
    front.declaration(R)
    front.acknowledgement(R)
    front.abstract(R)
    R.front("TABLE OF CONTENTS")
    R.toc(r'TOC \o "1-3" \h \z \u')
    R.front("LIST OF FIGURES")
    R.toc(r'TOC \h \z \t "FigureCaption,4"')
    R.front("LIST OF TABLES")
    R.toc(r'TOC \h \z \t "TableCaption,4"')
    front.abbreviations(R)

    R.new_section("decimal", 1)
    for ch in (ch1, ch2, ch3, ch4, ch5, ch6, ch7):
        ch.build(R)
    appendix.references(R)
    appendix.build(R)
    R.save(OUT)

    problems = R.check()
    if refs.uncited():
        problems.append(f"references never cited: {refs.uncited()}")
    print("written", OUT)
    print("figures", len([1 for k, *_ in R.inserted if k == "f"]), "tables", len([1 for k, *_ in R.inserted if k == "t"]),
          "references", len(refs.ORDER))
    print("problems:", problems or "none")


if __name__ == "__main__":
    main()
