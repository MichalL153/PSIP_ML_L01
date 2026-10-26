"""Sprawdzenia ryzyk przestrzennych: osie, otwory i male enklawy."""
import argparse
import json
import unittest
from pathlib import Path

import h3
from osgeo import ogr
from python.h3_generator import generate_grid, read_county, parse_resolutions


class GridTests(unittest.TestCase):
    def test_county_and_coordinate_order(self):
        geometry, properties = read_county(Path("/data/powiat.shp"))
        self.assertEqual(properties["JPT_KOD_JE"], "1201")
        counts = []
        for resolution in (6, 7, 8):
            features = generate_grid(geometry, resolution)
            self.assertEqual(len(features), len({f["properties"]["h3_index"] for f in features}))
            for feature in features:
                cell = feature["properties"]["h3_index"]
                self.assertTrue(h3.is_valid_cell(cell))
                self.assertEqual(h3.get_resolution(cell), resolution)
                lng, lat = feature["geometry"]["coordinates"][0][0]
                self.assertTrue(19 < lng < 22 and 49 < lat < 51)
                self.assertTrue(ogr.CreateGeometryFromJson(json.dumps(feature["geometry"])).IsValid())
            counts.append(len(features))
        self.assertTrue(counts[0] < counts[1] < counts[2])

    def test_tiny_island_is_not_lost_and_hole_is_respected(self):
        # Enklawa znacznie mniejsza od komorki H3 nie moze zniknac.
        island = [[20.4,50.0],[20.40001,50.0],[20.40001,50.00001],[20.4,50.00001],[20.4,50.0]]
        self.assertGreater(len(generate_grid({"type":"Polygon", "coordinates":[island]}, 7)), 0)
        outer = [[20,49],[21,49],[21,50],[20,50],[20,49]]
        hole = [[20.2,49.2],[20.8,49.2],[20.8,49.8],[20.2,49.8],[20.2,49.2]]
        features = generate_grid({"type":"Polygon", "coordinates":[outer,hole]}, 7)
        self.assertNotIn(h3.latlng_to_cell(49.5,20.5,7), {f["properties"]["h3_index"] for f in features})

    def test_resolution_validation(self):
        self.assertEqual(parse_resolutions("8,6,7,7"), [6,7,8])
        for value in ("", "-1", "16", "abc"):
            with self.assertRaises(argparse.ArgumentTypeError):
                parse_resolutions(value)


if __name__ == "__main__":
    unittest.main()
