# Formula 1 for Newcomers: An Introduction to the Podium Prediction Project

Our model predicts, for every driver in a race, whether they finish in the top 3 (the podium), using only what is known after qualifying and before the race starts. To judge features, spot leakage, and explain results, every team member needs a working mental model of how Formula 1 works and how its rules shifted between 1950 and 2024.

Formula 1 is a world championship of single-seat racing cars, run every year since 1950. Each year is a **season** made of individual races (officially **Grands Prix**, e.g., the British Grand Prix), held at different **circuits** around the world.

**Drivers** are the people in the cars. **Constructors** are the teams that build and run the cars (Ferrari, McLaren, Mercedes, Red Bull). Today each constructor enters exactly two cars, so a modern race has about 20 drivers. In the 1950s to 1980s fields were much larger and far less uniform.

There are two championships each season, both decided by points:
* **Drivers' Championship:** points go to the individual driver.
* **Constructors' Championship (since 1958):** points of a team's cars are added together.

A **podium** is a finish in 1st, 2nd, or 3rd place, named after the stand where the top three receive trophies. Podiums are rare by design: about 3 of 20 drivers per race, so roughly 15% of rows in the modern era and far less in eras with 30+ entrants.

What decides who wins is a mix of car performance (the dominant factor in most eras), driver skill, starting position, strategy, reliability, and luck. That is why our features lean on grid position and constructor form, not just driver form.

---

## The Race Weekend

A modern race weekend runs Friday to Sunday, and our prediction is made in the gap between the grid being fixed and the lights going out.

*We may use everything up to the starting grid; the race is what we predict.*

```text
                                                prediction cutoff
                                                       |
[ Practice ] ---> [ Qualifying ] ---> [ Starting grid ] | ---> [ Race ] ---> [ Results ]
Setup runs;       Timed laps          Quali order      |      About 305 km;  Positions,
no points, not    decide the          plus penalties   |      top 3 finishers points, status,
in our dataset    starting order      and pit starts   |      form the podium standings
                                                       |
<------- Known before lights out: usable as features -->|<--- Known only after: the target --->
```

1. **Practice (Friday, sometimes Saturday):** free sessions where teams tune the car. No points, and not in the Kaggle dataset.
2. **Qualifying (usually Saturday):** each driver sets timed laps. The fastest takes **pole position** (P1 on the grid); P1 and P2 form the **front row**.
3. **Starting grid:** normally the qualifying order, but it can change. Penalties move drivers back (e.g., for fitting more engine or gearbox parts than allowed, or for an offence at an earlier race). A driver can also start from the pit lane or be excluded from qualifying. So qualifying position and grid position are not the same thing.
4. **Race (Sunday):** a standing start from the grid, about 305 km (Monaco is shorter) with a time limit. Drivers make pit stops for fresh tyres. The first three across the line finish on the podium.
5. **Results:** finishing order, points, the reason anyone stopped early (`status`), and updated championship standings. All of this is post-race.

**Sprint weekends** (2021 onward, a handful of races per season) add a short Saturday race of about 100 km with fewer points. The format kept changing: in 2021–2022 the sprint result set the Sunday grid; from 2023 Friday qualifying sets the Sunday grid and a separate sprint qualifying sets the sprint grid. Because the sprint runs before the main race, its result is technically pre-race information.

---

## Glossary

These are the terms that come up in the dataset, the milestone brief, and our discussions, sorted alphabetically.

