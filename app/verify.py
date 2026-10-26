"""Kontrola danych, geometrii, pokrycia powiatu i identycznosci siatek."""
import os
import psycopg

from python.h3_generator import parse_resolutions


def verify():
    resolutions = parse_resolutions(os.getenv("H3_RESOLUTIONS", "6,7,8"))
    with psycopg.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT teryt, nazwa FROM public.powiat")
        counties = cur.fetchall()
        if len(counties) != 1:
            raise RuntimeError(f"Oczekiwano jednego powiatu, otrzymano {len(counties)}")
        print(f"Powiat: {counties[0][1]}, TERYT {counties[0][0]}")
        for resolution in resolutions:
            cur.execute("""
                SELECT count(*), bool_and(ST_IsValid(geom) AND NOT ST_IsEmpty(geom)
                       AND ST_SRID(geom)=4326 AND ST_NPoints(geom)>=7),
                       md5(string_agg(h3_index, ',' ORDER BY h3_index))
                FROM grid.hexagons WHERE resolution=%s AND teryt=%s
            """, (resolution, counties[0][0]))
            count, valid, fingerprint = cur.fetchone()
            if count == 0 or not valid:
                raise RuntimeError(f"Niepoprawna siatka H3 {resolution}")
            cur.execute("""
                WITH cells AS (
                    SELECT ST_UnaryUnion(ST_Collect(geom)) AS geom
                    FROM grid.hexagons WHERE resolution=%s AND teryt=%s
                )
                SELECT ST_Area(ST_Transform(ST_Difference(p.geom,c.geom),2180))
                FROM public.powiat p CROSS JOIN cells c WHERE p.teryt=%s
            """, (resolution, counties[0][0], counties[0][0]))
            uncovered = cur.fetchone()[0]
            if uncovered > 1.0:
                raise RuntimeError(f"Siatka H3 {resolution} pomija {uncovered} m2 powiatu")
            print(f"H3 {resolution}: {count} komorek, brak pokrycia {uncovered:.4f} m2, MD5 {fingerprint}")


if __name__ == "__main__":
    verify()
