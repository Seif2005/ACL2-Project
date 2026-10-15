"""Build ACL_Milestone1_Report.docx from notebook outputs.
Run from the project root: python report/build_report.py
"""
import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FIGURES = "report/figures"
OUT = "report/ACL_Milestone1_Report.docx"

# ── helpers ───────────────────────────────────────────────────────────────────

def heading(doc, text, level):
    doc.add_heading(text, level=level)

def para(doc, text, bold=False, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    return p

def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(text)
    return p

def fig(doc, name, caption, width=6.0):
    path = os.path.join(FIGURES, name)
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(width))
        last = doc.paragraphs[-1]
        last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        para(doc, f"[FIGURE MISSING: {name}]", italic=True)
    c = doc.add_paragraph(caption)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.runs[0].italic = True
    doc.add_paragraph()  # spacer

def table_from_rows(doc, headers, rows, caption=""):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    hrow = t.rows[0]
    for i, h in enumerate(headers):
        cell = hrow.cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            t.rows[ri + 1].cells[ci].text = str(val)
    if caption:
        c = doc.add_paragraph(caption)
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.runs[0].italic = True
    doc.add_paragraph()
    return t

def page_break(doc):
    doc.add_page_break()

# ── document ─────────────────────────────────────────────────────────────────

doc = Document()

# ── title page ───────────────────────────────────────────────────────────────
title_para = doc.add_paragraph()
title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title_para.add_run("GUC ACL Milestone 1\nFormula 1 Podium Prediction\nAnalytical Report")
run.bold = True
run.font.size = Pt(24)

doc.add_paragraph()
doc.add_paragraph()

for label, placeholder in [
    ("Team name:", "[TEAM NAME]"),
    ("Team members:", "[NAME 1] – [ID 1]\n[NAME 2] – [ID 2]\n[NAME 3] – [ID 3]"),
    ("Tutorial group:", "[GROUP]"),
    ("Date:", "October 2026"),
]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(label + " ").bold = True
    p.add_run(placeholder)

page_break(doc)

# ── table of contents stub ───────────────────────────────────────────────────
heading(doc, "Contents", 1)
para(doc, "(Use Word's References → Update Table to generate the final TOC.)", italic=True)
page_break(doc)

# =============================================================================
# SECTION 1 – DATA CLEANING & AUDIT
# =============================================================================
heading(doc, "1  Data Cleaning & Audit", 1)

para(doc,
     "This section documents every change made to the raw CSV data before any analysis. "
     "The raw files are never modified; all operations are applied to copies. "
     "The main table used throughout is results (one row per driver per race); "
     "we also join races, qualifying, circuits, drivers, status, and constructors.")

# 1.1 Dataset overview
heading(doc, "1.1  Dataset Overview", 2)
para(doc,
     "The dataset contains 14 CSV tables covering the Formula 1 World Championship from 1950 to 2024. "
     "Table 1 shows the row and column counts after loading (before any cleaning).")

table_from_rows(doc,
    ["Table", "Rows", "Columns"],
    [
        ["circuits", "77", "9"],
        ["constructors", "212", "5"],
        ["drivers", "861", "9"],
        ["seasons", "75", "2"],
        ["races", "1,125", "18"],
        ["status", "139", "2"],
        ["results", "26,759", "18"],
        ["qualifying", "10,494", "9"],
        ["sprint_results", "360", "16"],
        ["driver_standings", "34,863", "7"],
        ["constructor_standings", "13,391", "7"],
        ["constructor_results", "12,625", "5"],
        ["lap_times", "589,081", "6"],
        ["pit_stops", "11,371", "7"],
    ],
    caption="Table 1. Raw table sizes (before cleaning)."
)

# 1.2 Sentinel handling
heading(doc, "1.2  Sentinel Handling and Semantic Typing", 2)
para(doc,
     "The CSV files use the literal string \\N as a placeholder for missing values. "
     "This causes a critical problem: pandas reads \\N-containing columns as text (object dtype) "
     "instead of numbers, hiding the true missing values. "
     "Figure 1 shows the extent of the problem.")

fig(doc, "fig01_sentinel_heatmap.png",
    "Figure 1. \\N counts per table and column. pandas found 0 missing values in raw results, "
    "but 122,887 \\N strings are present. The heatmap shows which columns are most affected.", 5.5)

para(doc,
     "After replacing all \\N strings with a proper missing value (NaN), the following cleaning steps "
     "were applied (all on copies; raw data is unchanged):")

bullet(doc, "Nine columns converted from text to numeric (e.g., results.position, results.milliseconds, results.fastestLapSpeed).")
bullet(doc, "Dates (races.date, drivers.dob) parsed to datetime objects.")
bullet(doc, "Qualifying and pit-stop times (q1–q3, lap_times.time, pit_stops.duration) converted from 'M:SS.mmm' format to decimal seconds. The parser matched millisecond columns to within rounding in 100% of rows.")
bullet(doc, "Twenty unused columns dropped (mainly session date/time columns in races that were over 90% missing, plus URL columns and the results.time column whose mixed format made it unusable).")
bullet(doc, "One impossible qualifying time found and corrected: a Q1 time of 16:42.640 (1,002.6 s) in the 1995 Japanese GP, where the session median was 101.5 s. The rule blanks any qualifying time more than twice the session median. Only this one row was affected.")
bullet(doc, "Two category-spelling mismatches fixed: the Las Vegas Strip circuit was stored as 'United States' instead of 'USA' (1 row), and one driver's nationality was 'Argentinian' instead of 'Argentine' (1 row).")
bullet(doc, "Six sets of impossible or contradictory values corrected across 5 tables: 2 classified drivers with no position restored from positionText (2005 Australian GP); 18 race-time records blanked after the 2024 Belgian GP disqualification swapped the race time for a time gap; 12 fastest-lap records blanked where the lap was recorded after the driver's last lap (5 races 2008–2024); 7 pit-stop stop/lap numbers swapped (2024 Monaco GP); 7 constructor-result rows removed for a wrong team id; 10 qualifying team-id mismatches corrected from the race result (2015, 5 races).")

# 1.3 Duplicate handling
heading(doc, "1.3  Driver-Race Grain and Shared-Drive Duplicate Handling", 2)
para(doc,
     "The modelling table must have exactly one row per (raceId, driverId): one prediction per driver per race. "
     "Section 1.1.4 found 176 rows involving 85 driver-race pairs that appear more than once, all between 1950 and 1978. "
     "These are shared drives: in early Formula 1 a driver could take over a second car after their own retired. "
     "The dataset stores one row per car, so a driver who drove two cars gets two rows.")

para(doc,
     "Three candidate rules were compared (Table 2):")

table_from_rows(doc,
    ["Rule", "Description", "Podiums lost"],
    [
        ["A (chosen)", "Keep the row with the best finishing position (lowest positionOrder)", "0"],
        ["B", "Keep the first row (lowest resultId)", "16"],
        ["C", "Drop every duplicated pair entirely", "22"],
    ],
    caption="Table 2. Comparison of three duplicate-handling rules. Rule A loses no podiums."
)

bullet(doc, "Rule A was chosen: it answers our question correctly (did this driver reach the podium?), matches the dataset's own convention of crediting shared cars to both drivers, and keeps the car the driver drove the most laps in (confirmed in 100% of pairs).")
bullet(doc, "After applying Rule A: results went from 26,759 → 26,668 rows (91 rows removed). No podium was lost: 3,397 podium rows before → 3,395 after (two drivers had been counted twice; each is now counted once).")

# 1.4 PK/FK validation
heading(doc, "1.4  Primary-Key and Foreign-Key Validation", 2)
para(doc,
     "Before joining tables we verified that every link between tables is trustworthy. "
     "Table 3 summarises the checks.")

table_from_rows(doc,
    ["Check", "Result"],
    [
        ["Primary keys (14 tables)", "All unique and never missing"],
        ["Foreign keys (23 relationships)", "No missing references, no orphans"],
        ["Consistency within a race", "4 issues in results: shared drives (fixed), shared cars (correct history, kept), repeated grid slots that are not shared cars (66 races, recording errors, noted), position ≠ positionOrder (1 race, 1983)"],
        ["Cross-table consistency", "Detail tables match results; driver_standings keeps listing drivers in rounds they skipped (handled in Section 3); all drivers have the same team in qualifying and in the race (fixed)"],
    ],
    caption="Table 3. PK/FK validation summary."
)

