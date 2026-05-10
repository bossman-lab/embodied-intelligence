import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


WORKSPACE_ROOT = Path(r"C:\oc\openclaw_ws")
ASCII_REPO_ROOT = Path(r"C:\openclaw_ascii")
PROJECT_ROOT = Path(r"C:\oc\VLM_Grasp_Interactive")
ROBOCASA_XML = (
    PROJECT_ROOT
    / "manipulator_grasp"
    / "assets"
    / "scenes"
    / "robocasa_layout51_style34_full.xml"
)
TEMPLATE_XML = (
    PROJECT_ROOT
    / "manipulator_grasp"
    / "assets"
    / "scenes"
    / "scene_simple_table.xml"
)
OUTPUT_XML = (
    PROJECT_ROOT
    / "manipulator_grasp"
    / "assets"
    / "scenes"
    / "scene_robocasa_layout51_style34.xml"
)
OBJECTS_REPO_ROOT = ASCII_REPO_ROOT if ASCII_REPO_ROOT.exists() else WORKSPACE_ROOT
ROBOCASA_OBJECTS_ROOT = (
    OBJECTS_REPO_ROOT
    / "sim"
    / "robocasa"
    / "robocasa"
    / "models"
    / "assets"
    / "objects"
)
TABLE_SURFACE_Z = 0.92
ROBOCASA_APPLE_MODEL = (
    ROBOCASA_OBJECTS_ROOT / "aigen_objs" / "apple" / "apple_0" / "model.xml"
)
ROBOCASA_PLATE_MODEL = (
    ROBOCASA_OBJECTS_ROOT / "objaverse" / "plate" / "plate_4" / "model.xml"
)
ADDITIONAL_OBJECTS = [
    {
        "instance": "DigitalScale",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "digital_scale"
        / "DigitalScale004"
        / "model.xml",
        "pos_xy": (4.18, -3.44),
        "euler": "0 0 0.25",
    },
    {
        "instance": "FlourBag",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "flour_bag"
        / "FlourBag008"
        / "model.xml",
        "pos_xy": (3.86, -3.46),
        "euler": "0 0 0.55",
    },
    {
        "instance": "FlowerVase",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "flower_vase"
        / "FlowerVase002"
        / "model.xml",
        "pos_xy": (4.92, -3.43),
        "euler": "0 0 0.0",
    },
    {
        "instance": "FruitBowl",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "fruit_bowl"
        / "FruitBowl001"
        / "model.xml",
        "pos_xy": (3.60, -3.70),
        "euler": "0 0 0.1",
    },
    {
        "instance": "GlassCup",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "glass_cup"
        / "GlassCup016"
        / "model.xml",
        "pos_xy": (4.45, -3.43),
        "euler": "0 0 0.0",
    },
    {
        "instance": "KnifeBlock",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "knife_block"
        / "KnifeBlock019"
        / "model.xml",
        "pos_xy": (4.90, -3.68),
        "euler": "0 0 -0.2",
    },
    {
        "instance": "MugTree",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "mug_tree"
        / "MugTree020"
        / "model.xml",
        "pos_xy": (3.63, -3.46),
        "euler": "0 0 0.15",
    },
    {
        "instance": "Shelf",
        "model": ROBOCASA_OBJECTS_ROOT
        / "lightwheel"
        / "tiered_shelf"
        / "Shelf010"
        / "model.xml",
        "pos_xy": (5.00, -3.83),
        "euler": "0 0 -1.57",
    },
]


def ensure_robocasa_scene():
    if ROBOCASA_XML.exists():
        return

    sys.path.insert(0, str(WORKSPACE_ROOT / "sim" / "robosuite"))
    sys.path.insert(0, str(WORKSPACE_ROOT / "sim" / "robocasa"))

    from robocasa.models.scenes.kitchen_arena import KitchenArena
    from robosuite.models.tasks import ManipulationTask

    arena = KitchenArena(layout_id=51, style_id=34, clutter_mode=0)
    model = ManipulationTask(
        mujoco_arena=arena,
        mujoco_robots=[],
        mujoco_objects=list(arena.fixtures.values()),
    )
    model.save_model(str(ROBOCASA_XML), pretty=False)


