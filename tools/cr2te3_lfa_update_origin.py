from __future__ import annotations

import argparse
import csv
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence
import xml.etree.ElementTree as ET

import originpro as op


ROOM_TEMPERATURE_C = 25.0
CR2TE3_CP_J_G_K = 0.256
PDMS_CP_J_G_K = 1.39


@dataclass(frozen=True)
class SampleResult:
    sample_number: int
    volume_fraction: float
    diffusivity_mm2_s: float
    diffusivity_std_mm2_s: float
    density_g_cm3: float
    cp_j_g_k: float
    thermal_conductivity_w_m_k: float
    thermal_conductivity_std_w_m_k: float


def _copy_if_needed(path: Path) -> Path:
    try:
        with path.open("rb"):
            return path
    except OSError:
        temp_dir = Path(tempfile.mkdtemp(prefix="cr2te3_lfa_"))
        copied = temp_dir / path.name
        shutil.copy2(path, copied)
        return copied


def _parse_shared_strings(archive: zipfile.ZipFile) -> List[str]:
    try:
        xml_bytes = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml_bytes)
    ns = {"a": root.tag.split("}")[0].strip("{")}
    values: List[str] = []
    for si in root.findall("a:si", ns):
        text_parts = [node.text or "" for node in si.findall(".//a:t", ns)]
        values.append("".join(text_parts))
    return values