para(doc,
     "The driver_standings table has 8,664 extra driver-race pairs: a driver who skips one round is still listed "
     "in the standings table with their points frozen from the previous race. This is not an error: 100% of such rows "
     "come between two of the driver's own races, or after their last race of the season. "
     "Consequence for Section 3: the standings row for the same raceId already includes that race's result, "
     "so only the previous round's standings row is used as a feature.")

# 1.5 Post-cleaning EDA
heading(doc, "1.5  Post-Cleaning EDA and Cleaning Impact", 2)

para(doc,
     "Figure 2 shows the impact of cleaning on missing values per table. "
     "Figure 3 shows three distributions that could not be plotted before cleaning "
     "(raw lap times, pit-stop durations, driver ages). "
     "Figure 4 confirms that cleaning did not distort the target.")

fig(doc, "fig04_cleaning_log.png",
    "Figure 2. Before cleaning, pandas sees almost no missing values (68 empty fields). "
    "After cleaning, real missing values are visible (e.g., 103,336 in results).", 5.5)

fig(doc, "fig06_distributions.png",
    "Figure 3. Three distributions after cleaning. Q1 lap time: median 87.1 s, range 53.9–153.9 s "
    "(spread reflects different circuit lengths). Pit-stop duration: median 23.6 s; clusters at 400–3,069 s "
    "are red-flag interruptions, not real stops. Driver age: 17.5–58.8 years, median 29.4.", 6.0)

fig(doc, "fig07_podium_rate_before_after.png",
    "Figure 4. Podium rate per season before and after cleaning. The two lines are identical from 1979 onward. "
    "Differences only appear in the 1950s (shared-drive rows removed). "
    "Overall rate: 12.69% → 12.73%. Cleaning did not distort the target.", 6.0)

para(doc,
     "Table 4 summarises what cleaning changed and what it means for modelling.")

table_from_rows(doc,
    ["What cleaning did", "Effect", "Consequence for modelling"],
    [
        ["Replaced 160,076 \\N placeholders", "Real missing values now visible (103,336 in results)", "Most gaps are by design → use missing-value flags (Section 3)"],
        ["Retyped 18 columns", "Times and dates are now computable", "Qualifying gaps must be computed as % off pole (lap times differ by circuit)"],
        ["Dropped 20 unused columns", "Smaller, cleaner tables", "—"],
        ["Fixed grain (−91 rows)", "One row per (raceId, driverId), no podium lost", "results is ready for the modelling table"],
        ["Fixed spellings and 56 impossible values", "Consistent values; reliable joins and filters", "Country joins (Q2) and team joins (Q3) are trustworthy"],
    ],
    caption="Table 4. Cleaning impact summary."
)

page_break(doc)

# =============================================================================
# SECTION 2 – DATA-ENGINEERING QUESTIONS
# =============================================================================
heading(doc, "2  Data-Engineering Questions", 1)

para(doc,
     "All three questions are answered from a single joined table (entries), which has one row per driver "
     "per race and combines results, races, circuits, drivers, qualifying, status, and constructors. "
     "The grain of entries is asserted before every analysis.")

# ── Q1 ───────────────────────────────────────────────────────────────────────
heading(doc, "2.1  Q1: Front-Row Starts to Podiums by Circuit and Era", 2)

heading(doc, "2.1.1  Question and method", 3)
para(doc,
     "Which circuits convert a front-row start into a podium most often, and does that ranking change after "
     "the 2014 hybrid era? We also distinguish qualifying position from grid position, since grid penalties "
     "can move drivers forward or backward after qualifying.")

bullet(doc, "Front-row start defined two ways: (a) grid position ∈ {1, 2}; (b) qualifying position ∈ {1, 2}.")
bullet(doc, "Conversion rate = podiums ÷ front-row starts, per circuit per era.")
bullet(doc, "Eras: 2003–2013 (pre-hybrid) vs. 2014–2024 (hybrid). Both eras have complete qualifying data (Section 1.5, Figure 5).")
bullet(doc, "Minimum sample filter: a circuit is only ranked in an era if it had at least 10 front-row starts there (roughly 5 races). This excludes Magny-Cours and Istanbul Park from the 2014–2024 era, as they dropped off the calendar. The filter leaves 14 circuits ranked in both eras.")

fig(doc, "fig02_qualifying_coverage.png",
    "Figure 5. Qualifying data coverage by year. Coverage is complete from 2003; "
    "the 1996–2002 period is incomplete. Eras 2003–2013 and 2014–2024 both have full data.", 5.5)

heading(doc, "2.1.2  Overall conversion rates", 3)
para(doc,
     "Overall, a front-row start converts into a podium more often in the hybrid era "
     "(Table 5 and Figure 6).")

table_from_rows(doc,
    ["Front-row definition", "Era", "Front-row starts", "Podiums", "Conversion rate"],
    [
        ["Grid", "2003–2013", "400", "272", "68.0%"],
        ["Grid", "2014–2024", "454", "345", "76.0%"],
        ["Qualifying", "2003–2013", "400", "269", "67.2%"],
        ["Qualifying", "2014–2024", "456", "336", "73.7%"],
    ],
    caption="Table 5. Overall front-row conversion rates by era and definition."
)

fig(doc, "fig08_q1_circuit_conversion_bar.png",
    "Figure 6. Front-row-to-podium conversion rate by circuit (grid definition), ranked by 2014–2024 rate. "
    "Only circuits with ≥10 front-row starts in both eras are shown (14 circuits). "
    "The hybrid era bars (orange) are higher than pre-hybrid bars (blue) for 11 of the 14 circuits.", 6.0)

heading(doc, "2.1.3  Circuit rankings and how they changed", 3)
para(doc,
     "Table 6 lists the top-5 circuits per era under each definition. "
     "Figure 7 shows how far each circuit moved between the two eras.")

table_from_rows(doc,
    ["Rank", "2003–2013 (grid)", "2014–2024 (grid)", "2003–2013 (qualifying)", "2014–2024 (qualifying)"],
    [
        ["1", "Magny-Cours 92%", "Suzuka 89%", "Magny-Cours 92%", "Suzuka 89%"],
        ["2", "Istanbul Park 79%", "Yas Marina 86%", "Istanbul Park 79%", "Monaco 85%"],
        ["3", "Monza 77%", "Monaco 85%", "Silverstone 77%", "Barcelona 82%"],
        ["4", "Monaco 77%", "Barcelona 82%", "Monza 73%", "Spa 82%"],
        ["5", "Silverstone 73%", "Spa 82%", "Spa 72%", "Yas Marina 82%"],
    ],
    caption="Table 6. Top-5 circuits by front-row conversion rate per era, by grid and qualifying definition."
)

fig(doc, "fig09_q1_rank_changes.png",
    "Figure 7. Rank changes between eras (grid definition, 14 circuits ranked in both). "
    "Positive = moved up (better rank in hybrid era); negative = moved down. "
    "Yas Marina moved up 8 places (60% → 86%), Interlagos up 6; Monza dropped 9 places (77% → 73%).", 5.5)

heading(doc, "2.1.4  Answer", 3)
para(doc,
     "A Spearman rank correlation between the circuit rankings in the two eras gives "
     "ρ = 0.30 (p = 0.29). "
     "This indicates no statistically significant rank consistency between eras: the pre-hybrid ranking "
     "is a poor predictor of the hybrid-era ranking. "
     "The non-significant p-value also reflects a small-sample caveat: each circuit's rate rests on "
     "only 10–24 front-row starts per era, so one podium more or less can shift a circuit's rank "
     "by several places. The qualitative conclusion — that the ranking changed substantially — "
     "is clear from the data; the exact magnitude of change cannot be precisely estimated.", italic=False)

bullet(doc, "11 of the 14 circuits convert better in the hybrid era; Bahrain is unchanged; Monza and Hungaroring convert worse.")
bullet(doc, "Biggest risers (grid): Yas Marina +8 places (60% → 86%), Interlagos +6 (59% → 79%).")
bullet(doc, "Biggest fallers (grid): Monza −9 places (77% → 73%), Hungaroring −5 (falls to last, 64% → 59%).")
bullet(doc, "Qualifying vs. grid definition: rank correlation ρ = 0.94 (2003–2013) and 0.88 (2014–2024) between the two definitions within the same era. The choice of definition changes a few percentage points but not which circuits top the table.")

