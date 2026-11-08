#!/usr/bin/env python3
"""Parametric S3-N16R8-compatible status-light enclosure with USB-C.

Run with CadQuery 2.8+:
    python enclosure.py --output-dir stl
All dimensions are millimetres. Exported STLs are oriented for printing.
"""

from __future__ import annotations

import argparse
import base64
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cadquery as cq


@dataclass(frozen=True)
class Parameters:
    board_length: float = 56.50
    board_width: float = 27.40
    board_thickness: float = 1.65
    board_bottom: float = 3.00
    board_fit_clearance: float = 0.30
    antenna_overhang: float = 6.24
    outer_length: float = 70.00
    outer_width: float = 34.00
    housing_center_x: float = 3.50
    base_height: float = 14.00
    wall: float = 2.00
    bottom: float = 2.00
    corner_radius: float = 4.00
    lid_thickness: float = 2.20
    skirt_depth: float = 3.40
    skirt_wall: float = 0.90
    fit_clearance: float = 0.25
    friction_rib: float = 0.30
    usb_connector_width: float = 8.88
    usb_connector_height: float = 3.14
    usb_shell_gap: float = 2.95
    usb_protrusion: float = 0.30
    cable_plug_width: float = 10.62
    cable_plug_height: float = 6.12
    usb_cable_clearance: float = 0.15
    usb_insert_clearance: float = 0.15
    usb_insert_rib: float = 0.20
    usb_receiver_width: float = 25.00
    usb_receiver_height: float = 8.20
    usb_flange_width: float = 25.60
    usb_flange_height: float = 11.20
    usb_flange_thickness: float = 1.20
    vent_slot_length: float = 16.00
    vent_slot_height: float = 1.60
    vent_slot_bottom: float = 3.80
    vent_slot_gap: float = 4.00
    led_x: float = -10.17
    led_y: float = 5.36
    diffuser_hole: float = 8.00
    diffuser_stem: float = 7.80
    diffuser_cap: float = 10.00
    diffuser_cap_height: float = 0.80

    @property
    def inner_length(self) -> float:
        return self.outer_length - 2 * self.wall

    @property
    def inner_width(self) -> float:
        return self.outer_width - 2 * self.wall

    @property
    def skirt_length(self) -> float:
        return self.inner_length - 2 * self.fit_clearance

    @property
    def skirt_width(self) -> float:
        return self.inner_width - 2 * self.fit_clearance

    @property
    def lid_top(self) -> float:
        return self.base_height + self.lid_thickness

    @property
    def usb_center_spacing(self) -> float:
        return self.usb_connector_width + self.usb_shell_gap

    @property
    def usb_center_z(self) -> float:
        return self.board_bottom + self.board_thickness + self.usb_connector_height / 2

    @property
    def usb_hole_width(self) -> float:
        return self.cable_plug_width + 2 * self.usb_cable_clearance

    @property
    def usb_hole_height(self) -> float:
        return self.cable_plug_height + 2 * self.usb_cable_clearance

    @property
    def usb_wall_x(self) -> float:
        return self.housing_center_x - self.outer_length / 2

    @property
    def usb_tongue_width(self) -> float:
        return self.usb_receiver_width - 2 * self.usb_insert_clearance

    @property
    def usb_tongue_height(self) -> float:
        return self.usb_receiver_height - 2 * self.usb_insert_clearance


P = Parameters()


def rounded_prism(
    length: float,
    width: float,
    height: float,
    radius: float,
    z: float = 0,
    x: float = 0,
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(length, width, height, centered=(True, True, False))
        .edges("|Z")
        .fillet(radius)
        .translate((x, 0, z))
    )


def rounded_yz_plate(
    thickness: float,
    width: float,
    height: float,
    radius: float,
    x: float,
    z: float,
    y: float = 0,
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(thickness, width, height)
        .edges("|X")
        .fillet(radius)
        .translate((x, y, z))
    )