def unique_key(elem):
    return (elem.tag, elem.get("name"), elem.get("file"))


def append_unique_children(dst_parent, src_parent):
    seen = {unique_key(child) for child in dst_parent}
    for child in src_parent:
        key = unique_key(child)
        if key in seen:
            continue
        dst_parent.append(copy.deepcopy(child))
        seen.add(key)


def remove_matching_children(parent, predicate):
    for child in list(parent):
        if predicate(child):
            parent.remove(child)


def strip_robocasa_debug_visuals(node):
    for child in list(node):
        if child.tag == "geom":
            name = child.get("name", "")
            if "_reg_" in name or name.startswith("reg_") or name.endswith("_tray"):
                node.remove(child)
                continue
        if child.tag == "site":
            name = child.get("name", "")
            if (
                name.endswith("_default_site")
                or "_int_" in name
                or "_ext_" in name
                or name.endswith("_p2")
            ):
                node.remove(child)
                continue
        strip_robocasa_debug_visuals(child)


def parse_vec(value):
    return [float(v) for v in value.split()]


def absolutize_asset_files(node, base_dir):
    for elem in list(node.iter()):
        file_attr = elem.get("file")
        if not file_attr:
            continue
        file_path = Path(file_attr)
        resolved_path = None
        if file_path.is_absolute():
            if file_path.exists():
                resolved_path = file_path
        else:
            candidate = base_dir / file_path
            if candidate.exists():
                resolved_path = candidate

        if resolved_path is not None:
            elem.set("file", str(resolved_path))
            continue

        parent = None
        for maybe_parent in node.iter():
            if elem in list(maybe_parent):
                parent = maybe_parent
                break
        if parent is not None:
            parent.remove(elem)

    valid_texture_names = {
        child.get("name") for child in node if child.tag == "texture" and child.get("name")
    }
    remove_matching_children(
        node,
        lambda child: child.tag == "material"
        and child.get("texture")
        and child.get("texture") not in valid_texture_names,
    )


def collect_class_defaults(default_node):
    class_defaults = {}
    if default_node is None:
        return class_defaults
    for default in default_node.findall(".//default"):
        class_name = default.get("class")
        if not class_name:
            continue
        class_defaults[class_name] = {}
        geom = default.find("geom")
        site = default.find("site")
        if geom is not None:
            class_defaults[class_name]["geom"] = dict(geom.attrib)
        if site is not None:
            class_defaults[class_name]["site"] = dict(site.attrib)
    return class_defaults


def apply_class_defaults(node, class_defaults):
    for elem in node.iter():
        class_name = elem.attrib.pop("class", None)
        if not class_name:
            continue
        defaults = class_defaults.get(class_name, {})
        elem_defaults = defaults.get(elem.tag, {})
        for key, value in elem_defaults.items():
            elem.attrib.setdefault(key, value)


def strip_object_helper_geoms(node):
    for child in list(node):
        if child.tag == "geom":
            class_name = child.get("class", "")
            name = child.get("name", "")
            if class_name in {"region", "spawn"} or name.startswith("reg_") or name in {
                "liquid",
                "reg_int",
            }:
                node.remove(child)
                continue
        if child.tag == "site":
            node.remove(child)
            continue
        strip_object_helper_geoms(child)


def prefix_body_names(node, prefix):
    for elem in node.iter():
        name = elem.get("name")
        if not name:
            continue
        elem.set("name", f"{prefix}_{name}")