heading(doc, "2.1.5  Grain, missing data, and pre-race cutoff", 3)
bullet(doc, "Grain: entries has one row per driver per race (asserted). A front-row start is one such row; the rate aggregates those rows per circuit and era.")
bullet(doc, "Missing data: grid is never missing; grid = 0 (pit-lane start or non-qualifier) is never a front-row start. The qualifying position is missing for 24 of the 8,970 entries in 2003–2024; those rows drop only from the qualifying-definition analysis.")
bullet(doc, "Pre-race cutoff: both the front-row slot (grid or qualifying) and the podium are observable facts — the first before the race, the second after. This is a descriptive historical question, so using the outcome is correct. For the model it shows that grid and qualifying position are strong, legitimate pre-race features (about 70–76% of front-row starters reach the podium).")

# ── Q2 ───────────────────────────────────────────────────────────────────────
heading(doc, "2.2  Q2: Home-Race Podium Advantage", 2)

heading(doc, "2.2.1  Question and method", 3)
para(doc,
     "Do drivers podium more often when racing at a circuit in their home country, after controlling for "
     "starting position? Starting position is the strongest predictor of a podium (Section 1.1). "
     "If home drivers simply start further forward, a raw home-vs-away comparison would show a spurious "
     "'home advantage' that is really a grid advantage. We therefore compare drivers who started from "
     "similar grid positions.")

bullet(doc, "Home race: driver nationality matches circuit country (not the race name — the San Marino GP at Imola counts as a home race for Italians).")
bullet(doc, "Rows used: drivers who actually started (grid > 0, not F/W), all seasons 1950–2024, excluding the 11 Indianapolis 500 races (1950–1960): a different event whose field was almost entirely American drivers who raced no other Grand Prix.")
bullet(doc, "Control: grid groups P1, P2–3, P4–6, P7–10, P11+. Home vs. away podium rates are compared within each group.")

heading(doc, "2.2.2  Results", 3)
para(doc,
     "Without controlling for grid position, home drivers look worse: 12.0% podium rate at home "
     "vs. 13.9% away. This is because 59% of home starts came from P11 or lower, vs. 54% of away starts — "
     "home races are more concentrated in the back of the grid, not in the front.")

fig(doc, "fig10_q2_home_by_grid_group.png",
    "Figure 8. Podium rate for home vs. away drivers within the same grid group. "
    "Differences are small and inconsistent in direction: home drivers do slightly better from P2–3 (+4.3 pp) "
    "and P4–6 (+1.1 pp), but slightly worse from P1 (−3.7 pp), P7–10 (−1.9 pp), and P11+ (−0.5 pp).", 5.5)

para(doc,
     "A logistic regression controlling for grid group and clustering standard errors by race gives "
     "the result in Table 7.")

table_from_rows(doc,
    ["Sample", "Starts", "Home starts", "Odds ratio", "95% CI", "p-value"],
    [
        ["All seasons (main)", "24,499", "1,923", "0.95", "0.81 – 1.13", "0.58"],
        ["2003–2024 (check)", "8,837", "363", "0.78", "0.52 – 1.16", "0.22"],
    ],
    caption="Table 7. Logistic-regression home-effect estimates, controlling for grid group."
)

heading(doc, "2.2.3  Answer", 3)
para(doc,
     "There is no evidence of a home advantage after controlling for grid position "
     "(OR 0.95, 95% CI 0.81–1.13, p = 0.58). "
     "The odds ratio of 0.95 means home drivers have slightly lower odds of a podium than away drivers "
     "in the same grid group, but the confidence interval comfortably includes 1.0, "
     "and the p-value of 0.58 is far above the conventional 0.05 threshold. "
     "Both samples (all seasons and 2003–2024) reach the same conclusion.")

bullet(doc, "Consequence for the model: a home-race flag was tested as a candidate feature (Section 3.5); it had an individual ROC-AUC of 0.50 (no signal) and was dropped from the feature set.")

heading(doc, "2.2.4  Grain, missing data, and pre-race cutoff", 3)
bullet(doc, "Grain: one row per driver per race (entries). Only drivers who actually started (grid > 0) are kept.")
bullet(doc, "Missing data: grid, nationality, and circuit country are never missing. 2,169 rows are excluded deliberately: non-starters (F/W), grid = 0 (pit-lane starts), and the Indianapolis 500.")
bullet(doc, "Pre-race cutoff: both home status (nationality, circuit country) and grid position are known before the race starts. This is a descriptive analysis; using the podium outcome is correct here.")

# ── Q3 ───────────────────────────────────────────────────────────────────────
heading(doc, "2.3  Q3: Constructor Mechanical-Retirement Rates 2014–2021 vs. 2022–2024", 2)

heading(doc, "2.3.1  Question and method", 3)
para(doc,
     "Which constructors have the highest mechanical-retirement rate in 2014–2021 vs. 2022–2024? "
     "A mechanical retirement is a race start that ended early because a component of the car failed. "
     "Crashes, driver decisions, and regulation decisions (disqualifications) do not count.")

para(doc,
     "Each of the 139 status codes used in the dataset was assigned to one of eight categories "
     "(Table 8 shows the mechanical category). Only the mechanical category counts as a retirement. "
     "The 50 'Retired' codes (no cause recorded) are excluded from the main count and tested separately "
     "in a robustness check.")

table_from_rows(doc,
    ["Category", "Count in 2014–2024", "Status codes included (sample)"],
    [
        ["mechanical", "388", "Engine, Gearbox, Brakes, Suspension, Hydraulics, Power Unit, Electrical, Turbo, Battery, ERS, Transmission, Clutch, Driveshaft, Throttle, Steering, and 26 others"],
        ["crash / contact", "308", "Collision, Accident, Collision damage, Spun off, Damage, Debris"],
        ["finished", "3,825", "Finished (plus all '+n Lap(s)' codes)"],
        ["pit stop / team error", "15", "Wheel, Wheel nut, Out of fuel"],
        ["tyre", "~", "Puncture, Tyre"],
        ["driver", "3", "Illness"],
        ["regulation", "~", "Disqualified, Excluded"],
        ["unknown cause", "50", "Retired (no cause recorded)"],
    ],
    caption="Table 8. Status-to-category mapping (2014–2024). 41 status codes map to 'mechanical'."
)

heading(doc, "2.3.2  Results", 3)
para(doc,
     "The overall mechanical-retirement rate fell from 9.0% of starts in 2014–2021 to 5.9% in 2022–2024. "
     "Table 9 shows the full breakdown for all teams with ≥40 starts in a period. "
     "Figure 9 shows the comparison visually.")

fig(doc, "fig11_q3_mechanical_rates.png",
    "Figure 9. Mechanical-retirement rates per constructor, 2014–2021 (blue) vs. 2022–2024 (orange). "
    "Teams are sorted by 2014–2021 rate. Missing bars mean a team did not qualify in that period "
    "(Lotus F1 left F1 after 2015; RB F1 Team entered only in 2024).", 6.0)

table_from_rows(doc,
    ["Constructor", "2014–2021 rate", "Mechanical / starts", "2022–2024 rate", "Mechanical / starts", "Change (pp)"],
    [
        ["Lotus F1", "18.7%", "14 / 75", "—", "—", "—"],
        ["Toro Rosso", "16.1%", "39 / 242", "—", "—", "—"],
        ["Renault", "13.6%", "27 / 199", "—", "—", "—"],
        ["McLaren", "13.0%", "41 / 315", "3.7%", "5 / 136", "−9.3"],
        ["Red Bull", "10.7%", "34 / 318", "3.7%", "5 / 136", "−7.0"],
        ["Sauber", "10.6%", "21 / 199", "2.1%", "1 / 48", "−8.5"],
        ["AlphaTauri", "9.1%", "7 / 77", "8.0%", "7 / 88", "−1.1"],
        ["Alpine F1 Team", "9.1%", "4 / 44", "10.4%", "14 / 135", "+1.3"],
        ["Haas F1 Team", "7.5%", "18 / 240", "5.2%", "7 / 135", "−2.3"],
        ["Williams", "7.2%", "23 / 319", "6.0%", "8 / 134", "−1.2"],
        ["Ferrari", "4.7%", "15 / 318", "5.2%", "7 / 134", "+0.5"],
        ["Aston Martin", "2.3%", "1 / 44", "5.3%", "7 / 133", "+3.0"],
        ["Mercedes", "3.8%", "12 / 320", "4.4%", "6 / 136", "+0.7"],
        ["Alfa Romeo", "3.3%", "4 / 120", "12.5%", "11 / 88", "+9.2"],
        ["RB F1 Team", "—", "—", "4.2%", "2 / 48", "—"],
    ],
    caption="Table 9. Mechanical-retirement rates per constructor and period. Teams with <40 starts in a period are not ranked. Toro Rosso and Renault did not race under those names in 2022–2024."
)