def build_base(p: Parameters = P) -> cq.Workplane:
    base = rounded_prism(
        p.outer_length,
        p.outer_width,
        p.base_height,
        p.corner_radius,
        x=p.housing_center_x,
    )
    cavity = rounded_prism(
        p.inner_length,
        p.inner_width,
        p.base_height,
        max(p.corner_radius - p.wall, 0.8),
        p.bottom,
        p.housing_center_x,
    )
    base = base.cut(cavity)

    receiver = rounded_yz_plate(
        2 * p.wall + 4,
        p.usb_receiver_width,
        p.usb_receiver_height,
        0.8,
        p.usb_wall_x,
        p.usb_center_z,
    )
    flange_recess = rounded_yz_plate(
        p.usb_flange_thickness + 0.2,
        p.usb_flange_width + 2 * p.usb_insert_clearance,
        p.usb_flange_height + 2 * p.usb_insert_clearance,
        1.0,
        p.usb_wall_x + (p.usb_flange_thickness - 0.2) / 2,
        p.usb_center_z,
    )
    base = base.cut(receiver).cut(flange_recess)

    slot_offset = (p.vent_slot_length + p.vent_slot_gap) / 2
    for sign in (-1, 1):
        for x in (p.housing_center_x - slot_offset, p.housing_center_x + slot_offset):
            slot = (
                cq.Workplane("XY")
                .box(p.vent_slot_length, 2 * p.wall + 4, p.vent_slot_height)
                .edges("|Y")
                .fillet(0.5)
                .translate(
                    (
                        x,
                        sign * p.outer_width / 2,
                        p.vent_slot_bottom + p.vent_slot_height / 2,
                    )
                )
            )
            base = base.cut(slot)

    rail_length = p.board_length - 8
    for y in (-9.0, 9.0):
        rail = (
            cq.Workplane("XY")
            .box(
                rail_length,
                2.0,
                p.board_bottom - p.bottom,
                centered=(True, True, False),
            )
            .translate((0, y, p.bottom))
        )
        base = base.union(rail)

    side_stop_width = p.inner_width / 2 - p.board_width / 2 - p.board_fit_clearance
    for sign in (-1, 1):
        y = sign * (p.board_width / 2 + p.board_fit_clearance + side_stop_width / 2)
        for x, length in ((-23.0, 6.0), (3.5, 3.0), (25.0, 6.0)):
            stop = (
                cq.Workplane("XY")
                .box(length, side_stop_width, 5.0, centered=(True, True, False))
                .translate((x, y, p.bottom))
            )
            base = base.union(stop)

    usb_stop_face = -p.board_length / 2 - p.board_fit_clearance
    usb_stop_back = p.usb_wall_x + p.wall
    usb_stop_length = usb_stop_face - usb_stop_back
    for y in (-12.6, 12.6):
        stop = (
            cq.Workplane("XY")
            .box(usb_stop_length, 2.0, 5.0, centered=(True, True, False))
            .translate(((usb_stop_face + usb_stop_back) / 2, y, p.bottom))
        )
        base = base.union(stop)

        antenna_stop_height = p.board_bottom + p.board_thickness - 0.15 - p.bottom
        stop = (
            cq.Workplane("XY")
            .box(1.2, 2.0, antenna_stop_height, centered=(True, True, False))
            .translate((p.board_length / 2 + p.board_fit_clearance + 0.6, y, p.bottom))
        )
        base = base.union(stop)
    return base.clean()


