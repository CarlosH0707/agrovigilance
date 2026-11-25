"""Repositório de core.weather_forecasts; o SQL fica em queries/, um arquivo por query."""

from dataclasses import asdict
from pathlib import Path

import psycopg

from agrovigilance.domain.weather_forecast import WeatherForecast

QUERIES = Path(__file__).parent / "queries"
INSERT = (QUERIES / "insert.sql").read_text(encoding="utf-8")


class WeatherForecastRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, item: WeatherForecast) -> None:
        self.conn.execute(INSERT, asdict(item))