heading(doc, "2.3.3  Answer", 3)
para(doc,
     "Mechanical failures became rarer overall (9.0% → 5.9%).")
bullet(doc, "2014–2021 highest: Lotus F1 18.7% (14 of 75 starts), Toro Rosso 16.1% (39 of 242), Renault 13.6% (27 of 199).")
bullet(doc, "2022–2024 highest: Alfa Romeo 12.5% (11 of 88 starts), Alpine 10.4% (14 of 135), AlphaTauri 8.0% (7 of 88).")
bullet(doc, "Biggest improvements: McLaren (13.0% → 3.7%), Sauber (10.6% → 2.1%), Red Bull (10.7% → 3.7%).")
bullet(doc, "Biggest increases: Alfa Romeo (+9.2 pp), Aston Martin (+3.0 pp).")
bullet(doc, "In 2022–2024, the front-running teams (Red Bull, McLaren, Mercedes, Ferrari) all stay at or below 5.2%.")
bullet(doc, "Robustness check: counting the 50 'Retired' codes as mechanical does not change the top team in either period. Only lower positions shift slightly, mostly for teams with very few starts.")
bullet(doc, "Caution: counts in 2022–2024 are small (e.g., Alfa Romeo: 11 failures from 88 starts). One or two extra failures move the rate by 1–2 percentage points.")

heading(doc, "2.3.4  Grain, missing data, and pre-race cutoff", 3)
bullet(doc, "Grain: one row per driver per race (entries). A two-car team has two rows per race.")
bullet(doc, "Missing data: status is never missing. All status codes used in 2014–2024 have a category (verified). Drivers who never started (F/W, 'Withdrew') are not counted as starts.")
bullet(doc, "Pre-race cutoff: the retirement status is only known after the race. This is correct for a descriptive question. For the predictive model, only a team's past mechanical-retirement rate (previous races) is used as a feature — the current race's outcome is never seen (Section 3).")

page_break(doc)

# =============================================================================
# SECTION 3 – FEATURE SELECTION & ENGINEERING
# =============================================================================
heading(doc, "3  Feature Selection and Engineering", 1)

para(doc,
     "The split (train / validation / test) is fixed before any feature choices, "
     "so all data-driven decisions (window lengths, gap definitions, which features to keep, "
     "imputation values) are made on training seasons only. "
     "The test seasons never influence the feature set.")

# 3.1 Modelling table
heading(doc, "3.1  Modelling Table and Target", 2)
para(doc,
     "The modelling table has one row per driver per race, built from cleaned results "
     "(already unique per (raceId, driverId) after Section 1.3). "
     "Seasons 2003–2024 are used: qualifying data is complete only from 2003 (Figure 5). "
     "Drivers who never started (positionText F/W, status 'Withdrew', 'Did not qualify', "
     "'Did not prequalify') are removed — 64 rows removed, none with a podium.")

table_from_rows(doc,
    ["Statistic", "Value"],
    [
        ["Modelling rows", "8,906"],
        ["Races", "428"],
        ["Podium rows (positionOrder ≤ 3)", "1,284"],
        ["Podium rate", "14.4%"],
        ["Non-starters removed", "64 (none had a podium)"],
        ["Every race has exactly 3 podium rows", "Yes (asserted)"],
    ],
    caption="Table 10. Modelling table summary."
)

para(doc,
     "The podium rate varies slightly by season because the field size changes "
     "(about 19–24 cars): with 3 fixed podium places, a 24-car field gives ~12.5% vs. ~15% for 20 cars. "
     "The class imbalance (~1 in 7 rows) is why PR-AUC and F1 are the primary metrics in Section 4.")

# 3.2 Pre-race cutoff
heading(doc, "3.2  Pre-Race Prediction Cutoff and Leakage Audit", 2)
para(doc,
     "A prediction is made after qualifying and before the race starts. "
     "A field is a legal feature only if its value is known at that moment. "
     "Current-race results, points, laps, status, and post-race standings are leakage. "
     "Two fields require special care:")

bullet(doc, "results.grid lives in the results table but is the official starting grid, fixed before the start. It is a legal pre-race feature.")
bullet(doc, "driver_standings for the same raceId looks like the championship before the race, but Section 1.4 showed it already contains the race's result. Only the previous round's standings row is allowed.")

para(doc,
     "Table 11 confirms the leakage problem empirically: points from the current race give ROC-AUC 0.97 "
     "because a podium always scores points. The pre-race grid gives 0.91 — strong and legal.")

table_from_rows(doc,
    ["Field", "ROC-AUC", "PR-AUC", "Legal?"],
    [
        ["points (this race)", "0.970", "0.873", "No — leakage"],
        ["laps (this race)", "0.634", "0.206", "No — leakage"],
        ["championship position, same raceId", "0.932", "0.651", "No — leakage"],
        ["championship position, previous round", "0.892", "0.543", "Yes"],
        ["grid (pre-race)", "0.910", "0.630", "Yes"],
    ],
    caption="Table 11. Leakage check: current-race fields score suspiciously high. Only the previous-round standings and the pre-race grid are legal features."
)

# 3.3 Data split
heading(doc, "3.3  Training, Validation, and Test Split", 2)
para(doc,
     "A temporal (season-based) split is used, not a random row split.")

table_from_rows(doc,
    ["Set", "Seasons", "Races", "Rows", "Podium rate"],
    [
        ["Train", "2003–2018", "300", "6,362", "14.1%"],
        ["Validation", "2019–2021", "60", "1,193", "15.1%"],
        ["Test", "2022–2024", "68", "1,351", "15.1%"],
    ],
    caption="Table 12. Dataset split by season."
)

para(doc,
     "Reasons for a temporal split (Figure 10):")
bullet(doc, "It reflects real use: the model predicts upcoming races from past data. A random split would train on 2024 races and test on 2005 races, which does not match any deployment scenario.")
bullet(doc, "A race must stay in one set: the 3 podium places per race are shared by the drivers of that race, so the rows are not independent. A random split scatters each race across all three sets.")
bullet(doc, "The test set is a genuine change of era: 2022 introduced new car regulations (ground-effect cars). Testing there is harder than testing on a random sample, giving an honest estimate of performance on future seasons.")
bullet(doc, "A random 70/15/15 split would place 100% of the test races' drivers in training and use 69% of 2022–2024 rows for training — evaluating the model on data it effectively already saw.")

fig(doc, "fig13_split_comparison.png",
    "Figure 10. Season split vs. random split. With a random split, 100% of the test races also have "
    "drivers in the training set, and 69% of the 2022–2024 rows would be used for training. "
    "The season split prevents both problems.", 6.0)

# 3.4 Feature construction
heading(doc, "3.4  Feature Construction", 2)

para(doc,
     "All candidate features are built from information known at the pre-race cutoff. "
     "Post-race results enter only through past_mean(..., shift=1), which removes the current race "
     "from any rolling calculation, and through the previous round's standings (never the same raceId).")

para(doc, "Two construction choices were made by trial on training seasons only:")

bullet(doc,
       "Form window N = 10 races (Figure 11). ROC-AUC rises steeply from N=1 to N=5, then flattens: "
       "from N=10 to N=20 the gain is less than 0.01 AUC. Ten races (roughly half a season) "
       "captures almost all the signal while reacting twice as fast as N=20 to real changes "
       "(driver switching teams, new car update).")