def _sheet_path_by_name(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    ns = {"a": workbook_root.tag.split("}")[0].strip("{")}
    rel_ns = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    rel_id = None
    for sheet in workbook_root.findall("a:sheets/a:sheet", ns):
        if sheet.attrib.get("name") == sheet_name:
            rel_id = sheet.attrib.get("{" + rel_ns["r"] + "}id")
            break
    if not rel_id:
        raise KeyError(f"Sheet {sheet_name!r} not found")

    rel_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {}
    for rel in rel_root:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            rel_map[rid] = target
    target = rel_map[rel_id]
    if not target.startswith("xl/"):
        target = f"xl/{target.lstrip('/')}"
    return target


def _read_sheet_values(xlsx_path: Path, sheet_name: str) -> Dict[str, str]:
    actual_path = _copy_if_needed(xlsx_path)
    with zipfile.ZipFile(actual_path) as archive:
        shared_strings = _parse_shared_strings(archive)
        sheet_path = _sheet_path_by_name(archive, sheet_name)
        root = ET.fromstring(archive.read(sheet_path))
        ns = {"a": root.tag.split("}")[0].strip("{")}
        values: Dict[str, str] = {}
        for cell in root.findall(".//a:c", ns):
            ref = cell.attrib.get("r")
            if not ref:
                continue
            value_node = cell.find("a:v", ns)
            text = value_node.text if value_node is not None else ""
            if cell.attrib.get("t") == "s" and text:
                text = shared_strings[int(text)]
            values[ref] = text or ""
        return values


def _read_actual_volume_fractions(xlsx_path: Path) -> Dict[int, float]:
    sheet_values = _read_sheet_values(xlsx_path, "Sheet2")
    row_to_sample = {
        9: 1,
        10: 2,
        11: 3,
        12: 4,
        13: 5,
        14: 6,
    }
    result: Dict[int, float] = {}
    for row, sample_number in row_to_sample.items():
        key = f"E{row}"
        if key not in sheet_values or not sheet_values[key]:
            raise ValueError(f"Missing actual volume fraction in {key}")
        result[sample_number] = float(sheet_values[key])
    return result


def _read_component_densities(xlsx_path: Path) -> tuple[float, float]:
    sheet_values = _read_sheet_values(xlsx_path, "Sheet2")
    filler_density = float(sheet_values["B1"])
    matrix_density = float(sheet_values["B2"])
    return filler_density, matrix_density


def _load_diffusivity_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _mass_fraction(phi: float, filler_density: float, composite_density: float) -> float:
    return phi * filler_density / composite_density


def _composite_density(phi: float, filler_density: float, matrix_density: float) -> float:
    return phi * filler_density + (1.0 - phi) * matrix_density


def _composite_cp(phi: float, filler_density: float, matrix_density: float) -> float:
    density = _composite_density(phi, filler_density, matrix_density)
    filler_mass_fraction = _mass_fraction(phi, filler_density, density)
    return filler_mass_fraction * CR2TE3_CP_J_G_K + (1.0 - filler_mass_fraction) * PDMS_CP_J_G_K


def compute_results(
    diffusivity_csv: Path,
    vf_workbook: Path,
) -> List[SampleResult]:
    volume_fractions = _read_actual_volume_fractions(vf_workbook)
    filler_density, matrix_density = _read_component_densities(vf_workbook)
    results: List[SampleResult] = []

    for row in _load_diffusivity_rows(diffusivity_csv):
        sample_number = int(row["sample_number"])
        phi = volume_fractions[sample_number]
        diffusivity_mm2_s = float(row["mean_diffusivity_mm2_s"])
        diffusivity_std_mm2_s = float(row["stddev_diffusivity_mm2_s"])
        density = _composite_density(phi, filler_density, matrix_density)
        cp = _composite_cp(phi, filler_density, matrix_density)

        alpha_m2_s = diffusivity_mm2_s * 1e-6
        alpha_std_m2_s = diffusivity_std_mm2_s * 1e-6
        density_kg_m3 = density * 1000.0
        cp_j_kg_k = cp * 1000.0
        thermal_conductivity = alpha_m2_s * density_kg_m3 * cp_j_kg_k
        thermal_conductivity_std = alpha_std_m2_s * density_kg_m3 * cp_j_kg_k

        results.append(
            SampleResult(
                sample_number=sample_number,
                volume_fraction=phi,
                diffusivity_mm2_s=diffusivity_mm2_s,
                diffusivity_std_mm2_s=diffusivity_std_mm2_s,
                density_g_cm3=density,
                cp_j_g_k=cp,
                thermal_conductivity_w_m_k=thermal_conductivity,
                thermal_conductivity_std_w_m_k=thermal_conductivity_std,
            )
        )

    return results


def export_results_csv(results: Sequence[SampleResult], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_number",
                "cr2te3_volume_fraction",
                "diffusivity_mm2_s",
                "diffusivity_std_mm2_s",
                "density_g_cm3",
                "composite_cp_j_g_k",
                "thermal_conductivity_w_m_k",
                "thermal_conductivity_std_w_m_k",
            ]
        )
        for item in results:
            writer.writerow(
                [
                    item.sample_number,
                    f"{item.volume_fraction:.9f}",
                    f"{item.diffusivity_mm2_s:.6f}",
                    f"{item.diffusivity_std_mm2_s:.6f}",
                    f"{item.density_g_cm3:.6f}",
                    f"{item.cp_j_g_k:.6f}",
                    f"{item.thermal_conductivity_w_m_k:.6f}",
                    f"{item.thermal_conductivity_std_w_m_k:.6f}",
                ]
            )


