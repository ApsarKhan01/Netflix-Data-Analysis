from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "data" / "raw" / "netflix_titles.csv"
CLEAN_DIR = ROOT / "data" / "clean"

AUDIENCE = {
    "TV-Y": "Kids", "TV-Y7": "Kids", "TV-Y7-FV": "Kids", "TV-G": "Kids", "G": "Kids",
    "PG": "Teens", "TV-PG": "Teens", "PG-13": "Teens", "TV-14": "Teens",
    "R": "Adults", "TV-MA": "Adults", "NC-17": "Adults",
}


def read_raw(path: Path = RAW_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Raw data not found: {path}")
    df = pd.read_csv(path)
    missing = {"show_id", "type", "title", "date_added", "release_year", "rating", "duration",
               "listed_in", "country"} - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
    return df


def strip_text(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()
    return df


def fix_shifted_durations(df: pd.DataFrame) -> pd.DataFrame:
    # Three stand-up specials have their running time in the rating column and
    # no duration, so the value belongs one column over.
    df = df.copy()
    shifted = df["rating"].str.fullmatch(r"\d+ min", na=False) & df["duration"].isna()
    df.loc[shifted, "duration"] = df.loc[shifted, "rating"]
    df.loc[shifted, "rating"] = pd.NA
    print(f"Moved running time from rating to duration for {shifted.sum()} titles: "
          f"{', '.join(df.loc[shifted, 'title'])}")
    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date_added"] = pd.to_datetime(df["date_added"], format="%B %d, %Y")
    df["year_added"] = df["date_added"].dt.year.astype("Int64")
    df["month_added"] = df["date_added"].dt.month.astype("Int64")
    # Movies only: a TV show's release_year is its latest season, so 12 shows
    # appear to arrive before they were released. Two movies are also negative
    # (a Netflix premiere ahead of the listed year) and are left as they are.
    is_movie = df["type"] == "Movie"
    df["years_to_netflix"] = (df["year_added"] - df["release_year"]).where(is_movie)
    print(f"Left date_added blank for {df['date_added'].isna().sum()} titles with no date in the source")
    return df


def split_duration(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    number = df["duration"].str.extract(r"(\d+)", expand=False).astype("Int64")
    is_movie = df["type"] == "Movie"
    df["duration_min"] = number.where(is_movie)
    df["seasons"] = number.where(~is_movie)
    return df


def fill_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["director", "cast", "country"]:
        df[col] = df[col].fillna("Unknown")
    df["rating"] = df["rating"].fillna("Unknown")
    # NR and UR both mean the title was never rated, so they share a group.
    df["audience"] = df["rating"].map(AUDIENCE).fillna("Unrated")
    return df


def explode_list(df: pd.DataFrame, column: str, name: str) -> pd.DataFrame:
    # Genres and countries are comma-separated lists. One row per title and value
    # lets Power BI count a co-production once for each country instead of
    # treating "United States, India" as a country of its own.
    values = df[["show_id", column]].assign(**{name: df[column].str.split(",")}).explode(name)
    values[name] = values[name].str.strip()
    values = values[values[name].notna() & (values[name] != "")]
    return values[["show_id", name]].drop_duplicates().reset_index(drop=True)


def clean_titles(raw: pd.DataFrame) -> pd.DataFrame:
    df = strip_text(raw)
    df = fix_shifted_durations(df)
    df = parse_dates(df)
    df = split_duration(df)
    df = fill_labels(df)
    if not df["show_id"].is_unique:
        raise ValueError("show_id is not unique after cleaning")
    return df


def main() -> None:
    raw = read_raw()
    titles = clean_titles(raw)
    genres = explode_list(titles, "listed_in", "genre")
    countries = explode_list(titles[titles["country"] != "Unknown"], "country", "country_name")

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    columns = ["show_id", "type", "title", "director", "cast", "country", "date_added", "year_added",
               "month_added", "release_year", "years_to_netflix", "rating", "audience", "duration",
               "duration_min", "seasons", "listed_in", "description"]
    titles[columns].to_csv(CLEAN_DIR / "titles.csv", index=False, date_format="%Y-%m-%d")
    genres.to_csv(CLEAN_DIR / "title_genres.csv", index=False)
    countries.rename(columns={"country_name": "country"}).to_csv(CLEAN_DIR / "title_countries.csv", index=False)

    print(f"\nWrote {len(titles):,} titles, {len(genres):,} title-genre rows ({genres['genre'].nunique()} genres), "
          f"{len(countries):,} title-country rows ({countries['country_name'].nunique()} countries) to {CLEAN_DIR}")


if __name__ == "__main__":
    main()