bullet(doc,
       "Qualifying gap: best-lap gap (gap from driver's best lap in any session to the session's "
       "fastest time, expressed as %). Compared to Q1-gap only: best-lap ROC-AUC 0.89 vs. Q1 0.83 "
       "(PR-AUC 0.59 vs. 0.45). In the knock-out format (since 2006) top drivers conserve tyres in Q1; "
       "their Q1 time understates their real pace. Both definitions are identical for 2003–2005 (single lap).")

fig(doc, "fig14_form_window.png",
    "Figure 11. Single-feature ROC-AUC of the three form features vs. form window N (training seasons only). "
    "Score flattens after N=10; N=20 adds less than 0.01 AUC.", 5.5)

# 3.5 Feature selection
heading(doc, "3.5  Feature Selection", 2)

para(doc,
     "Seventeen candidate features were built in six families. "
     "Two kinds of evidence drive selection: (1) relevance — does the feature separate podium from "
     "non-podium rows on its own? (2) redundancy — does it repeat information another feature already carries?")

fig(doc, "fig15_single_feature_auc.png",
    "Figure 12. Individual feature ROC-AUC on training seasons. Qualifying, grid, standings, and form "
    "features are strong (0.86–0.91). Reliability and context are weaker but informative (0.66–0.70). "
    "home_race (0.50) and pit_lane_start (0.50) carry no signal.", 5.5)

fig(doc, "fig16_podium_rate_by_decile.png",
    "Figure 13. Podium rate by decile for eight candidate features (training seasons). "
    "Seven features show a monotonic relationship. career_starts is non-monotonic: "
    "podium rate peaks around 190 starts then falls for veterans in slow cars, "
    "a pattern a linear model cannot fit directly.", 6.0)

fig(doc, "fig18_spearman_heatmap.png",
    "Figure 14. Spearman rank-correlation matrix for all 17 candidates (training seasons). "
    "Four pairs have |ρ| ≥ 0.90 and are nearly copies: grid vs. qualifying position (0.97), "
    "driver championship position vs. points share (0.95), team championship position vs. team points share (0.92), "
    "and driver vs. team points share (0.92).", 5.5)

fig(doc, "fig17_grid_penalty.png",
    "Figure 15. Grid-penalty analysis. Among drivers with the same qualifying position, those moved back "
    "reach the podium far less often: from P2, 25% vs. 64%; from P3, 29% vs. 51%. "
    "This conditional signal justifies keeping grid_penalty despite its weak individual AUC (0.56).", 5.5)

para(doc, "Selection rule:")
bullet(doc, "Drop any candidate with individual ROC-AUC below 0.55, unless it carries demonstrable conditional information.")
bullet(doc, "Drop any candidate with |Spearman ρ| ≥ 0.90 to an already-kept feature (keep the stronger one).")

para(doc, "Result: 12 of the 17 candidates kept. The 5 dropped ones:")
bullet(doc, "grid_position: near-copy of quali_position (ρ = 0.97). Keeping (quali_position, grid_penalty) instead of (quali_position, grid_position) replaces two near-identical columns with two nearly uncorrelated ones (ρ = −0.21), each with its own meaning.")
bullet(doc, "driver_points_share: copy of both team_points_share (0.92) and driver_champ_pos (0.95).")
bullet(doc, "team_champ_pos: copy of team_points_share (0.92).")
bullet(doc, "home_race: ROC-AUC 0.50, confirms Q2 finding.")
bullet(doc, "pit_lane_start: ROC-AUC 0.50; the pit-lane-start information is already encoded as a large grid_penalty.")

# 3.6 Selected feature set
heading(doc, "3.6  Selected Feature Set and Leakage-Safety", 2)

para(doc,
     "Table 13 documents all 12 selected features. Each is computable before the race starts.")

table_from_rows(doc,
    ["Group", "Feature", "What it measures", "How it is computed", "Why leakage-safe"],
    [
        ["qualifying", "quali_position", "Official qualifying rank", "From qualifying table", "Qualifying is finished before the race"],
        ["qualifying", "quali_gap_pct", "% gap of driver's best lap to pole time", "Best Q1/Q2/Q3 lap minus pole time, divided by pole time", "Qualifying is finished before the race"],
        ["grid", "grid_penalty", "Places lost (+) or gained (−) after qualifying (= grid − quali_position)", "Both grid and qualifying result fixed before start", "Both are fixed before the race starts"],
        ["standings", "driver_champ_pos", "Driver's championship position entering the race", "Previous round of driver_standings (never same raceId)", "Previous round known before race start"],
        ["standings", "team_points_share", "Team's points ÷ championship leader's points", "Previous round of constructor_standings", "Previous round known before race start"],
        ["form", "driver_podium_rate", "Fraction of driver's last 10 races that ended on the podium", "past_mean with shift(1) over last 10 races", "shift(1) removes the current race; only past races used"],
        ["form", "driver_avg_finish", "Driver's mean finishing position over last 10 races", "past_mean with shift(1) over last 10 races", "shift(1) removes the current race"],
        ["form", "team_podium_rate", "Team's podium fraction over last 10 races", "past_mean with shift(1) over last 10 races", "shift(1) removes the current race"],
        ["reliability", "team_finish_rate", "Fraction of team's last 10 races that finished (no retirement)", "past_mean with shift(1)", "shift(1) removes the current race"],
        ["reliability", "team_mech_dnf_rate", "Fraction of team's last 10 races ending with a mechanical failure", "past_mean with shift(1)", "shift(1) removes the current race"],
        ["context", "career_starts", "Number of F1 starts before this race", "Count of entries before this race", "Only entries before this race are counted"],
        ["context", "driver_age", "Driver's age on race day", "Race date − date of birth", "Both known before the race"],
    ],
    caption="Table 13. Selected feature set with leakage-safety justification."
)

# 3.7 Preprocessing
heading(doc, "3.7  Preprocessing", 2)

para(doc,
     "All preprocessing steps are fitted on training seasons only. "
     "The same fitted pipeline is applied unchanged to validation and test. "
     "Fitting on all rows would let the test seasons shape the imputation medians and scaling "
     "parameters — a form of leakage through preprocessing.")

para(doc, "Pipeline steps:")
bullet(doc, "Missing values → median imputation (training medians) plus one binary missing-value flag per distinct missingness reason. There are 5 reasons (Table 14). Adding one flag per reason (not one per column) avoids duplicate flags for columns missing for the same reason.")
bullet(doc, "log1p transformation applied only to quali_gap_pct (training skewness 4.63): most drivers are within 2% of pole, but a few sessions give gaps up to 37.8%. After standardisation these outliers would sit more than 10 standard deviations from the mean; log1p pulls them in while keeping 0 (pole) at 0 and preserving the ordering.")
bullet(doc, "Standardisation (mean 0, std 1 on training). Required for logistic regression and the neural network; applied to all features for consistency.")

table_from_rows(doc,
    ["Missing-value flag", "Features it covers", "Root cause", "Share missing (train)"],
    [
        ["missingindicator_driver_champ_pos", "All 4 standings features", "Round 1: no previous round yet", "5.2%"],
        ["missingindicator_driver_podium_rate", "driver_podium_rate, driver_avg_finish", "Driver's debut race: no history", "1.1%"],
        ["missingindicator_team_podium_rate", "team_podium_rate, team_finish_rate, team_mech_dnf_rate", "Team's first race under this constructor id", "0.5%"],
        ["missingindicator_quali_position", "quali_position, grid_penalty", "No qualifying row for this driver (24 entries)", "0.3%"],
        ["missingindicator_quali_gap_pct", "quali_gap_pct", "No qualifying time set", "1.7%"],
    ],
    caption="Table 14. Five missing-value flags. One flag per cause, not per column."
)

fig(doc, "fig20_preprocessing_distributions.png",
    "Figure 16. Feature distributions before (grey) and after (blue) preprocessing, for four features. "
    "After preprocessing: all features have mean ≈ 0 and std ≈ 1 on training. "
    "The log1p transform compresses the right tail of quali_gap_pct (largest gap: 13 std before, 4.5 after). "
    "Shapes are unchanged for the other features; only the scale changes. "
    "Missing values appear as a spike at the imputed median value.", 6.0)

para(doc, "After preprocessing, the model receives 17 inputs: 12 features + 5 missing-value flags. "
         "No missing values remain in any split.")

page_break(doc)

# =============================================================================
# SECTION 4 – PREDICTIVE MODELLING
# =============================================================================
heading(doc, "4  Predictive Modelling", 1)

