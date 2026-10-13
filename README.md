# Indus-valley-script

This project brings together research on the undeciphered Indus (Harappan) script, c. 2600–1900 BCE, and adds a new, reproducible structural analysis of the surviving inscriptions.

**Start here: [report/INDUS_SCRIPT_REPORT.md](report/INDUS_SCRIPT_REPORT.md)**

## Findings

- **The script has not been deciphered phonetically, here or anywhere else.** There is no bilingual text, and the corpus (about 4–5k very short texts) is too small for any proposed sound values to be checked. The report reviews every major claimed decipherment and explains why each is unverified or rejected.
- **We can still decode what the signs do.** Two independently transcribed corpora were analysed: the ICIT digitisation (2,543 objects) and Mahadevan 1977 (3,573 lines). Both show the following:
  - **Reading direction.** Texts run right to left. The final position is far more constrained than the initial one: 23 signs cover 80% of endings, while 103 are needed to cover 80% of beginnings.
  - **Script type.** There are about 400–800 signs, which points to a **logo-syllabic** system.
  - **Text structure.** Texts follow a three-zone template: **OPENING → CORE → CLOSING**. Using each sign's typical position alone, the order of held-out texts can be predicted (Kendall τ = 0.65).
  - **Functional sign classes.** These include an opening formula; stroke numerals placed before the thing they count; a productive "fish" class; and a bound "jar" morpheme that closes texts.
  - **Seal text vs. seal animal.** The text on a seal is **statistically independent of the animal** shown on it.
  - **Genres.** Seal texts are mostly unique (86%). Tablet texts are mostly repeated (61–69%).
  - **Standardisation.** Sign use is highly uniform: Mohenjo-daro and Harappa differ on only 3 of 73 signs.
- **Every text has a functional transliteration** in [`results/tables/functional_readings.csv`](results/tables/functional_readings.csv).

## Layout

```
report/INDUS_SCRIPT_REPORT.md   literature review, evidence, results, decoding attempt, references
analysis/                       build_corpus.py, run_analysis.py, functional_reading.py, render_signs.py, sign_names.csv
results/                        summary.json, analysis_log.md (all numbers), tables/*.csv, figures/*.png
data/fetch_sources.sh           downloads the source corpora (pinned commits) into data/raw/ (not committed)
```

## Reproduce

```bash
pip install numpy scipy matplotlib pillow
./data/fetch_sources.sh
python3 analysis/build_corpus.py
python3 analysis/render_signs.py 200
cd analysis && python3 run_analysis.py && python3 functional_reading.py
```

## Data sources and licences

- **ICIT transcriptions** come from Yajnadevam's digitisation, [`yajnadevam/indus-website`](https://github.com/yajnadevam/indus-website) (GPL-3.0). Only the raw sign sequences and metadata are used, not that author's proposed readings. Tables in `results/` that list sign sequences are derived from this data.
- **Mahadevan (1977) concordance** comes from the CSV export distributed in [`joyboseroy/indus_decipher`](https://github.com/joyboseroy/indus_decipher).
- **Sign images** in `results/figures/` are rendered with the `sk_indus_script` font shipped with the ICIT digitisation.
