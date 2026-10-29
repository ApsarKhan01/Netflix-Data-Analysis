# Building the Power BI dashboard

These are the steps I followed to build `netflix_dashboard.pbix` from the three cleaned tables. Run `python src/clean.py` first so `data/clean/` exists.

The dashboard has two pages:

1. **Overview**: KPI cards, titles added per year, top countries and genres, audience mix, and slicers for type, genre, country, audience and year added.
2. **Title details**: a drill-through page listing the individual titles behind any bar.

## 1. Load the data

1. Home > Get data > Text/CSV, and load `data/clean/titles.csv`. Repeat for `title_genres.csv` and `title_countries.csv`.
2. Choose **Transform Data** instead of Load, and check the column types in Power Query:
   - `titles`: `date_added` as Date. `year_added`, `month_added`, `release_year`, `years_to_netflix`, `duration_min` and `seasons` as Whole Number. Everything else as Text.
   - `title_genres` and `title_countries`: both columns as Text.
3. Close & Apply.
4. In the Data pane, select `year_added`, `release_year` and `month_added`, and set **Summarization** to **Don't summarize** under Column tools. Otherwise Power BI adds the years up.

## 2. Set up the model

Genres and countries are lists: a title can have up to three genres and several countries. That is why they sit in their own tables with one row per title and value, linked to `titles` by `show_id`.

1. Open Model view. Power BI usually detects both relationships from the `show_id` column. If not, drag `titles[show_id]` onto `title_genres[show_id]`, then onto `title_countries[show_id]`.
2. Both relationships should be **one-to-many**, with `titles` on the one side.
3. Open each relationship (double-click the line) and set **Cross filter direction** to **Both**.

Why Both: with the default single direction, filters only flow from `titles` to the bridge tables. A genre slicer would then not change the title count, and a "top genres" chart would show the same total on every bar. With Both, picking "Documentaries" filters `titles` to the documentaries, and those filter `title_countries` in turn, so the country chart shows where documentaries come from. The model is a star with `titles` in the middle and no loops, so the two-way filters can't conflict.

## 3. Create the measures

Select the `titles` table, then Home > New measure, once for each:

```dax
Total Titles = DISTINCTCOUNT ( titles[show_id] )

Movies = CALCULATE ( [Total Titles], KEEPFILTERS ( titles[type] = "Movie" ) )

TV Shows = CALCULATE ( [Total Titles], KEEPFILTERS ( titles[type] = "TV Show" ) )

Movie Share % = DIVIDE ( [Movies], [Total Titles] )

Released 2016+ % =
DIVIDE (
    CALCULATE ( [Total Titles], KEEPFILTERS ( titles[release_year] >= 2016 ) ),
    [Total Titles]
)

Median Years to Netflix = MEDIAN ( titles[years_to_netflix] )

Countries = DISTINCTCOUNT ( title_countries[country] )
```

Notes:

- `DISTINCTCOUNT` on `show_id` makes sure a title with three genres is still counted once.
- `KEEPFILTERS` makes the Movies and TV Shows cards respect the type slicer. A plain `CALCULATE` would override the slicer, so the Movies card would still show 6,131 with "TV Show" selected.
- `years_to_netflix` is blank for TV shows (their release year is the latest season), and `MEDIAN` ignores blanks, so the measure covers movies only.
- Format `Movie Share %` and `Released 2016+ %` as Percentage with 1 decimal place.

## 4. Overview page

| Visual | Fields | Settings |
|---|---|---|
| 4 cards | Total Titles, Movies, TV Shows, Released 2016+ % | Display units: None, so 8,807 shows in full instead of 8.81K |
| Stacked column chart | X: `titles[year_added]`, Y: Total Titles, Legend: `titles[type]` | Format > X axis > Type: Categorical. Filter `year_added` to 2015 or later |
| Bar chart: top countries | Y: `title_countries[country]`, X: Total Titles | Filters pane on `country`: Filter type Top N, Top 10, by value Total Titles |
| Bar chart: top genres | Y: `title_genres[genre]`, X: Total Titles | Same Top N filter, Top 10 |
| 100% stacked bar | Y: `titles[type]`, X: Total Titles, Legend: `titles[audience]` | Shows the audience mix by type |
| Slicers | `titles[type]` (tiles), `title_genres[genre]` (dropdown), `title_countries[country]` (dropdown), `titles[audience]` (tiles), `titles[year_added]` (between) | Search on for genre and country |

Put the cards across the top, the yearly chart under them, and the slicers in a column on the left.

## 5. Title details page (drill-through)

1. Add a new page and name it **Title details**.
2. With the page selected and nothing else, open the Visualizations pane and find the **Drill through** section. Drag in `title_genres[genre]`, `title_countries[country]` and `titles[type]`. Power BI adds a back button to the page.
3. Add a Table visual with `title`, `type`, `release_year`, `year_added`, `rating`, `duration`, `director` and `description` from `titles`. Sort by `year_added`, newest first.
4. Add a card with Total Titles, so the page shows how many titles are in the selection.

To use it, right-click any bar on the Overview page, for example "India" in top countries, and choose Drill through > Title details. The table lists those titles, and the back button returns to the overview.

## 6. Check the numbers

With no slicers selected, the dashboard should match the notebook exactly:

| Check | Expected |
|---|---|
| Total Titles | 8,807 |
| Movies / TV Shows | 6,131 / 2,676 |
| Released 2016+ % | 64.2% |
| Median Years to Netflix | 2 |
| Titles added in 2019 | 2,016 |
| United States (top countries) | 3,690 |
| International Movies (top genres) | 2,752 |
| Countries | 122 |

If Total Titles is larger than 8,807 when a genre or country is involved, the measure is counting bridge rows instead of distinct titles. Check that the cards use `Total Titles` and not a count of a bridge-table column.

## 7. Save and publish

1. Save the file as `powerbi/netflix_dashboard.pbix`.
2. Take a screenshot of the Overview page and save it as `images/powerbi_overview.png`.
3. Commit and push:

```
git add powerbi/netflix_dashboard.pbix images/powerbi_overview.png
git commit -m "Add Power BI dashboard"
git push
```