para(doc,
     "Four models are trained on the same 8,906 driver-race rows and the same 17 inputs (12 features + 5 flags). "
     "The simple logistic regression is the reference baseline; "
     "tuned logistic regression and XGBoost are the two statistical models; "
     "a shallow Keras neural network is the third model family.")

heading(doc, "4.1  Evaluation Protocol", 2)
bullet(doc, "Primary metric: PR-AUC (average precision) on validation. It is more informative than ROC-AUC at ~14% positive rate because it focuses on how well the model ranks true podium finishers above non-finishers. ROC-AUC is the secondary metric.")
bullet(doc, "All metrics (ROC-AUC, PR-AUC, F1) are computed on all three splits. Test metrics are computed only after all selections are frozen.")
bullet(doc, "Hyperparameters are selected to maximise validation AP. Thresholds are selected to maximise validation binary F1 over distinct probability values. Test split is never used for selection.")
bullet(doc, "Note: the model comparison table shows F1 at the tuned threshold. Individual Precision and Recall at that threshold are not available in the notebook outputs.")

heading(doc, "4.2  Models", 2)

heading(doc, "Baseline: Simple Logistic Regression", 3)
para(doc, "L2 regularisation (C = 1), no class weighting, all 17 inputs. "
         "Estimates linear log-odds associations. Cannot follow the non-linear career-experience pattern "
         "or learn feature interactions, but establishes what a simple statistical model achieves.")

heading(doc, "Enhanced Logistic Regression", 3)
para(doc, "Grid search over C ∈ {0.01, 0.1, 1, 10} × class_weight ∈ {None, 'balanced'} (8 configurations). "
         "Best: C = 10, no class weighting (validation AP 0.7364 vs. 0.7362 for baseline). "
         "The improvement over the baseline is negligible, confirming that logistic regression "
         "is at its ceiling with this feature set.")

heading(doc, "XGBoost", 3)
para(doc, "Gradient-boosted trees; learns non-linear qualifying effects and feature interactions. "
         "Grid search over max_depth ∈ {2, 3} × min_child_weight ∈ {1, 5, 10} × "
         "scale_pos_weight ∈ {1, neg/pos ratio} (12 configurations). "
         "Best: max_depth = 3, min_child_weight = 5, scale_pos_weight = 1, 68 trees (early-stopped on validation). "
         "Selected as the preferred model by validation AP.")

heading(doc, "Keras Shallow Neural Network (17 → 32 → 16 → 1)", 3)
para(doc, "Two ReLU hidden layers + sigmoid output. Architecture: 17 inputs → Dense(32, ReLU) → Dense(16, ReLU) → Dense(1, sigmoid). "
         "1,121 trainable parameters. L2 kernel regularisation (1e-4) on both hidden layers. "
         "Adam optimiser (lr = 0.001), binary cross-entropy, batch size 64, max 300 epochs. "
         "Early stopping on validation loss (patience = 20). Training-only preprocessing reused.")

heading(doc, "4.3  Model Comparison", 2)

fig(doc, "fig21_roc_pr_curves.png",
    "Figure 17. ROC curves (top row) and precision-recall curves (bottom row) for all four models, "
    "on validation (left) and test (right). XGBoost achieves the highest validation PR-AUC (0.751).", 6.0)

table_from_rows(doc,
    ["Model", "Train ROC-AUC", "Val ROC-AUC", "Test ROC-AUC", "Train AP", "Val AP", "Test AP", "Val F1", "Test F1", "Threshold"],
    [
        ["Baseline LR", "0.9302", "0.9392", "0.9334", "0.6866", "0.7362", "0.6968", "0.7358", "0.6522", "0.2313"],
        ["Enhanced LR", "0.9302", "0.9392", "0.9334", "0.6864", "0.7364", "0.6968", "0.7341", "0.6534", "0.2301"],
        ["XGBoost", "0.9427", "0.9390", "0.9346", "0.7231", "0.7509", "0.6906", "0.7371", "0.6606", "0.3691"],
        ["Keras NN", "0.9413", "0.9333", "0.9301", "0.7126", "0.7083", "0.7019", "0.7259", "0.6358", "0.3216"],
    ],
    caption="Table 15. Full model comparison. AP = PR-AUC (average precision). Threshold is selected on validation F1. Bold = selected model."
)

para(doc, "Interpretation:")
bullet(doc, "XGBoost achieves the highest validation AP (0.751) and is selected as the preferred model.")
bullet(doc, "All models are close in validation ROC-AUC (0.933–0.939), reflecting the strong signal from qualifying features.")
bullet(doc, "On the test set XGBoost AP drops to 0.691 (−0.060 from validation). The Keras NN drops only −0.006 but scored lower on validation to begin with. The 2022 regulation change and reliability drift documented in Section 2.3 are plausible contributing factors; they are not proven causes.")
bullet(doc, "Training AP is below validation AP for all logistic models and XGBoost (negative optimism gap). For Keras NN training AP slightly exceeds validation (0.043 difference), suggesting mild overfitting.")
bullet(doc, "The enhanced LR adds essentially no improvement over the baseline (ΔAP = +0.0002 on validation), showing that regularisation strength does not constrain the linear model at this scale.")

page_break(doc)

# =============================================================================
# SECTION 5 – EXPERIMENTS
# =============================================================================
heading(doc, "5  Experiments", 1)

para(doc,
     "All experiments use the same training (2003–2018) and validation (2019–2021) rows. "
     "Section 4's models, thresholds, feature set, and preprocessor remain unchanged. "
     "No test-set predictions are generated in this section.")

heading(doc, "5.1  Feature-Group Ablation (XGBoost)", 2)

para(doc,
     "One feature group is removed at a time; a fresh XGBoost model is trained with the remaining features "
     "using Section 4's selected hyperparameters (depth 3, min_child_weight 5, 68 trees fixed, "
     "no early stopping). "
     "Drop = full-reference AP − ablated AP. A positive drop means removing that group hurt performance.")

fig(doc, "fig23_ablation_results.png",
    "Figure 18. Feature-group ablation: validation AP drop when each group is removed. "
    "Qualifying features contribute the most (drop 0.089); all other groups contribute positively but by a smaller amount.", 5.5)

table_from_rows(doc,
    ["Group removed", "Features removed", "Validation AP", "AP drop", "F1 drop"],
    [
        ["None (reference)", "—", "0.7509", "—", "—"],
        ["qualifying", "quali_position, quali_gap_pct", "0.6618", "+0.089", "+0.040"],
        ["grid", "grid_penalty", "0.7162", "+0.035", "+0.004"],
        ["form", "driver_podium_rate, driver_avg_finish, team_podium_rate", "0.7316", "+0.019", "+0.013"],
        ["standings", "driver_champ_pos, team_points_share", "0.7337", "+0.017", "+0.006"],
        ["context", "career_starts, driver_age", "0.7396", "+0.011", "+0.002"],
        ["reliability", "team_finish_rate, team_mech_dnf_rate", "0.7397", "+0.011", "+0.002"],
    ],
    caption="Table 16. Feature-group ablation results (XGBoost, validation set). All groups contribute positively."
)

bullet(doc, "Qualifying is by far the most important group (removing it drops AP by 0.089). This is consistent with the EDA: 70–76% of front-row starters reach the podium.")
bullet(doc, "Grid (the penalty) contributes +0.035 AP despite its weak individual AUC (0.56), confirming the conditional signal shown in Figure 15.")
bullet(doc, "Form and standings contribute similarly (+0.019 and +0.017). Their overlap (Spearman ρ 0.78–0.89) means each adds somewhat redundant information; removing one while the other remains gives a smaller drop than removing both.")
bullet(doc, "Context and reliability groups have the smallest conditional contributions, though both are positive. They add value the other groups do not capture (career experience, mechanical-failure risk).")
bullet(doc, "Note: drops are conditional on the retained features and the fixed XGBoost configuration. They measure dependence, not causal importance.")

heading(doc, "5.2  Preprocessing-Order Experiments (Enhanced Logistic Regression)", 2)

para(doc,
     "The reference pipeline is log1p → median imputation → standardisation. "
     "Two variants swap the order of numeric steps (Table 17).")