def prefix_asset_names(asset_node, body_node, prefix):
    name_map = {}
    for elem in asset_node.iter():
        if elem.tag not in {"mesh", "material", "texture"}:
            continue
        name = elem.get("name")
        if not name:
            continue
        new_name = f"{prefix}_{name}"
        name_map[(elem.tag, name)] = new_name
        elem.set("name", new_name)

    ref_attrs = {
        "geom": ("mesh", "material"),
        "material": ("texture",),
    }
    for node in (asset_node, body_node):
        for elem in node.iter():
            for attr in ref_attrs.get(elem.tag, ()):
                value = elem.get(attr)
                if not value:
                    continue
                key_tag = "texture" if attr == "texture" else attr
                new_value = name_map.get((key_tag, value))
                if new_value:
                    elem.set(attr, new_value)


def import_object_body(asset_parent, model_path, instance_name, pos_xy, euler=None):
    obj_tree = ET.parse(model_path)
    obj_root = obj_tree.getroot()
    obj_asset = copy.deepcopy(obj_root.find("asset"))
    class_defaults = collect_class_defaults(obj_root.find("default"))
    object_body = obj_root.find("./worldbody/body/body[@name='object']")
    body = copy.deepcopy(object_body)
    absolutize_asset_files(obj_asset, model_path.parent)
    prefix_asset_names(obj_asset, body, instance_name)
    append_unique_children(asset_parent, obj_asset)
    bbox = object_body.find("./geom[@name='reg_bbox']")
    if bbox is None:
        raise RuntimeError(f"reg_bbox not found in {model_path}")
    bbox_pos = parse_vec(bbox.get("pos"))
    bbox_size = parse_vec(bbox.get("size"))
    min_z = bbox_pos[2] - bbox_size[2]
    body_z = TABLE_SURFACE_Z - min_z

    prefix_body_names(body, instance_name)
    body.set("name", instance_name)
    body.set("pos", f"{pos_xy[0]:.6f} {pos_xy[1]:.6f} {body_z:.6f}")
    if euler is not None:
        body.set("euler", euler)
        body.attrib.pop("quat", None)
    strip_object_helper_geoms(body)
    apply_class_defaults(body, class_defaults)
    return body


def import_free_object_body(asset_parent, model_path, instance_name, pos_xy, euler=None):
    obj_tree = ET.parse(model_path)
    obj_root = obj_tree.getroot()
    obj_asset = copy.deepcopy(obj_root.find("asset"))
    class_defaults = collect_class_defaults(obj_root.find("default"))
    object_body = obj_root.find("./worldbody/body/body[@name='object']")
    body = copy.deepcopy(object_body)
    absolutize_asset_files(obj_asset, model_path.parent)
    prefix_asset_names(obj_asset, body, instance_name)
    append_unique_children(asset_parent, obj_asset)
    bbox = object_body.find("./geom[@name='reg_bbox']")
    if bbox is None:
        raise RuntimeError(f"reg_bbox not found in {model_path}")
    bbox_pos = parse_vec(bbox.get("pos"))
    bbox_size = parse_vec(bbox.get("size"))
    min_z = bbox_pos[2] - bbox_size[2]
    body_z = TABLE_SURFACE_Z - min_z + 0.002

    prefix_body_names(body, instance_name)
    body.set("name", instance_name)
    body.set("pos", f"{pos_xy[0]:.6f} {pos_xy[1]:.6f} {body_z:.6f}")
    if euler is not None:
        body.set("euler", euler)
        body.attrib.pop("quat", None)
    body.insert(
        0,
        ET.Element(
            "joint",
            {"name": f"{instance_name}_joint", "type": "free", "damping": "0.1"},
        ),
    )
    strip_object_helper_geoms(body)
    apply_class_defaults(body, class_defaults)
    return body


def remove_children(parent):
    for child in list(parent):
        parent.remove(child)


def set_body_pose(body, pos, quat=None, euler=None):
    body.set("pos", " ".join(f"{v:.6f}" for v in pos))
    if quat is not None:
        body.set("quat", quat)
        body.attrib.pop("euler", None)
    if euler is not None:
        body.set("euler", euler)
        body.attrib.pop("quat", None)


