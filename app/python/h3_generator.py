"""Generowanie siatek H3 o kolejnych rozdzielczosciach dla jednego powiatu."""
import argparse
import json
from pathlib import Path

import h3
from osgeo import ogr, osr


def parse_resolutions(value):
    try:
        resolutions = sorted(set(int(item.strip()) for item in value.split(",")))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Podaj rozdzielczosci, np. 6,7,8") from exc
    if not resolutions or any(r < 0 or r > 15 for r in resolutions):
        raise argparse.ArgumentTypeError("Rozdzielczosci H3 musza byc z zakresu 0-15")
    return resolutions


def read_county(path):
    ogr.UseExceptions()
    source = ogr.Open(str(path))
    if source is None:
        raise FileNotFoundError(f"Nie mozna otworzyc: {path}")
    layer = source.GetLayer(0)
    if layer.GetFeatureCount() != 1:
        raise ValueError("Plik musi zawierac dokladnie jeden powiat")
    feature = layer.GetNextFeature()
    properties = feature.items()
    for key in ("JPT_KOD_JE", "JPT_NAZWA_"):
        if not properties.get(key):
            raise ValueError(f"Brak atrybutu powiatu: {key}")
    geometry = feature.GetGeometryRef().Clone()
    source_srs = layer.GetSpatialRef()
    if source_srs is None:
        raise ValueError("Dane wejsciowe nie maja ukladu wspolrzednych")
    source_srs = source_srs.Clone()
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)
    source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geometry.Transform(osr.CoordinateTransformation(source_srs, target_srs))
    if geometry.IsEmpty() or not geometry.IsValid():
        raise ValueError("Niepoprawna geometria powiatu")
    return json.loads(geometry.ExportToJson()), properties


def generate_grid(county, resolution):
    """Pelne komorki przecinajace powiat, takze przy granicy i w enklawach.

    Zachowujemy ksztalt H3. Tryb overlap zapobiega lukom na brzegu
    typowym dla wyboru komorek tylko na podstawie ich srodkow.
    """
    if not 0 <= resolution <= 15:
        raise ValueError("Rozdzielczosc H3 musi byc z zakresu 0-15")
    shape = h3.geo_to_h3shape(county)
    cells = h3.h3shape_to_cells_experimental(shape, resolution, contain="overlap")
    features = []
    for cell in sorted(cells):
        ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(cell)]
        ring.append(ring[0])
        features.append({
            "type": "Feature",
            "properties": {"h3_index": cell, "resolution": resolution,
                           "area_m2": h3.cell_area(cell, unit="m^2")},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return features


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("/data/powiat.shp"))
    parser.add_argument("--resolutions", type=parse_resolutions, default="6,7,8")
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/grid"))
    args = parser.parse_args()
    county, properties = read_county(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for resolution in args.resolutions:
        features = generate_grid(county, resolution)
        output = args.output_dir / f"h3_{properties['JPT_KOD_JE']}_r{resolution}.geojson"
        output.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
        print(f"{output}: {len(features)} komorek")


if __name__ == "__main__":
    main()
