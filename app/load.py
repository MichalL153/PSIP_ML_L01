"""Import granicy powiatu i siatek H3 do bazy wskazanej zmiennymi PG*."""
import argparse
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from python.h3_generator import generate_grid, read_county, parse_resolutions


def load(shapefile, resolutions):
    county, properties = read_county(shapefile)
    # Jedna transakcja: blad nie zostawia pustych tabel po usunieciu starej siatki.
    with psycopg.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS grid")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.powiat (
                    teryt text PRIMARY KEY, nazwa text NOT NULL,
                    geom geometry(MultiPolygon, 4326) NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grid.hexagons (
                    h3_index text NOT NULL,
                    resolution smallint NOT NULL CHECK (resolution BETWEEN 0 AND 15),
                    teryt text NOT NULL,
                    area_m2 double precision NOT NULL CHECK (area_m2 > 0),
                    geom geometry(Polygon, 4326) NOT NULL,
                    PRIMARY KEY (teryt, resolution, h3_index)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS powiat_geom_idx ON public.powiat USING gist (geom)")
            cursor.execute("CREATE INDEX IF NOT EXISTS hexagons_geom_idx ON grid.hexagons USING gist (geom)")
            teryt = properties["JPT_KOD_JE"]
            cursor.execute("""
                INSERT INTO public.powiat (teryt, nazwa, geom)
                VALUES (%s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)))
                ON CONFLICT (teryt) DO UPDATE SET nazwa=excluded.nazwa, geom=excluded.geom
            """, (teryt, properties["JPT_NAZWA_"], Jsonb(county)))
            for resolution in resolutions:
                features = generate_grid(county, resolution)
                if not features:
                    raise ValueError(f"Pusta siatka dla rozdzielczosci {resolution}")
                cursor.execute("DELETE FROM grid.hexagons WHERE teryt=%s AND resolution=%s", (teryt, resolution))
                cursor.executemany("""
                    INSERT INTO grid.hexagons (h3_index, resolution, teryt, area_m2, geom)
                    VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s),4326))
                """, [(f["properties"]["h3_index"], resolution, teryt,
                       f["properties"]["area_m2"], Jsonb(f["geometry"])) for f in features])
                print(f"{properties['JPT_NAZWA_']}: H3 {resolution}, {len(features)} komorek")
    print("Zapisano granice w public.powiat i siatki w grid.hexagons.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("/data/powiat.shp"))
    parser.add_argument("--resolutions", type=parse_resolutions,
                        default=os.getenv("H3_RESOLUTIONS", "6,7,8"))
    args = parser.parse_args()
    load(args.input, args.resolutions)