def update_origin_project(origin_path: Path, results: Sequence[SampleResult]) -> None:
    op.set_show(False)
    op.open(str(origin_path), readonly=False, asksave=False)
    try:
        workbook = next(page for page in op.pages("w") if page.name == "Book1")
        worksheet = next(iter(workbook))

        worksheet.from_list(0, [item.sample_number for item in results], lname="Sample Number", axis="N")
        worksheet.from_list(
            1,
            [item.volume_fraction for item in results],
            lname="Cr2Te3 Volume Fraction",
            units="1",
            comments="Actual values from Sheet2 of 体积分数计算表.xlsx",
            axis="X",
        )
        worksheet.from_list(
            2,
            [item.diffusivity_mm2_s for item in results],
            lname="Diffusivity",
            units="mm^2/s",
            comments="Mean thermal diffusivity",
            axis="N",
        )
        worksheet.from_list(
            3,
            [item.diffusivity_std_mm2_s for item in results],
            lname="Diffusivity Std Dev",
            units="mm^2/s",
            comments="Std dev from LFA repeats",
            axis="N",
        )
        worksheet.from_list(
            4,
            [item.density_g_cm3 for item in results],
            lname="Composite Density",
            units="g/cm^3",
            comments="Calculated from volume fraction and component densities",
            axis="N",
        )
        worksheet.from_list(
            5,
            [item.cp_j_g_k for item in results],
            lname="Composite Cp",
            units="J/g/K",
            comments="Mass-weighted rule of mixtures at room temperature",
            axis="N",
        )
        worksheet.from_list(
            6,
            [item.thermal_conductivity_w_m_k for item in results],
            lname="Thermal Conductivity",
            units="W/m/K",
            comments="k = alpha * rho * Cp",
            axis="Y",
        )
        worksheet.from_list(
            7,
            [item.thermal_conductivity_std_w_m_k for item in results],
            lname="Thermal Conductivity Std Dev",
            units="W/m/K",
            comments="Propagated from diffusivity std dev only",
            axis="E",
        )

        graph = next(page for page in op.pages("g") if page.name == "Graph1")
        layer = list(graph)[0]
        plots = layer.plot_list()
        if not plots:
            layer.add_plot(worksheet, coly=6, colx=1, colyerr=7, type="y")
        else:
            plots[0].change_data(worksheet, x=1, y=6, yerr=7)
        layer.rescale()
        graph.lname = "Thermal Conductivity vs Cr2Te3 Volume Fraction"
        graph.lt_exec('label -xb "Cr2Te3 Volume Fraction";')
        graph.lt_exec('label -yl "Thermal Conductivity (W/m/K)";')
        op.save()
    finally:
        op.exit()


def print_summary(results: Iterable[SampleResult]) -> None:
    print(f"Temperature basis: {ROOM_TEMPERATURE_C:.1f} C")
    print(f"Cp(Cr2Te3) = {CR2TE3_CP_J_G_K:.3f} J/g/K")
    print(f"Cp(RTV615/PDMS) = {PDMS_CP_J_G_K:.3f} J/g/K")
    print()
    print(
        "sample\tphi\talpha(mm^2/s)\trho(g/cm^3)\tCp(J/g/K)\tk(W/m/K)\tk_std(W/m/K)"
    )
    for item in results:
        print(
            f"{item.sample_number}\t"
            f"{item.volume_fraction:.6f}\t"
            f"{item.diffusivity_mm2_s:.3f}\t"
            f"{item.density_g_cm3:.4f}\t"
            f"{item.cp_j_g_k:.4f}\t"
            f"{item.thermal_conductivity_w_m_k:.4f}\t"
            f"{item.thermal_conductivity_std_w_m_k:.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Cr2Te3/RTV615 thermal conductivity and update Origin")
    parser.add_argument(
        "--diffusivity-csv",
        type=Path,
        default=Path(r"f:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\extracted_lfa_diffusivity.csv"),
    )
    parser.add_argument(
        "--vf-workbook",
        type=Path,
        default=Path(r"f:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\体积分数计算表.xlsx"),
    )
    parser.add_argument(
        "--origin-project",
        type=Path,
        default=Path(r"f:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\Cr2Te3_LFA_4.22.opju"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path(r"f:\OneDrive - 草莓甜品屋\实验数据\Cr2Te3\LFA\4.22\computed_thermal_conductivity_vs_volume_fraction.csv"),
    )
    parser.add_argument(
        "--origin-out",
        type=Path,
        default=None,
        help="Optional output path. If provided, copy the Origin project and modify the copy.",
    )
    args = parser.parse_args()

    origin_target = args.origin_project
    if args.origin_out:
        args.origin_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.origin_project, args.origin_out)
        origin_target = args.origin_out

    results = compute_results(args.diffusivity_csv, args.vf_workbook)
    export_results_csv(results, args.output_csv)
    update_origin_project(origin_target, results)
    print_summary(results)
    print(f"Updated Origin project: {origin_target}")
    print(f"Exported CSV: {args.output_csv}")


if __name__ == "__main__":
    main()