def build_scene():
    ensure_robocasa_scene()

    robo_tree = ET.parse(ROBOCASA_XML)
    robo_root = robo_tree.getroot()
    template_tree = ET.parse(TEMPLATE_XML)
    root = template_tree.getroot()

    root.set("model", "scene_robocasa_layout51_style34")

    compiler = root.find("compiler")
    compiler.set("inertiagrouprange", "0 0")

    size = root.find("size")
    if size is None:
        size = ET.Element("size")
        root.insert(list(root).index(root.find("option")) + 1, size)
    size.set("nconmax", "5000")
    size.set("njmax", "5000")

    statistic = root.find("statistic")
    statistic.set("center", "4.45 -2.90 1.30")
    statistic.set("extent", "5.20")
    statistic.set("meansize", "0.08")

    visual = root.find("visual")
    remove_children(visual)
    global_node = ET.SubElement(visual, "global")
    global_node.set("azimuth", "145")
    global_node.set("elevation", "-22")
    global_node.set("offheight", "1280")
    global_node.set("offwidth", "1280")

    for include in root.findall("include"):
        if include.get("file") == "../universal_robots_ur5e/ur5e.xml":
            include.set("file", "../universal_robots_ur5e/ur5e_robocasa.xml")

    asset = root.find("asset")
    remove_matching_children(
        asset,
        lambda child: child.tag == "texture"
        and child.get("builtin") in {"gradient", "checker"},
    )
    remove_matching_children(
        asset,
        lambda child: child.tag == "material" and child.get("name") == "groundplane",
    )
    append_unique_children(asset, robo_root.find("asset"))

    worldbody = root.find("worldbody")
    template_worldbody = ET.parse(TEMPLATE_XML).getroot().find("worldbody")

    remove_children(worldbody)
    robo_worldbody = robo_root.find("worldbody")
    for child in robo_worldbody:
        name = child.get("name", "")
        if name in {"left_eef_target", "right_eef_target"}:
            continue
        if name.startswith("stool_"):
            continue
        worldbody.append(copy.deepcopy(child))

    strip_robocasa_debug_visuals(worldbody)

    camera = ET.Element(
        "camera",
        {
            "name": "cam",
            "mode": "targetbody",
            "target": "island_island_group_1_main",
            "pos": "4.65 -5.55 2.15",
        },
    )
    worldbody.append(camera)

    mocap = template_worldbody.find("./body[@name='mocap']")
    set_body_pose(mocap, (4.05, -4.02, 0.92))
    worldbody.append(copy.deepcopy(mocap))

    custom_positions = {
        "Banana": ((4.52, -3.54, 1.04), "0 1 0 0", None),
        "Hammer": ((4.70, -3.69, 1.04), "0 0 1 0", None),
        "Knife": ((4.62, -3.79, 1.04), None, "0 0 0"),
        "Duck": ((4.82, -3.84, 1.04), None, "0 0 2.2"),
    }
    for name, (pos, quat, euler) in custom_positions.items():
        body = template_worldbody.find(f"./body[@name='{name}']")
        set_body_pose(body, pos, quat=quat, euler=euler)
        worldbody.append(copy.deepcopy(body))

    worldbody.append(
        import_free_object_body(
            asset,
            ROBOCASA_APPLE_MODEL,
            "Apple",
            (4.28, -3.46),
            euler="0 0 0.35",
        )
    )

    worldbody.append(
        import_object_body(
            asset,
            ROBOCASA_PLATE_MODEL,
            "Plate",
            (4.74, -3.50),
            euler="0 0 0",
        )
    )

    for spec in ADDITIONAL_OBJECTS:
        worldbody.append(
            import_object_body(
                asset,
                spec["model"],
                spec["instance"],
                spec["pos_xy"],
                euler=spec.get("euler"),
            )
        )

    tree = ET.ElementTree(root)
    tree.write(OUTPUT_XML, encoding="utf-8", xml_declaration=False)
    print(OUTPUT_XML)


if __name__ == "__main__":
    build_scene()