table_from_rows(doc,
    ["Experiment", "Numeric order", "Max |input difference| from reference", "Validation AP change", "F1 change"],
    [
        ["Reference", "log → impute → scale", "0", "—", "—"],
        ["Order 1: impute before log", "impute → log → scale", "0 (identical)", "+0.000000", "+0.000000"],
        ["Order 2: scale before impute", "log → scale → impute", "0.069", "−0.000070", "+0.000000"],
    ],
    caption="Table 17. Preprocessing-order experiment results (Enhanced LR, validation set)."
)

bullet(doc, "Order 1 (impute then log) produces numerically identical inputs to the reference. This is because log1p is a monotonic transformation: for any value x, log1p(median(x)) = log1p(median(x)). When the median is the only value substituted, the log transformation commutes with median imputation — applying them in either order gives the same result for every row, observed or imputed.")
bullet(doc, "Order 2 (scale then impute) changes the transformed inputs (max absolute difference 0.069): scaling estimates the mean and standard deviation from observed-only values, so the imputed median sits at a slightly different scaled position than in the reference pipeline. The AP change is negligible (−0.000070, well below the 0.005 threshold used for assessing practical differences).")
bullet(doc, "Conclusion: the reference ordering is correct and robust. Imputing before or after log is equivalent; scaling before imputing shifts inputs by a small, practically irrelevant amount.")

page_break(doc)

# =============================================================================
# SECTION 6 – MODEL EXPLAINABILITY
# =============================================================================
heading(doc, "6  Model Explainability (XAI)", 1)

para(doc,
     "We explain Section 4's selected XGBoost model using two global methods "
     "(permutation importance and SHAP) and one local explanation. "
     "All explanations use the 1,193 validation rows (2019–2021); "
     "no retraining or test-set analysis occurs here.")

para(doc,
     "IMPORTANT: Feature importance is NOT proof that a feature causes podium finishes. "
     "A feature being important to the model means the model relies on it to make predictions. "
     "It does not mean that changing the feature would change a driver's real chance of a podium. "
     "Correlation and model reliance are not causation.",
     bold=True)

heading(doc, "6.1  Global Explanation: Permutation Importance", 2)

para(doc,
     "Each transformed input is shuffled independently across validation rows 20 times. "
     "Importance = original validation AP − mean AP after shuffling. "
     "Error bars show the standard deviation across 20 shuffles (not confidence intervals).")

fig(doc, "fig25_permutation_importance.png",
    "Figure 19. Permutation importance for XGBoost (validation set, 20 repeats). "
    "quali_position has by far the largest drop (+0.204 AP). "
    "quali_gap_pct (+0.035) and driver_podium_rate (+0.019) are next. "
    "Most flags have near-zero importance.", 5.5)

table_from_rows(doc,
    ["Rank", "Feature", "Mean AP drop", "Shuffle std"],
    [
        ["1", "quali_position", "0.2039", "0.0184"],
        ["2", "quali_gap_pct", "0.0355", "0.0158"],
        ["3", "driver_podium_rate", "0.0194", "0.0098"],
        ["4", "grid_penalty", "0.0187", "0.0057"],
        ["5", "team_points_share", "0.0118", "0.0109"],
        ["6", "driver_avg_finish", "0.0110", "0.0090"],
        ["7", "career_starts", "0.0082", "0.0089"],
        ["8", "driver_champ_pos", "0.0067", "0.0030"],
        ["9", "team_podium_rate", "0.0061", "0.0073"],
        ["10", "driver_age", "0.0057", "0.0070"],
        ["11", "team_finish_rate", "0.0039", "0.0034"],
        ["12", "missingindicator_driver_champ_pos", "0.0002", "0.0001"],
        ["13–17", "Remaining flags", "≈0.000", "—"],
    ],
    caption="Table 18. Permutation importance (XGBoost, 20 shuffles). Positive drop = model relies on this input."
)

heading(doc, "6.2  Global Explanation: SHAP", 2)

para(doc,
     "TreeSHAP attributes each prediction to individual inputs relative to a baseline. "
     "The bar chart ranks inputs by mean absolute SHAP value (in log-odds units). "
     "The beeswarm shows individual contributions: red = high input value pushes toward podium; "
     "blue = high input value pushes away.")

fig(doc, "fig26_shap_global.png",
    "Figure 20. SHAP global explanations. Left: mean |SHAP| bar chart. Right: beeswarm. "
    "quali_position is the dominant driver (mean |SHAP| 1.031 log-odds). "
    "A high quali_position value (= worse rank) pushes strongly away from a podium (blue, right). "
    "A high team_points_share (= stronger team) pushes toward a podium (red, left in beeswarm).", 6.0)

table_from_rows(doc,
    ["Rank", "Feature", "Mean |SHAP| (log-odds)"],
    [
        ["1", "quali_position", "1.031"],
        ["2", "quali_gap_pct", "0.348"],
        ["3", "team_points_share", "0.319"],
        ["4", "driver_podium_rate", "0.284"],
        ["5", "driver_avg_finish", "0.186"],
        ["6", "team_podium_rate", "0.165"],
        ["7", "driver_age", "0.059"],
        ["8", "career_starts", "0.054"],
        ["9", "grid_penalty", "0.034"],
        ["10", "driver_champ_pos", "0.032"],
        ["11", "team_finish_rate", "0.018"],
        ["12–17", "Flags and team_mech_dnf_rate", "<0.010"],
    ],
    caption="Table 19. SHAP feature ranking (mean absolute SHAP, log-odds units). Top three match permutation importance."
)

para(doc,
     "Permutation importance and SHAP agree on the top inputs: quali_position is dominant in both. "
     "They differ in the middle: SHAP ranks team_points_share 3rd (vs. 5th in permutation), while "
     "grid_penalty drops from 4th to 9th. "
     "This reflects the different quantities measured: permutation importance measures loss of AP when "
     "a feature is removed; SHAP measures the attribution of each feature's actual value to each prediction. "
     "Correlated features can share SHAP credit, and permutation importance can be masked by overlapping inputs. "
     "Neither scale can be directly compared to the other.")

heading(doc, "6.3  Local Explanation: Decision Boundary Example", 2)

para(doc,
     "The validation prediction closest to the frozen XGBoost threshold (0.3691) is chosen: "
     "Sebastian Vettel at the 2019 Monaco Grand Prix (raceId = 1015, driverId = 20). "
     "Probability = 0.3691, exactly at the threshold. Predicted: podium. Observed: podium (correct).")

para(doc,
     "Note: The notebook's Section 6.4 computed only this one local explanation from the validation set. "
     "A test-set (2022–2024) example and a misclassified-example (false positive/false negative) "
     "waterfall were requested but are not present in the notebook outputs. "
     "These would require re-running the XAI section with additional row selections.",
     italic=True)

table_from_rows(doc,
    ["Feature", "Pre-race value", "Interpretation"],
    [
        ["quali_position", "4", "Qualified 4th — competitive but not front row"],
        ["quali_gap_pct", "1.11%", "About 1.1% behind pole — typical for top-4"],
        ["grid_penalty", "0", "No penalty; starts from his qualified position"],
        ["driver_champ_pos", "4", "4th in the championship entering Monaco"],
        ["team_points_share", "0.558", "Ferrari has 55.8% of the championship leader's points"],
        ["driver_podium_rate", "0.40", "Reached the podium in 40% of his last 10 races"],
        ["driver_avg_finish", "3.9", "Average finish position of 3.9 in last 10 races"],
        ["team_podium_rate", "0.40", "Ferrari reached the podium in 40% of their last 10 races"],
        ["team_finish_rate", "0.95", "Ferrari finished 95% of their last 10 race starts"],
        ["team_mech_dnf_rate", "0.05", "Ferrari had 5% mechanical failures in last 10 races"],
        ["career_starts", "230", "230 F1 starts — very experienced driver"],
        ["driver_age", "34.2", "Age 34.2 — prime racing age"],
    ],
    caption="Table 20. Pre-race feature values for Vettel at the 2019 Monaco GP (local explanation example)."
)

fig(doc, "fig27_local_explanation.png",
    "Figure 21. SHAP waterfall for Vettel at the 2019 Monaco GP. "
    "The model starts at the SHAP expected log-odds and adds contributions from each feature. "
    "Red bars push toward a podium prediction; blue bars push away. "
    "Qualifying position (starting 4th at Monaco) and team strength (Ferrari's high points share) "
    "are the main drivers pushing toward a podium prediction.", 6.0)