def build_usb_insert(p: Parameters = P) -> cq.Workplane:
    flange = rounded_yz_plate(
        p.usb_flange_thickness,
        p.usb_flange_width,
        p.usb_flange_height,
        1.0,
        p.usb_wall_x + p.usb_flange_thickness / 2,
        p.usb_center_z,
    )
    tongue = rounded_yz_plate(
        p.wall,
        p.usb_tongue_width,
        p.usb_tongue_height,
        0.6,
        p.usb_wall_x + p.wall / 2,
        p.usb_center_z,
    )
    insert = flange.union(tongue)
    for sign in (-1, 1):
        rib = (
            cq.Workplane("XY")
            .box(p.wall * 0.65, 2 * p.usb_insert_rib, 3.0)
            .translate(
                (
                    p.usb_wall_x + p.wall * 0.55,
                    sign * p.usb_tongue_width / 2,
                    p.usb_center_z,
                )
            )
        )
        insert = insert.union(rib)

    for y in (-p.usb_center_spacing / 2, p.usb_center_spacing / 2):
        hole = rounded_yz_plate(
            p.wall + p.usb_flange_thickness + 2,
            p.usb_hole_width,
            p.usb_hole_height,
            0.45,
            p.usb_wall_x,
            p.usb_center_z,
            y,
        )
        insert = insert.cut(hole)
    return insert.clean()


def build_lid(p: Parameters = P) -> cq.Workplane:
    skirt_bottom = p.base_height - p.skirt_depth
    lid = rounded_prism(
        p.outer_length,
        p.outer_width,
        p.lid_thickness,
        p.corner_radius,
        p.base_height,
        p.housing_center_x,
    )
    skirt = rounded_prism(
        p.skirt_length,
        p.skirt_width,
        p.skirt_depth,
        max(p.corner_radius - p.wall - p.fit_clearance, 0.8),
        skirt_bottom,
        p.housing_center_x,
    )
    skirt_void = rounded_prism(
        p.skirt_length - 2 * p.skirt_wall,
        p.skirt_width - 2 * p.skirt_wall,
        p.skirt_depth,
        1.0,
        skirt_bottom,
        p.housing_center_x,
    )
    lid = lid.union(skirt.cut(skirt_void))

    for x in (-19.0, 19.0):
        for sign in (-1, 1):
            rib = (
                cq.Workplane("XY")
                .box(10.0, 2 * p.friction_rib, 1.4)
                .edges("|Z")
                .fillet(p.friction_rib * 0.8)
                .translate(
                    (
                        x + p.housing_center_x,
                        sign * p.skirt_width / 2,
                        p.base_height - 1.8,
                    )
                )
            )
            lid = lid.union(rib)

    hole = (
        cq.Workplane("XY")
        .workplane(offset=p.base_height - 0.2)
        .center(p.led_x, p.led_y)
        .circle(p.diffuser_hole / 2)
        .extrude(p.lid_thickness + 0.4)
    )
    return lid.cut(hole).clean()


def build_diffuser(p: Parameters = P) -> cq.Workplane:
    stem = (
        cq.Workplane("XY")
        .workplane(offset=p.base_height)
        .center(p.led_x, p.led_y)
        .circle(p.diffuser_stem / 2)
        .extrude(p.lid_thickness)
    )
    cap = (
        cq.Workplane("XY")
        .workplane(offset=p.lid_top)
        .center(p.led_x, p.led_y)
        .circle(p.diffuser_cap / 2)
        .extrude(p.diffuser_cap_height)
        .edges(">Z")
        .fillet(0.30)
    )
    return stem.union(cap).clean()


def print_oriented(shape: cq.Workplane, part: str, p: Parameters) -> cq.Workplane:
    if part == "base":
        return shape
    if part == "usb_insert":
        return shape.rotate((0, 0, 0), (0, 1, 0), -90).translate(
            (0, 0, -p.usb_wall_x)
        )
    top = p.lid_top if part == "lid" else p.lid_top + p.diffuser_cap_height
    return shape.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, top))