| Term | Meaning | Where it matters for us |
| :--- | :--- | :--- |
| **Classified** | A driver who completed enough of the race distance (today 90% of the winner's laps) to be given an official position, even if they stopped before the end | Explains why some retired drivers still have a numeric position |
| **Constructor** | The team that builds and enters the car; can change name when sold (e.g., Toleman became Benetton, then Renault, Lotus, Alpine) | Each name is a separate `constructorId`, so team history can break at renames |
| **DNF** | Did Not Finish: the car stopped before the end (crash, mechanical failure, etc.) | Status table; question 3 on mechanical retirements |
| **DNQ/DNPQ** | Did Not (Pre-)Qualify: too slow to earn a grid slot in eras with more entrants than grid places | Rows with no race start; decide whether they belong in the modeling table |
| **DRS** | Drag Reduction System, a rear-wing flap that eases overtaking, introduced 2011 | Makes grid position slightly less decisive after 2011 |
| **DSQ** | Disqualified after the race, usually for a technical or sporting breach | Result changes after the chequered flag; still post-race |
| **Fastest lap** | The quickest single lap in the race; worth a bonus point in some eras | Post-race, never a feature |
| **Front row** | Grid positions 1 and 2 | Question 1 |
| **Grand Prix** | Formal name of a race event | Race names in `races.csv` |
| **Grid position** | Where the car actually starts the race, after penalties | Allowed feature; `0` in the data means a pit-lane start (verify in EDA) |
| **Home race** | A race held in the driver's own country | Question 2; needs mapping driver nationality (e.g., `"British"`) to circuit country (e.g., `"UK"`) |
| **Hybrid era** | 2014–2021 rules: 1.6-litre turbo V6 engines with energy recovery | Question 1 and 3 era split |
| **Lapped** | Finished but one or more laps behind the winner; status shows `"+1 Lap"` etc. | Counts as finished, not a retirement |
| **Pit stop** | A stop in the pit lane to change tyres (and in some eras refuel) | Post-race data; never a feature |
| **Pole position** | First place on the starting grid, earned by the fastest qualifying lap | Strongest single predictor of a podium |
| **Podium** | Finishing 1st, 2nd, or 3rd | Our target: `positionOrder` $\le 3$ |
| **Qualifying** | Timed session that sets the starting order | Allowed feature; coverage in the data is patchy for older years |
| **Retirement** | Same as DNF; split into mechanical (engine, gearbox, hydraulics) and accident/driver causes | Question 3 needs a mechanical vs. non-mechanical grouping of status values |
| **Safety car** | A road car that neutralises the race after an incident, bunching up the field | Reason upsets happen; not a feature |
| **Season** | One championship year | Split boundaries: train $\le 2019$, validation 2020–2021, test $\ge 2022$ |
| **Sprint** | Short Saturday race on selected weekends since 2021 | `sprint_results.csv`; a leakage judgement call |
| **Standings** | Cumulative championship points and rank after each race | Must be shifted to "standings before this race" to be leakage-safe |
| **Status** | Why a driver's race ended: `"Finished"`, `"+1 Lap"`, `"Engine"`, `"Collision"`, etc. | Post-race; used for question 3 only |
| **Tyre compounds** | Softer tyres are faster but wear quicker; since 2007 each driver must use two dry compounds in a dry race | Background for strategy, not in our features |

---

## How a Result Is Recorded

Every driver who enters a race gets a row in `results.csv`, and three different "position" columns describe where they ended up. Our target uses `positionOrder` because it is the only one filled for every row.

| Column | What it holds | Example for a driver who crashed out |
| :--- | :--- | :--- |
| `position` | Official finishing position; empty (`\N`) if not classified | `\N` |
| `positionText` | Position as text, or a letter code when there is no position | `R` |
| `positionOrder` | A full ranking of every entrant, classified or not; always filled | `17` |

The letter codes in `positionText` are: `R` retired, `D` disqualified, `E` excluded, `W` withdrawn, `F` failed to qualify, `N` not classified. A retired driver can still be "classified" and get a numeric position if they completed 90% of the winner's laps.

The `status` column (via `status.csv`) says why a driver's race ended. `"Finished"` and `"+1 Lap"`, `"+2 Laps"` and so on mean the driver reached the flag. Everything else is a reason for stopping, and there are over 100 of them. For question 3 we have to group them ourselves into mechanical failures (`Engine`, `Gearbox`, `Hydraulics`, `Brakes`, `Power Unit`, etc.) versus accidents, driver errors, and other causes, and document that mapping.

Note that a podium is almost always a clean finish on the lead lap, but a disqualification after the race can promote the 4th-place driver to the podium. `positionOrder` already reflects the final, post-appeal classification.

---

## Qualifying Formats Through History

Qualifying has always ranked drivers by lap time, but the format changed repeatedly, and the dataset only records it in detail for recent decades. For most of history, the `grid` column in `results.csv` is our only record of the starting order.

| Seasons | Format | What the dataset shows |
| :--- | :--- | :--- |
| **2006–2024** | Three-part knockout: Q1 drops the slowest cars, Q2 drops more, Q3 decides the top 10 (a failed "elimination" variant was tried for two races in 2016) | `q1`, `q2`, `q3` lap times; drivers knocked out early have `\N` for later parts |
| **2005** | Single-lap runs, briefly as an aggregate of two sessions | Mostly `q1` only |
| **2003–2004** | Single-lap, one car on track at a time | Mostly `q1` only |
| **1996–2002** | One-hour session, 12-lap limit, best lap counts; the "107% rule" excluded drivers too far off pole | Mostly `q1` only |
| **1950–1995** | Varied: usually timed sessions on Friday and Saturday with the best time counting; pre-qualifying for oversubscribed fields in the late 1980s and early 1990s | Little or no qualifying data |

**Why this matters:** the milestone brief warns about *"historical qualifying-coverage drift"*. Qualifying-based features will be missing for most pre-2000s rows, so our EDA should plot qualifying coverage per season and decide whether to impute, fall back to `grid`, or restrict the training window. We believe `qualifying.csv` begins in the mid-1990s, but that must be confirmed from our own copy.

---

## Technical and Sporting Eras, 1950–2024

F1 rewrites its technical rules every few years, and each rewrite reshuffles which teams are fast.

| Era | What defined it | Who tended to win |
| :--- | :--- | :--- |
| **2022–2024: ground-effect era** | New cars that generate grip from shaped floor tunnels, designed to allow closer racing; a team budget cap has applied since 2021 | Red Bull dominant in 2022–2023; McLaren won the 2024 constructors' title |
| **2014–2021: turbo-hybrid era** | 1.6-litre turbo V6 engines with energy recovery; wider, faster cars from 2017; COVID-shortened 17-race season in 2020 | Mercedes won every constructors' title; Verstappen (Red Bull) took the 2021 drivers' title |
| **2009–2013: late V8 era** | Big aerodynamic reset in 2009; refuelling banned from 2010; DRS and a single tyre supplier (Pirelli) from 2011 | Brawn in 2009, then Red Bull and Vettel 2010–2013 |
| **1995–2008: V10 and early V8** | 3-litre V10s (V8s from 2006); in-race refuelling allowed 1994–2009, making strategy central | Williams, McLaren, then Ferrari and Schumacher dominant 2000–2004 |
| **1989–1994: post-turbo** | Turbos banned; electronic driver aids flourished, then were banned for 1994; safety car formalised 1993 | McLaren-Honda, then Williams-Renault |
| **1977–1988: turbo and ground effect** | Turbocharged engines from 1977; early ground-effect cars until flat floors were mandated in 1983; refuelling banned from 1984 | Many teams; McLaren and Williams strong in the 1980s |
| **1966–1976: 3-litre and wings** | Engine size doubled in 1966; wings appear in 1968; the customer Cosworth DFV engine lets small teams compete | Lotus, Tyrrell, Ferrari, McLaren |
| **1958–1965: rear-engine revolution** | Cooper shows engines behind the driver are better; Constructors' Championship starts 1958; 1.5-litre engines 1961–1965 | Cooper, Lotus, BRM, Ferrari |
| **1950–1957: front-engine era** | Pre-war-style cars, few safety rules, very high retirement rates | Alfa Romeo, Ferrari, Maserati, Mercedes |

Season length grew from 7 races in 1950 to 24 in 2024, and a modern driver faces far more competitive, reliable cars than a 1950s driver did. Both facts change what "typical" podium and retirement rates look like.

---

## Oddities of Early F1 That Show Up in the Data

Several practices from the 1950s and 1960s break assumptions a modern fan (or a modern schema) would make. The most important one breaks our required grain of one row per `(raceId, driverId)`.

* **Shared drives:** Until 1957, a team could call a driver in mid-race and hand his car to a teammate, and a star driver could take over a teammate's car after his own broke. Points were split between the drivers who shared a car. In the data this appears as the same driver having two result rows in one race (one per car), or two drivers attached to one car's result. The brief asks us to choose and justify a rule, for example keeping the row for the car the driver started in (non-zero grid) or the row with the best `positionOrder`.
* **The Indianapolis 500 counted, 1950–1960:** This American oval race was part of the championship but almost no F1 regulars entered it, and its drivers rarely raced elsewhere. It inflates race counts for American drivers, distorts home-race analysis (question 2), and has a very different grid structure. Excluding it is a defensible choice we should document.
* **Oversized, uneven fields:** Privateers entered their own cars, one-off local drivers appeared at their home race, and in the 1980s–1990s many more cars turned up than could start. Non-qualifiers still have result rows, so the base rate of podiums per row is lower in those years.
* **Team and driver identity drift:** Drivers switched teams mid-season more freely, car numbers were not fixed, and constructors changed names. A "constructor form" feature must follow `constructorId`, and we should accept that renames reset history.
* **Low reliability:** Retirement rates were far higher in the early decades, so a good grid slot converted to a podium much less reliably than today.