para(doc,
     "The probability of 0.369 is exactly at the threshold (0.3691). The model's borderline confidence "
     "is reflected in the pre-race context: Vettel qualified 4th, not on the front row, but Monaco's "
     "narrow circuit strongly rewards starting position. "
     "The positive outcome (podium) confirms the model's assessment in this instance, "
     "but one correct prediction does not validate the model; that role belongs to the metrics in Section 4.")

page_break(doc)

# =============================================================================
# SECTION 7 – INFERENCE FUNCTION
# =============================================================================
heading(doc, "7  Inference Function", 1)

para(doc,
     "The predict_podium(record) function takes a single driver-race as a dictionary or pandas Series "
     "containing the 12 engineered pre-race features (unscaled, in their raw units). "
     "It applies Section 4's frozen preprocessing pipeline and selected XGBoost model, "
     "and returns the podium probability, the binary prediction (podium / not podium), "
     "and the decision threshold.")

para(doc, "Input contract:")
bullet(doc, "The 12 features in FEATURES (definitions in Table 13). Not raw CSV fields: qualifying gaps are percentages, rates are fractions, grid penalties are signed places, and historical values must exclude the current race.")
bullet(doc, "Omitted keys, None, NaN, pd.NA, or the sentinel \\N are treated as missing.")
bullet(doc, "Unknown keys are rejected to catch spelling mistakes and accidental outcome fields.")

heading(doc, "7.1  Demonstration", 2)

para(doc,
     "Two calls are shown in Table 21: the first validation driver-race with all 12 features available "
     "(raceId = 1011, driverId = 1, Lewis Hamilton), and the same record with "
     "the qualifying gap and championship/team standings set to missing "
     "(simulating a pre-qualifying prediction).")

table_from_rows(doc,
    ["Feature", "Complete record", "Partially missing record"],
    [
        ["quali_position", "3.0", "3.0"],
        ["quali_gap_pct", "0.369%", "missing"],
        ["grid_penalty", "0.0", "0.0"],
        ["driver_champ_pos", "2.0", "missing"],
        ["team_points_share", "1.000", "missing"],
        ["driver_podium_rate", "0.90", "0.90"],
        ["driver_avg_finish", "1.70", "1.70"],
        ["team_podium_rate", "0.65", "0.65"],
        ["team_finish_rate", "1.00", "1.00"],
        ["team_mech_dnf_rate", "0.00", "0.00"],
        ["career_starts", "230", "230"],
        ["driver_age", "34.23 years", "34.23 years"],
        ["— Output —", "", ""],
        ["Podium probability", "0.6055", "0.3916"],
        ["Threshold", "0.3691", "0.3691"],
        ["Prediction", "podium", "podium"],
    ],
    caption="Table 21. Inference function output for a complete and a partially-missing record. "
             "Removing qualifying gap and championship standings reduces confidence from 0.606 to 0.392, "
             "but the prediction (podium) is unchanged because the driver's form (podium rate 0.90, avg finish 1.7) "
             "and team strength (points share 1.0) are strong enough."
)

para(doc,
     "The complete call reproduces Section 4's stored probability for that driver-race "
     "(verified by an assertion in the notebook). "
     "The partially-missing call uses the training-fitted medians for the three missing features, "
     "and the five missing-value flags are set accordingly. "
     "The probability difference (0.606 → 0.392) reflects the model's reliance on qualifying and standings "
     "information for this particular record — it is not a measure of robustness to all missingness patterns.")

page_break(doc)

# =============================================================================
# SECTION 8 – LIMITATIONS
# =============================================================================
heading(doc, "8  Known Limitations", 1)

table_from_rows(doc,
    ["Limitation", "Description", "Impact"],
    [
        ["Historical qualifying coverage",
         "Qualifying data is incomplete for 1994–2002 and absent before 1994. The modelling table is restricted to 2003–2024.",
         "Results from the 1950–2002 era are used only for form/standing history; no model predictions are made for those seasons."],
        ["Era and regulation sensitivity",
         "The model is trained on 2003–2018 and tested on 2022–2024, which follows a major regulation change (ground-effect cars, 2022). Feature distributions and team competitiveness changed.",
         "Test AP (0.691) is lower than validation AP (0.751). Results may not generalise equally to future regulation changes."],
        ["Class imbalance",
         "~14.4% of rows are podiums (~1 in 7). Accuracy would be misleadingly high (~86% for always predicting 'not podium').",
         "PR-AUC and F1 are used as primary metrics. The tuned decision threshold (0.3691 for XGBoost) is not 0.5."],
        ["Shared drives / duplicate handling",
         "85 driver-race pairs appear twice in 1950–1978 due to shared drives. Rule A (keep best position) is applied.",
         "No impact on 2003–2024 modelling rows. The data-engineering answers (Q1–Q3) use pre-cleaned data; findings from 1950s races may reflect the cleaning choice."],
        ["Constructor renames",
         "When a team rebrands (e.g., Toro Rosso → AlphaTauri in 2020), the new name has a new constructor id with no prior history in the dataset.",
         "Form and reliability features are missing for the first race under a new id. The missing-value flag handles this; it does not affect teams mid-season."],
        ["Indianapolis 500 excluded",
         "The 11 Indianapolis 500 races (1950–1960) were World Championship rounds but a different competition. Excluded from Q2 analysis and removed as non-starts would obscure the home-advantage test.",
         "Small impact on the overall dataset; no impact on 2003–2024 modelling."],
        ["Grid = 0 (pit-lane starts)",
         "Grid = 0 encodes both pit-lane starts and non-qualifiers. The qualifying position is still available for these drivers; grid_penalty encodes the distance from qualifying to grid.",
         "No driver started from grid = 0 and reached the podium in the dataset. pit_lane_start was dropped as a feature (ROC-AUC 0.50)."],
        ["Validation reuse",
         "The validation set was used for hyperparameter selection, early stopping (XGBoost, NN), threshold selection, and explanation (Section 6). Its reported scores are selection estimates, not independent performance estimates.",
         "Only the test scores are independent. Section 4's interpretation notes this explicitly."],
        ["Single NN seed",
         "The neural network uses one random seed. Training variability is not quantified.",
         "NN results may vary across seeds. The selected model is XGBoost, which does not have this issue."],
    ],
    caption="Table 22. Known limitations."
)

page_break(doc)

# =============================================================================
# SECTION 9 – CONCLUSION
# =============================================================================
heading(doc, "9  Conclusion", 1)

para(doc,
     "This report describes a complete data-engineering and machine-learning pipeline "
     "for predicting F1 podium finishes from pre-race information. "
     "After cleaning 14 relational CSV tables (replacing 160,076 sentinel values, "
     "fixing 56 impossible records, and deduplicating 85 shared-drive pairs), "
     "we answered three data-engineering questions: "
     "front-row conversion rates rose from 68% to 76% after 2014 with no significant rank consistency "
     "between eras (ρ = 0.30); there is no evidence of a home-race advantage after controlling for "
     "grid position (OR = 0.95, p = 0.58); "
     "and mechanical failures became rarer overall (9.0% → 5.9%), "
     "though Alfa Romeo's rate jumped sharply in 2022–2024.")

para(doc,
     "The modelling table (8,906 rows, 428 races, 2003–2024) uses 12 leakage-safe features "
     "across qualifying, grid, standings, form, reliability, and context groups, "
     "plus 5 missingness flags. "
     "XGBoost achieved the highest validation PR-AUC (0.751) and was selected as the best model. "
     "Feature-group ablation confirms that qualifying features dominate (removing them drops AP by 0.089), "
     "while all other groups contribute positively in conditional ablation. "
     "XAI methods (permutation importance, SHAP) agree: qualifying position is the single most relied-upon input, "
     "with qualifying gap, team strength, and driver recent form next.")

para(doc,
     "The main limitation is era sensitivity: the model trained on 2003–2018 predicts 2022–2024 "
     "(new regulations, different competitive order) with AP 0.691 vs. 0.751 on validation. "
     "Future work could address this with rolling retraining as new seasons arrive.")

# ── save ──────────────────────────────────────────────────────────────────────
doc.save(OUT)
print(f"Saved: {OUT}")