def validate(
    base: cq.Workplane,
    lid: cq.Workplane,
    diffuser: cq.Workplane,
    usb_insert: cq.Workplane,
    p: Parameters,
) -> None:
    shapes = (("base", base), ("lid", lid), ("diffuser", diffuser), ("usb_insert", usb_insert))
    for name, shape in shapes:
        solids = shape.solids().vals()
        assert len(solids) == 1, f"{name}: expected one solid, got {len(solids)}"
        assert solids[0].isValid(), f"{name}: invalid solid"
        assert solids[0].Volume() > 0, f"{name}: empty solid"

    board = (
        cq.Workplane("XY")
        .box(
            p.board_length,
            p.board_width,
            p.board_thickness,
            centered=(True, True, False),
        )
        .translate((0, 0, p.board_bottom))
    )
    antenna = (
        cq.Workplane("XY")
        .box(p.antenna_overhang, 18.0, 0.8, centered=(True, True, False))
        .translate(
            (
                p.board_length / 2 + p.antenna_overhang / 2,
                0.2,
                p.board_bottom + p.board_thickness,
            )
        )
    )
    for name, shape in shapes:
        if name == "diffuser":
            continue
        overlap = shape.intersect(board).vals()
        volume = sum(s.Volume() for s in overlap if hasattr(s, "Volume"))
        assert volume < 0.01, f"{name}: intersects PCB by {volume:.3f} mm^3"
        overlap = shape.intersect(antenna).vals()
        volume = sum(s.Volume() for s in overlap if hasattr(s, "Volume"))
        assert volume < 0.01, f"{name}: intersects antenna by {volume:.3f} mm^3"

    connector_front = -p.board_length / 2 - p.usb_protrusion
    for y in (-p.usb_center_spacing / 2, p.usb_center_spacing / 2):
        connector = (
            cq.Workplane("XY")
            .box(8.0, p.usb_connector_width, p.usb_connector_height)
            .translate((connector_front + 4.0, y, p.usb_center_z))
        )
        for name, shape in (("base", base), ("lid", lid), ("usb_insert", usb_insert)):
            overlap = shape.intersect(connector).vals()
            volume = sum(s.Volume() for s in overlap if hasattr(s, "Volume"))
            assert volume < 0.01, f"{name}: intersects USB connector by {volume:.3f} mm^3"

    assert p.skirt_width - 2 * p.skirt_wall > p.board_width
    assert p.skirt_length - 2 * p.skirt_wall > p.board_length
    assert p.diffuser_hole > p.diffuser_stem
    assert p.usb_tongue_height > p.usb_hole_height
    assert p.usb_center_spacing - p.usb_hole_width >= 0.8
    assert p.usb_center_z - p.usb_receiver_height / 2 >= p.bottom
    assert p.usb_receiver_width < p.usb_flange_width
    assert p.usb_receiver_height < p.usb_flange_height
    assert p.usb_flange_width + 2 * p.usb_insert_clearance <= p.outer_width - 2 * p.corner_radius


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "stl")
    parser.add_argument("--fit-clearance", type=float, default=P.fit_clearance)
    args = parser.parse_args()
    p = Parameters(fit_clearance=args.fit_clearance)

    assembled = {
        "base": build_base(p),
        "lid": build_lid(p),
        "diffuser": build_diffuser(p),
        "usb_insert": build_usb_insert(p),
    }
    validate(**assembled, p=p)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, shape in assembled.items():
        filename = "usb-insert" if name == "usb_insert" else name
        cq.exporters.export(
            print_oriented(shape, name, p),
            str(args.output_dir / f"{filename}.stl"),
            tolerance=0.05,
            angularTolerance=0.12,
        )
    (args.output_dir / "dimensions.json").write_text(
        json.dumps(asdict(p), indent=2) + "\n", encoding="utf-8"
    )
    model_data = "window.EMBEDDED_STL = " + json.dumps(
        {
            name: base64.b64encode(
                (args.output_dir / f"{'usb-insert' if name == 'usb_insert' else name}.stl").read_bytes()
            ).decode("ascii")
            for name in assembled
        }
    ) + ";\n"
    (args.output_dir.parent / "model-data.js").write_text(model_data, encoding="utf-8")
    print(f"Exported {', '.join(assembled)} to {args.output_dir}")


if __name__ == "__main__":
    main()
