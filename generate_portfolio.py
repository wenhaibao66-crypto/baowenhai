import base64
import html
import json
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(r"C:\Users\bao\Documents\Codex\2026-06-05\files-mentioned-by-the-user-pdf-4")
WORK = ROOT / "work"
PDF_DIR = WORK / "pdfs"
ASSET_BASE_NAME = "baowenhai-portfolio-assets"
ASSET_GROUP_SIZE = 10
STAGING_ASSET_DIR = WORK / "generated-assets"
OUTPUT_HTML = ROOT / "outputs" / "baowenhai-portfolio.html"
RESUME_HTML = WORK / "resume-source.html"
PORTRAIT_PNG = Path(r"C:\Users\bao\Downloads\export_1780583771956.png")


def ensure_dirs() -> None:
    (ROOT / "outputs").mkdir(parents=True, exist_ok=True)
    STAGING_ASSET_DIR.mkdir(parents=True, exist_ok=True)


def clear_asset_dirs() -> None:
    outputs_dir = ROOT / "outputs"
    for folder in outputs_dir.iterdir():
        if folder.is_dir() and folder.name.startswith(ASSET_BASE_NAME):
            for item in folder.iterdir():
                if item.is_file():
                    item.unlink()
            folder.rmdir()
    for item in STAGING_ASSET_DIR.iterdir():
        if item.is_file():
            item.unlink()

def asset_output_path(filename: str) -> Path:
    return STAGING_ASSET_DIR / filename


def asset_group_name_by_index(index: int) -> str:
    return f"{ASSET_BASE_NAME}-{index:02d}"


def asset_map_from_projects(projects: list[dict]) -> dict[str, str]:
    ordered_names = ["headshot.jpg"]
    for project in projects:
        ordered_names.append(project["hero_file"])
        ordered_names.extend(item["file"] for item in project["gallery_files"])

    asset_map: dict[str, str] = {}
    unique_names: list[str] = []
    seen: set[str] = set()
    for name in ordered_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    for idx, name in enumerate(unique_names, start=1):
        group_index = ((idx - 1) // ASSET_GROUP_SIZE) + 1
        asset_map[name] = f"{asset_group_name_by_index(group_index)}/{name}"
    return asset_map


def distribute_assets(asset_map: dict[str, str]) -> list[Path]:
    created_dirs: dict[str, Path] = {}
    for filename, relative_path in asset_map.items():
        source = STAGING_ASSET_DIR / filename
        folder_name, _, target_name = relative_path.partition("/")
        target_dir = created_dirs.setdefault(folder_name, ROOT / "outputs" / folder_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        source.replace(target_dir / target_name)
    return [created_dirs[name] for name in sorted(created_dirs)]


def asset_public_path(filename: str, asset_map: dict[str, str]) -> str:
    return asset_map[filename]


def export_pdf_image(image, output_name: str) -> str:
    has_alpha = image.mode in ("RGBA", "LA") or ("transparency" in image.info)
    if has_alpha:
        filename = f"{output_name}.png"
        out_path = asset_output_path(filename)
        image.save(out_path, format="PNG")
    else:
        filename = f"{output_name}.jpg"
        out_path = asset_output_path(filename)
        image.convert("RGB").save(out_path, format="JPEG", quality=92, optimize=True)
    return out_path.name


def save_image_from_pdf(pdf_name: str, page_no: int, output_name: str) -> str:
    reader = PdfReader(str(PDF_DIR / pdf_name))
    page = reader.pages[page_no - 1]
    images = list(page.images)
    if not images:
        raise ValueError(f"{pdf_name} page {page_no} has no images")

    largest = None
    largest_area = -1
    for img in images:
        try:
            size = img.image.size
        except Exception:
            continue
        area = size[0] * size[1]
        if area > largest_area:
            largest_area = area
            largest = img

    if largest is None:
        raise ValueError(f"{pdf_name} page {page_no} has no readable images")

    return export_pdf_image(largest.image, output_name)


def save_named_image_from_pdf(pdf_name: str, page_no: int, image_name: str, output_name: str) -> str:
    reader = PdfReader(str(PDF_DIR / pdf_name))
    page = reader.pages[page_no - 1]
    for img in list(page.images):
        if img.name == image_name:
            return export_pdf_image(img.image, output_name)
    return save_image_from_pdf(pdf_name, page_no, output_name)


def crop_portrait(output_name: str) -> str:
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(Image.open(PORTRAIT_PNG)).convert("RGBA")
    background = Image.new("RGBA", img.size, (241, 236, 228, 255))
    background.alpha_composite(img)
    portrait = background.convert("RGB")
    if portrait.height > 1800:
        scale = 1800 / portrait.height
        portrait = portrait.resize((int(portrait.width * scale), 1800), Image.LANCZOS)
    filename = f"{output_name}.jpg"
    out_path = asset_output_path(filename)
    portrait.save(out_path, quality=92, optimize=True)
    return out_path.name


def inline_headshot() -> str:
    portrait_file = STAGING_ASSET_DIR / "headshot.jpg"
    data = base64.b64encode(portrait_file.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{data}"


def get_resume_summary() -> dict:
    text = RESUME_HTML.read_text(encoding="utf-8")
    return {
        "name": "包文海",
        "title": "室内设计师 · 空间方案与落地深化",
        "tagline": "以高端住宅、样板间与商业空间为核心，兼具效果表达、施工图深化与落地协同能力。",
        "phone": "159 5190 5739",
        "email": "2649678740@qq.com",
        "city": "南京",
        "availability": "离职状态，可到岗（2026.07）",
        "education": [
            "南京理工大学继续教育学院 · 环境艺术设计本科 · 2021.09 - 2022.07",
            "江苏工程职业技术学院 · 环境艺术设计大专 · 2019.09 - 2021.07",
        ],
        "skills": [
            "SketchUp",
            "CAD",
            "Enscape",
            "D5 Render",
            "Photoshop",
            "Illustrator",
            "CorelDRAW",
            "Blender",
            "AI辅助设计（MJ / SD）",
            "全案落地流程",
        ],
        "strengths": [
            "独立承担量房、方案深化、施工图、效果图与落地跟进，具备完整项目闭环能力。",
            "擅长通过材质、灯光与软硬装整合强化空间气质，提升方案呈现与决策效率。",
            "具备跨客户、施工方、工厂与软装团队的协同经验，注重结果与落地还原。",
        ],
        "experience": [
            {
                "role": "方案设计师（效果图 / 施工图方向）",
                "company": "南京肌理里约设计有限公司",
                "date": "2025.11 - 至今",
                "bullets": [
                    "负责高端样板房、售楼处与办公空间效果图及施工图，累计完成 12+ 项目。",
                    "配合软硬装团队精准还原材质与灯光，方案中标率提升约 30%。",
                    "独立对接深化需求，把控图纸规范，减少施工变更平均 5 次 / 项目。",
                ],
            },
            {
                "role": "室内设计师",
                "company": "知间建筑工程（句容）有限公司",
                "date": "2024.01 - 2025.10",
                "bullets": [
                    "全流程负责私宅及小型商业空间设计，对接客户 50+ 位，方案通过率 92%。",
                    "独立完成量房、概念方案、施工图、主材定样及成本管控，预算偏差小于 8%。",
                    "跟踪施工现场并解决技术问题 40+ 项，项目落地还原度达 95% 以上。",
                ],
            },
            {
                "role": "设计师助理",
                "company": "溧水名匠装饰",
                "date": "2023.04 - 2024.01",
                "bullets": [
                    "参与 500㎡、700㎡ 别墅及 200㎡ 办公室项目施工图与效果图制作。",
                    "独立完成 128㎡ 住宅全案，覆盖量房、方案、施工图、效果图与落地。",
                    "输出 CAD 图纸、SketchUp 模型与 D5 全景漫游，协助主案缩短绘图周期约 20%。",
                ],
            },
        ],
        "featured_table": [
            ("国家电网（南京）会议室及3个展厅设计", "2024.03 - 2024.08", "独立完成概念方案、效果图、施工图，并全程参与施工交底，提前 7 天交付。"),
            ("徐州紫薇公馆 / 泰州长江国际豪宅（施工图深化）", "2024.01 - 2024.06", "配合深圳总部绘制高精度施工图 30+ 张，图纸修改率低于 5%。"),
            ("南京金陵序 / 天琴华章 / 江湾境 / 长江之歌样板房效果图", "2025.11 - 2026.06", "为多个高端楼盘制作软装效果图，精准呈现材质与光影，直接促成 2 套样板间方案通过。"),
            ("石虎名苑 · 128㎡ 单身住宅全案设计", "2023.10 - 2024.01", "独立完成量房、平面、施工图、全景效果图与漫游视频，客户满意度 9.5 / 10。"),
        ],
        "resume_file_used": "包文海" in text,
    }


def build_projects() -> list[dict]:
    definitions = [
        {
            "id": "jinling-soft",
            "title": "南京金陵序 176户型软装设计",
            "category": "高端住宅 / 软装概念",
            "year": "2026",
            "location": "南京",
            "area": "176户型",
            "overview": "围绕都市雅奢气质展开，以细腻的材质组合和稳定的空间秩序，塑造精英家庭的高品质居住场景。",
            "roles": ["方案深化", "空间效果图", "软装气质表达"],
            "pdf_name": "doc04.pdf",
            "hero_page": 15,
            "gallery": [8, 10, 12, 13, 15, 18, 19, 22, 25, 28, 31, 33],
        },
        {
            "id": "jinling-soft-1103",
            "title": "金陵序 176户型软装方案 · 3-1103",
            "category": "高端住宅 / 软装方案",
            "year": "2026",
            "location": "南京",
            "area": "176户型",
            "overview": "围绕金陵序 176 中间户私宅展开，以暖灰石材、木饰面与柔和家具关系为主线，营造兼具都会质感与家庭温度的客餐厅与卧室场景。",
            "roles": ["软装方案深化", "空间效果图", "材质与家具搭配"],
            "pdf_name": "doc12.pdf",
            "hero_page": 8,
            "gallery": [5, 6, 7, 8, 10, 11, 12, 15, 18, 21, 24, 25],
        },
        {
            "id": "jinling-soft-3504",
            "title": "金陵序 176户型软装方案 · 3-504",
            "category": "高端住宅 / 软装方案",
            "year": "2026",
            "location": "南京",
            "area": "176户型",
            "overview": "以更克制的浅灰与暖木为基底，强化客餐厅通透感、卧室舒适度与露台休闲氛围，形成完整且可落地的私宅软装表达。",
            "roles": ["软装方案深化", "空间效果图", "露台生活场景"],
            "pdf_name": "doc13.pdf",
            "hero_page": 7,
            "gallery": [6, 7, 8, 10, 11, 12, 13, 17, 19, 23, 27, 28],
            "named_images": {
                4: "IM58.jpg",
                5: "IM63.jpg",
                6: "IM68.jpg",
                7: "IM79.jpg",
                8: "IM84.jpg",
                10: "IM97.jpg",
                11: "IM102.jpg",
                12: "IM107.jpg",
                13: "IM110.jpg",
                15: "IM130.jpg",
                16: "IM133.jpg",
                17: "IM138.jpg",
                18: "IM143.jpg",
                19: "IM148.jpg",
                20: "IM155.jpg",
                21: "IM160.jpg",
                23: "IM170.jpg",
                24: "IM176.jpg",
                25: "IM183.jpg",
                26: "IM188.jpg",
                27: "IM194.jpg",
                28: "IM199.jpg",
            },
        },
        {
            "id": "tianqin-300",
            "title": "天琴华樟 300户型设计方案",
            "category": "样板房 / 大平层",
            "year": "2025",
            "location": "南京",
            "area": "300户型",
            "overview": "以“水”为灵感母题，通过奢石、古木、皮革与金属的层叠关系，构建兼具秩序感与艺术性的家庭空间。",
            "roles": ["概念表达", "平面优化", "空间效果图"],
            "pdf_name": "doc05.pdf",
            "hero_page": 8,
            "gallery": [5, 6, 8, 9, 12, 14, 17, 20, 21, 23, 32, 35, 37, 42],
        },
        {
            "id": "tianqin-soft-345",
            "title": "天琴华樟 345户型软装设计方案",
            "category": "高端住宅 / 软装概念",
            "year": "2026",
            "location": "南京",
            "area": "345户型",
            "overview": "以轻奢暖调与流动曲线统领客餐厅、茶室、主卧与书房关系，在更开阔的 345 户型中塑造兼具会客仪式感与日常居住舒适度的软装氛围。",
            "roles": ["软装方案深化", "空间效果图", "整体氛围营造"],
            "pdf_name": "doc14.pdf",
            "hero_page": 9,
            "gallery": [6, 8, 9, 10, 12, 13, 14, 15, 18, 19, 23, 24, 27, 29, 30],
        },
        {
            "id": "jinling-hard",
            "title": "金陵序 176户型空间效果方案",
            "category": "样板房 / 硬装基调",
            "year": "2026",
            "location": "南京",
            "area": "176户型",
            "overview": "聚焦私家电梯前室、客餐厅、主卧、女孩房、阳台与书房等重点界面，通过克制的材质与光感营造高端居住体验。",
            "roles": ["空间效果图", "平面方案推演", "效果表达"],
            "pdf_name": "doc06.pdf",
            "hero_page": 7,
            "gallery": [5, 7, 9, 10, 13, 14, 15, 18, 19, 23, 24, 26],
            "named_images": {
                5: "IM87.jpg",
                6: "IM99.jpg",
                7: "IM104.jpg",
                9: "IM116.jpg",
                10: "IM121.jpg",
                13: "IM138.jpg",
                14: "IM145.jpg",
                15: "IM151.jpg",
                18: "IM168.jpg",
                19: "IM173.jpg",
                23: "IM192.jpg",
                24: "IM197.jpg",
                26: "IM208.jpg",
            },
        },
        {
            "id": "changjiang-song",
            "title": "伟星长江之歌 王总效果图方案",
            "category": "私宅 / 效果图呈现",
            "year": "2026",
            "location": "南京",
            "area": "定制私宅",
            "overview": "从玄关、客厅、主卧到男孩房，完成一套具备完整叙事节奏的私宅空间效果图方案。",
            "roles": ["效果图方案", "空间视角组织", "视觉表达"],
            "pdf_name": "doc03.pdf",
            "hero_page": 7,
            "gallery": [5, 6, 8, 9, 10, 11, 12, 13, 14, 18, 19],
        },
        {
            "id": "changjiang-garden",
            "title": "泰兴长江国际豪宅概念方案",
            "category": "别墅 / 概念方案",
            "year": "2025",
            "location": "泰兴",
            "area": "多层豪宅",
            "overview": "覆盖五层空间与庭院场景，从平面规划到室内意向图，形成完整的别墅概念设计表达。",
            "roles": ["概念方案", "空间意向", "多层住宅表达"],
            "pdf_name": "doc08.pdf",
            "hero_page": 20,
            "gallery": [20, 21, 22, 24, 25, 26, 29, 31, 33, 38, 45, 52, 53, 54, 55],
        },
        {
            "id": "xijiu",
            "title": "南京习酒君品馆设计方案",
            "category": "商业空间 / 展示会所",
            "year": "2025",
            "location": "南京",
            "area": "750㎡",
            "overview": "围绕品牌展示、前厅流线与包间体验展开，兼顾宴请氛围、工艺展示与商业接待效率。",
            "roles": ["商业空间方案", "效果图展示", "功能分区表达"],
            "pdf_name": "doc10.pdf",
            "hero_page": 15,
            "gallery": [6, 7, 8, 10, 11, 12, 13, 15, 17, 18, 20],
        },
        {
            "id": "yunshang-140",
            "title": "云尚紫薇 140方效果图方案",
            "category": "住宅 / 效果图方案",
            "year": "2025",
            "location": "徐州",
            "area": "140㎡",
            "overview": "在舒适、品质、人文与艺术之间寻找平衡，重点展示客厅、餐厅、主卧与儿童房的生活氛围。",
            "roles": ["效果图方案", "住宅氛围营造", "空间表达"],
            "pdf_name": "doc11.pdf",
            "hero_page": 15,
            "gallery": [14, 15, 16, 18, 19, 21, 24, 25, 27, 29, 30, 32],
        },
        {
            "id": "jinji",
            "title": "金基底跃效果图方案",
            "category": "复式住宅 / 效果图方案",
            "year": "2025",
            "location": "南京",
            "area": "底跃住宅",
            "overview": "从负一层玄关到一层主卧，结合软装单品体系，呈现完整的复式住宅生活场景与空间气质。",
            "roles": ["复式住宅效果图", "软装整合", "空间视觉呈现"],
            "pdf_name": "doc07.pdf",
            "hero_page": 18,
            "gallery": [14, 15, 16, 17, 18, 21, 22, 23, 24, 25, 27, 28],
        },
    ]

    projects = []
    for project in definitions:
        named_images = project.get("named_images", {})
        hero_page = project["hero_page"]
        if hero_page in named_images:
            hero_file = save_named_image_from_pdf(
                project["pdf_name"], hero_page, named_images[hero_page], f"{project['id']}-hero"
            )
        else:
            hero_file = save_image_from_pdf(project["pdf_name"], hero_page, f"{project['id']}-hero")

        gallery_files = []
        for index, page in enumerate(project["gallery"], start=1):
            if page in named_images:
                file_name = save_named_image_from_pdf(
                    project["pdf_name"], page, named_images[page], f"{project['id']}-{index:02d}"
                )
            else:
                file_name = save_image_from_pdf(project["pdf_name"], page, f"{project['id']}-{index:02d}")
            gallery_files.append({"page": page, "file": file_name})

        projects.append({**project, "hero_file": hero_file, "gallery_files": gallery_files})
    return projects


def build_html(resume: dict, projects: list[dict], asset_map: dict[str, str]) -> str:
    portrait_src = inline_headshot()
    def asset_src(filename: str) -> str:
        return asset_public_path(filename, asset_map)
    nav_items = "".join(
        f'<a href="#{p["id"]}" class="nav-link">{html.escape(p["title"])}</a>' for p in projects
    )
    project_cards = "".join(
        f"""
        <a href="#{html.escape(p["id"])}" class="project-card-link">
          <article class="project-card">
            <div class="project-card-image">
              <img src="{html.escape(asset_src(p["hero_file"]))}" alt="{html.escape(p["title"])} 主图">
            </div>
            <div class="project-card-body">
              <div class="project-meta-row">
                <span>{html.escape(p["category"])}</span>
                <span>{html.escape(p["location"])} · {html.escape(p["year"])}</span>
              </div>
              <h3>{html.escape(p["title"])}</h3>
              <p>{html.escape(p["overview"])}</p>
              <div class="tag-list">
                {''.join(f'<span>{html.escape(tag)}</span>' for tag in p["roles"])}
              </div>
            </div>
          </article>
        </a>
        """
        for p in projects
    )
    detailed_sections = "".join(
        f"""
        <section class="case-section" id="{html.escape(p["id"])}">
          <div class="case-heading">
            <div>
              <div class="eyebrow">Selected Project</div>
              <h2>{html.escape(p["title"])}</h2>
            </div>
            <div class="case-facts">
              <span>{html.escape(p["category"])}</span>
              <span>{html.escape(p["area"])}</span>
              <span>{html.escape(p["location"])}</span>
              <span>{html.escape(p["year"])}</span>
            </div>
          </div>
          <div class="case-intro">
            <div class="case-copy">
              <p>{html.escape(p["overview"])}</p>
              <ul class="role-list">
                {''.join(f'<li>{html.escape(role)}</li>' for role in p["roles"])}
              </ul>
            </div>
            <div class="case-cover">
              <img src="{html.escape(asset_src(p["hero_file"]))}" alt="{html.escape(p["title"])} 封面图">
            </div>
          </div>
          <div class="gallery-grid">
            {''.join(
                f'<figure class="gallery-item"><img src="{html.escape(asset_src(item["file"]))}" alt="{html.escape(p["title"])} 页面 {item["page"]}"></figure>'
                for item in p["gallery_files"]
            )}
          </div>
        </section>
        """
        for p in projects
    )
    experience_blocks = "".join(
        f"""
        <div class="timeline-item">
          <div class="timeline-top">
            <h4>{html.escape(item["role"])}</h4>
            <span>{html.escape(item["date"])}</span>
          </div>
          <div class="timeline-company">{html.escape(item["company"])}</div>
          <ul class="timeline-list">
            {''.join(f'<li>{html.escape(bullet)}</li>' for bullet in item["bullets"])}
          </ul>
        </div>
        """
        for item in resume["experience"]
    )
    featured_rows = "".join(
        f"""
        <tr>
          <td>{html.escape(name)}</td>
          <td>{html.escape(date)}</td>
          <td>{html.escape(result)}</td>
        </tr>
        """
        for name, date, result in resume["featured_table"]
    )
    skill_badges = "".join(f"<span>{html.escape(skill)}</span>" for skill in resume["skills"])
    strength_list = "".join(f"<li>{html.escape(item)}</li>" for item in resume["strengths"])
    education_list = "".join(f"<li>{html.escape(item)}</li>" for item in resume["education"])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1360, initial-scale=0.28, minimum-scale=0.22, maximum-scale=2.5, user-scalable=yes">
  <title>包文海 · 室内设计作品集</title>
  <style>
    :root {{
      --bg: #efe8de;
      --paper: #f9f6f1;
      --surface: #ffffff;
      --ink: #1f1914;
      --muted: #76675b;
      --line: rgba(73, 58, 43, 0.15);
      --accent: #8d5e3b;
      --accent-deep: #5e3a1d;
      --olive: #8b9272;
      --shadow: 0 18px 40px rgba(42, 28, 18, 0.12);
    }}

    * {{
      box-sizing: border-box;
    }}

    html {{
      scroll-behavior: smooth;
    }}

    body {{
      margin: 0;
      font-family: "Georgia", "Times New Roman", "PingFang SC", "Microsoft YaHei", serif;
      color: var(--ink);
      overflow-x: hidden;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.72), transparent 30%),
        linear-gradient(180deg, #e8dfd3 0%, #efe8de 18%, #f5f1eb 100%);
    }}

    img {{
      max-width: 100%;
      display: block;
    }}

    a {{
      color: inherit;
      text-decoration: none;
    }}

    .shell {{
      width: min(1360px, calc(100vw - 40px));
      margin: 18px auto 40px;
      background: rgba(249, 246, 241, 0.86);
      border: 1px solid rgba(95, 73, 55, 0.12);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
      overflow: hidden;
      position: relative;
    }}

    .shell::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(115deg, rgba(141,94,59,0.06), transparent 35%),
        linear-gradient(180deg, transparent 0%, rgba(139,146,114,0.07) 100%);
      pointer-events: none;
    }}

    .topbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      gap: 18px;
      align-items: center;
      justify-content: space-between;
      padding: 18px 28px;
      background: rgba(249, 246, 241, 0.9);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(12px);
    }}

    .brand {{
      display: flex;
      gap: 12px;
      align-items: center;
      min-width: 0;
    }}

    .brand-mark {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, var(--accent) 0%, #b48764 100%);
      color: white;
      font-size: 14px;
      letter-spacing: 0.25em;
      box-shadow: 0 10px 20px rgba(93, 58, 30, 0.18);
    }}

    .brand-copy {{
      min-width: 0;
    }}

    .brand-copy strong {{
      display: block;
      font-size: 16px;
      letter-spacing: 0.08em;
    }}

    .brand-copy span {{
      display: block;
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      justify-content: flex-end;
    }}

    .nav-link {{
      font-size: 12px;
      color: var(--muted);
      padding-bottom: 2px;
      border-bottom: 1px solid transparent;
      transition: border-color 0.2s ease, color 0.2s ease;
    }}

    .nav-link:hover {{
      color: var(--accent-deep);
      border-color: var(--accent);
    }}

    .hero {{
      display: grid;
      grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.3fr);
      gap: 0;
      min-height: 720px;
      position: relative;
    }}

    .hero-left {{
      padding: 58px 42px 42px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255,255,255,0.36)),
        linear-gradient(150deg, rgba(141,94,59,0.18), rgba(141,94,59,0.03));
      border-right: 1px solid var(--line);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .hero-right {{
      padding: 54px 52px 56px;
      position: relative;
      overflow: hidden;
    }}

    .hero-right::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at 75% 18%, rgba(139,146,114,0.18), transparent 28%),
        radial-gradient(circle at 88% 75%, rgba(141,94,59,0.12), transparent 30%);
      pointer-events: none;
    }}

    .portrait-wrap {{
      display: inline-flex;
      flex-direction: column;
      gap: 18px;
      align-items: flex-start;
    }}

    .portrait-frame {{
      width: min(100%, 248px);
      background:
        radial-gradient(circle at top, rgba(255,255,255,0.95), rgba(255,255,255,0.52) 58%, rgba(230, 220, 209, 0.85) 100%);
      padding: 14px;
      border-radius: 28px;
      border: 1px solid rgba(95, 73, 55, 0.14);
      box-shadow: 0 18px 36px rgba(42, 28, 18, 0.1);
    }}

    .portrait-frame img {{
      width: 100%;
      aspect-ratio: 0.74 / 1.34;
      object-fit: contain;
      border-radius: 20px;
      filter: saturate(0.98) contrast(1.02);
      object-position: center top;
      background: linear-gradient(180deg, #f7f2eb, #ece1d4);
    }}

    .portrait-note {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 12px;
      background: rgba(255,255,255,0.7);
      color: var(--muted);
      border: 1px solid rgba(95, 73, 55, 0.1);
    }}

    .contact-panel {{
      display: grid;
      gap: 14px;
      margin-top: 36px;
    }}

    .contact-item {{
      display: flex;
      gap: 12px;
      align-items: flex-start;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(95, 73, 55, 0.09);
    }}

    .contact-item:last-child {{
      border-bottom: none;
    }}

    .contact-label {{
      width: 48px;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      padding-top: 3px;
    }}

    .contact-value strong {{
      display: block;
      font-size: 14px;
      margin-bottom: 4px;
    }}

    .contact-value span {{
      display: block;
      font-size: 14px;
      color: var(--muted);
    }}

    .eyebrow {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.26em;
      color: var(--accent);
      margin-bottom: 16px;
    }}

    .hero-title {{
      font-size: clamp(40px, 5vw, 78px);
      line-height: 0.96;
      letter-spacing: -0.04em;
      margin: 0 0 18px;
      max-width: 720px;
      position: relative;
      z-index: 1;
    }}

    .hero-subtitle {{
      max-width: 620px;
      font-size: 18px;
      line-height: 1.9;
      color: #56483d;
      margin: 0 0 28px;
      position: relative;
      z-index: 1;
    }}

    .hero-stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 36px;
      position: relative;
      z-index: 1;
    }}

    .stat {{
      background: rgba(255,255,255,0.66);
      border: 1px solid rgba(95, 73, 55, 0.1);
      padding: 18px 16px;
      border-radius: 18px;
      min-height: 112px;
    }}

    .stat strong {{
      display: block;
      font-size: 32px;
      margin-bottom: 6px;
      color: var(--accent-deep);
    }}

    .stat span {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }}

    .section {{
      padding: 62px 44px;
      border-top: 1px solid var(--line);
      position: relative;
    }}

    .section-heading {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: end;
      margin-bottom: 28px;
    }}

    .section-heading h2 {{
      margin: 8px 0 0;
      font-size: clamp(30px, 3vw, 48px);
      line-height: 1.02;
      letter-spacing: -0.04em;
    }}

    .section-heading p {{
      max-width: 620px;
      margin: 0;
      color: var(--muted);
      line-height: 1.9;
    }}

    .intro-grid {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 22px;
    }}

    .panel {{
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(95, 73, 55, 0.11);
      border-radius: 24px;
      padding: 26px;
      box-shadow: 0 14px 30px rgba(42, 28, 18, 0.06);
    }}

    .panel h3 {{
      margin: 0 0 14px;
      font-size: 18px;
      letter-spacing: 0.02em;
    }}

    .panel p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.9;
      font-size: 15px;
    }}

    .skill-cloud, .tag-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}

    .skill-cloud span, .tag-list span, .case-facts span {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 12px;
      background: rgba(141,94,59,0.08);
      color: var(--accent-deep);
      border: 1px solid rgba(141,94,59,0.12);
    }}

    .text-list {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.9;
    }}

    .text-list li + li {{
      margin-top: 8px;
    }}

    .timeline {{
      display: grid;
      gap: 18px;
    }}

    .timeline-item {{
      background: rgba(255,255,255,0.68);
      border: 1px solid rgba(95, 73, 55, 0.1);
      border-radius: 22px;
      padding: 22px 24px;
    }}

    .timeline-top {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
      margin-bottom: 6px;
    }}

    .timeline-top h4 {{
      margin: 0;
      font-size: 21px;
      line-height: 1.2;
    }}

    .timeline-top span, .timeline-company {{
      color: var(--muted);
    }}

    .timeline-company {{
      margin-bottom: 14px;
      font-size: 14px;
    }}

    .timeline-list {{
      margin: 0;
      padding-left: 18px;
      color: #51443a;
      line-height: 1.9;
    }}

    .project-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 22px;
    }}

    .project-card-link {{
      display: block;
    }}

    .project-card {{
      background: rgba(255,255,255,0.74);
      border-radius: 26px;
      overflow: hidden;
      border: 1px solid rgba(95, 73, 55, 0.12);
      box-shadow: 0 14px 34px rgba(42, 28, 18, 0.08);
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}

    .project-card-link:hover .project-card {{
      transform: translateY(-4px);
      box-shadow: 0 18px 38px rgba(42, 28, 18, 0.12);
    }}

    .project-card-image {{
      aspect-ratio: 1.48 / 1;
      overflow: hidden;
      background: #ded6ca;
      min-height: 0;
    }}

    .project-card-image img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.5s ease;
    }}

    .project-card-link:hover img {{
      transform: scale(1.04);
    }}

    .project-card-body {{
      padding: 22px 22px 24px;
    }}

    .project-meta-row {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 10px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .project-card h3 {{
      margin: 0 0 10px;
      font-size: 26px;
      line-height: 1.1;
      letter-spacing: -0.03em;
    }}

    .project-card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.85;
      font-size: 15px;
    }}

    .feature-table-wrap {{
      overflow: auto;
      border-radius: 20px;
      border: 1px solid rgba(95, 73, 55, 0.12);
      background: rgba(255,255,255,0.72);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }}

    th, td {{
      padding: 18px 18px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid rgba(95, 73, 55, 0.08);
      line-height: 1.75;
      font-size: 14px;
    }}

    th {{
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      background: rgba(141,94,59,0.05);
    }}

    .case-section {{
      scroll-margin-top: 92px;
    }}

    .case-section + .case-section {{
      margin-top: 48px;
    }}

    .case-heading {{
      display: flex;
      justify-content: space-between;
      gap: 22px;
      align-items: end;
      margin-bottom: 24px;
    }}

    .case-heading h2 {{
      margin: 8px 0 0;
      font-size: clamp(30px, 3vw, 50px);
      line-height: 1.02;
      letter-spacing: -0.04em;
    }}

    .case-facts {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: flex-end;
    }}

    .case-intro {{
      display: grid;
      grid-template-columns: 0.88fr 1.12fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 22px;
    }}

    .case-copy {{
      background: rgba(255,255,255,0.7);
      border: 1px solid rgba(95, 73, 55, 0.11);
      border-radius: 24px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 18px;
    }}

    .case-copy p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.9;
      font-size: 15px;
    }}

    .role-list {{
      margin: 0;
      padding-left: 18px;
      line-height: 1.85;
      color: #51443a;
    }}

    .case-cover {{
      border-radius: 26px;
      overflow: hidden;
      background: #ddd4c8;
      border: 1px solid rgba(95, 73, 55, 0.11);
      min-height: 420px;
    }}

    .case-cover img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center center;
    }}

    .gallery-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }}

    .gallery-item {{
      margin: 0;
      border-radius: 20px;
      overflow: hidden;
      border: 1px solid rgba(95, 73, 55, 0.11);
      background: rgba(255,255,255,0.78);
      box-shadow: 0 12px 24px rgba(42, 28, 18, 0.06);
    }}

    .gallery-item img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      aspect-ratio: 1.15 / 1;
      object-position: center center;
    }}

    .footer {{
      padding: 42px 44px 54px;
      border-top: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
      color: var(--muted);
      background: linear-gradient(180deg, rgba(255,255,255,0.2), rgba(141,94,59,0.05));
    }}

    .footer strong {{
      display: block;
      color: var(--accent-deep);
      margin-bottom: 8px;
      font-size: 14px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}

    .footer p {{
      margin: 0;
      line-height: 1.85;
      font-size: 14px;
    }}

    @media (max-width: 1100px) and (min-width: 99999px) {{
      .hero,
      .intro-grid,
      .case-intro,
      .project-grid {{
        grid-template-columns: 1fr;
      }}

      .hero {{
        min-height: auto;
      }}

      .hero-left {{
        border-right: none;
        border-bottom: 1px solid var(--line);
      }}

      .hero-stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .gallery-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .case-cover {{
        min-height: 320px;
      }}
    }}

    @media (max-width: 900px) and (min-width: 99999px) {{
      .shell {{
        width: min(100vw, calc(100vw - 24px));
        margin: 12px auto 24px;
      }}

      .topbar {{
        padding: 16px 20px;
        align-items: flex-start;
      }}

      .nav {{
        width: 100%;
        gap: 8px 12px;
        justify-content: flex-start;
      }}

      .nav-link {{
        font-size: 11px;
      }}

      .hero-left {{
        padding: 28px 24px 24px;
      }}

      .hero-right {{
        padding: 32px 24px 34px;
      }}

      .portrait-wrap {{
        width: 100%;
        align-items: center;
      }}

      .portrait-frame {{
        width: min(100%, 220px);
      }}

      .hero-title {{
        font-size: clamp(34px, 10vw, 56px);
      }}

      .hero-subtitle,
      .section-heading p,
      .case-copy p,
      .project-card p,
      .panel p {{
        line-height: 1.75;
      }}

      .section {{
        padding: 44px 24px;
      }}

      .section-heading,
      .case-heading {{
        margin-bottom: 22px;
      }}

      .project-card h3 {{
        font-size: 22px;
      }}

      .project-card-body {{
        padding: 18px 18px 20px;
      }}

      .case-cover {{
        min-height: 260px;
      }}

      .gallery-grid {{
        gap: 14px;
      }}

      table {{
        min-width: 640px;
      }}
    }}

    @media (max-width: 720px) and (min-width: 99999px) {{
      .shell {{
        width: min(100vw, calc(100vw - 16px));
        margin: 8px auto 20px;
      }}

      .topbar,
      .hero-left,
      .hero-right,
      .section,
      .footer {{
        padding-left: 18px;
        padding-right: 18px;
      }}

      .topbar,
      .section-heading,
      .case-heading,
      .footer {{
        flex-direction: column;
        align-items: flex-start;
      }}

      .topbar {{
        gap: 14px;
      }}

      .brand {{
        width: 100%;
      }}

      .brand-copy span {{
        white-space: normal;
        overflow: visible;
        text-overflow: clip;
      }}

      .hero-stats {{
        grid-template-columns: 1fr;
      }}

      .gallery-grid {{
        grid-template-columns: 1fr;
      }}

      .project-meta-row {{
        flex-direction: column;
      }}

      .nav {{
        justify-content: flex-start;
        overflow-x: auto;
        flex-wrap: nowrap;
        padding-bottom: 4px;
        max-width: 100%;
        -ms-overflow-style: none;
        scrollbar-width: none;
      }}

      .nav::-webkit-scrollbar {{
        display: none;
      }}

      .nav-link {{
        flex: 0 0 auto;
      }}

      .case-facts {{
        justify-content: flex-start;
      }}

      .case-cover {{
        min-height: 220px;
      }}

      .project-card-image {{
        aspect-ratio: 1.22 / 1;
      }}

      .gallery-item img {{
        aspect-ratio: 1.04 / 1;
      }}

      th,
      td {{
        padding: 14px 12px;
        font-size: 13px;
      }}
    }}

    @media (max-width: 560px) and (min-width: 99999px) {{
      .shell {{
        width: 100vw;
        margin: 0;
        border-left: none;
        border-right: none;
        border-radius: 0;
      }}

      .topbar,
      .hero-left,
      .hero-right,
      .section,
      .footer {{
        padding-left: 14px;
        padding-right: 14px;
      }}

      .hero-left {{
        padding-top: 20px;
        padding-bottom: 20px;
      }}

      .hero-right {{
        padding-top: 24px;
        padding-bottom: 26px;
      }}

      .portrait-frame {{
        width: min(100%, 184px);
        padding: 10px;
        border-radius: 22px;
      }}

      .portrait-frame img {{
        border-radius: 14px;
      }}

      .hero-title {{
        font-size: clamp(28px, 12vw, 42px);
        line-height: 0.98;
      }}

      .hero-subtitle {{
        font-size: 15px;
        line-height: 1.68;
      }}

      .section-heading h2,
      .case-heading h2 {{
        font-size: clamp(24px, 8.4vw, 34px);
      }}

      .project-card h3 {{
        font-size: 20px;
      }}

      .contact-item,
      .timeline-top,
      .project-meta-row {{
        gap: 8px;
      }}

      .contact-label {{
        width: 42px;
      }}

      .case-copy,
      .panel,
      .timeline-item {{
        padding: 18px;
        border-radius: 18px;
      }}

      .project-card,
      .case-cover,
      .gallery-item {{
        border-radius: 18px;
      }}

      .project-card-body {{
        padding: 16px 16px 18px;
      }}

      .case-cover {{
        min-height: 180px;
      }}

      .gallery-grid {{
        gap: 12px;
      }}

      .gallery-item img {{
        aspect-ratio: 1 / 1;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">BWH</div>
        <div class="brand-copy">
          <strong>包文海 Portfolio</strong>
          <span>Interior Design · Residential · Model House · Commercial Space</span>
        </div>
      </div>
      <nav class="nav">{nav_items}</nav>
    </header>

    <section class="hero">
      <aside class="hero-left">
        <div>
          <div class="portrait-wrap">
            <div class="portrait-frame">
              <img src="{portrait_src}" alt="包文海头像">
            </div>
            <div class="portrait-note">室内设计 · 效果表达 · 施工深化</div>
          </div>

          <div class="contact-panel">
            <div class="contact-item">
              <div class="contact-label">Phone</div>
              <div class="contact-value">
                <strong>{html.escape(resume["phone"])}</strong>
                <span>个人联系</span>
              </div>
            </div>
            <div class="contact-item">
              <div class="contact-label">Email</div>
              <div class="contact-value">
                <strong>{html.escape(resume["email"])}</strong>
                <span>欢迎作品合作与岗位沟通</span>
              </div>
            </div>
            <div class="contact-item">
              <div class="contact-label">City</div>
              <div class="contact-value">
                <strong>{html.escape(resume["city"])}</strong>
                <span>{html.escape(resume["availability"])}</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div class="hero-right">
        <div class="eyebrow">Interior Designer Portfolio</div>
        <h1 class="hero-title">{html.escape(resume["name"])}</h1>
        <p class="hero-subtitle">
          {html.escape(resume["tagline"])}
          作品集聚焦高端住宅、样板房与商业空间项目，强调空间氛围、材质关系与落地可执行性之间的统一。
        </p>
        <div class="hero-stats">
          <div class="stat">
            <strong>12+</strong>
            <span>高端样板房、售楼处与办公空间项目交付经验</span>
          </div>
          <div class="stat">
            <strong>5</strong>
            <span>独立承担从量房到落地跟进的完整全案项目</span>
          </div>
          <div class="stat">
            <strong>95%</strong>
            <span>住宅与商业项目的空间落地还原度</span>
          </div>
          <div class="stat">
            <strong>AI+</strong>
            <span>将 AI 辅助设计融入方案表达与协同提效流程</span>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Profile</div>
          <h2>个人简介与能力概览</h2>
        </div>
        <p>
          这份作品集由简历信息与多个项目方案文件整理而成，既保留个人履历与方法论，也展示代表性空间案例。
        </p>
      </div>
      <div class="intro-grid">
        <div class="panel">
          <h3>设计定位</h3>
          <p>{html.escape(resume["tagline"])}</p>
          <div class="skill-cloud">{skill_badges}</div>
        </div>
        <div class="panel">
          <h3>核心优势</h3>
          <ul class="text-list">{strength_list}</ul>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Experience</div>
          <h2>教育与职业经历</h2>
        </div>
        <p>
          从环境艺术设计科班背景，到高端住宅与商业空间实践，形成了兼具视觉表现与落地执行的设计路径。
        </p>
      </div>
      <div class="intro-grid" style="margin-bottom: 22px;">
        <div class="panel">
          <h3>教育背景</h3>
          <ul class="text-list">{education_list}</ul>
        </div>
        <div class="panel">
          <h3>工作方式</h3>
          <p>以方案表达为入口，以施工图深化与现场协同为支撑，关注空间美学、工艺可行性与客户沟通效率之间的平衡。</p>
        </div>
      </div>
      <div class="timeline">{experience_blocks}</div>
    </section>

    <section class="section">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Projects</div>
          <h2>案例总览</h2>
        </div>
        <p>
          从样板房、私宅到底跃与商业展馆，以下案例覆盖方案推演、空间效果表达、软装气质塑造与功能组织等不同维度。点击任意卡片可直接跳转到对应案例详情。
        </p>
      </div>
      <div class="project-grid">{project_cards}</div>
    </section>

    <section class="section">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Highlights</div>
          <h2>简历精选项目</h2>
        </div>
        <p>
          以下项目来自简历中的代表履历条目，补充呈现包文海在施工图深化、全案执行与样板房视觉表达方面的综合能力。
        </p>
      </div>
      <div class="feature-table-wrap">
        <table>
          <thead>
            <tr>
              <th>项目名称</th>
              <th>时间</th>
              <th>职责与成果</th>
            </tr>
          </thead>
          <tbody>{featured_rows}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Case Studies</div>
          <h2>项目详情展示</h2>
        </div>
        <p>
          每个案例均选取最具代表性的页面与空间图，突出项目气质、重点功能区以及空间氛围的控制能力。
        </p>
      </div>
      {detailed_sections}
    </section>

    <footer class="footer">
      <div>
        <strong>Contact</strong>
        <p>{html.escape(resume["name"])} · {html.escape(resume["phone"])} · {html.escape(resume["email"])}</p>
      </div>
      <div>
        <strong>Notes</strong>
        <p>本页根据提供的个人简历与 PDF 方案文件整理生成，适合本地展示、投递作品集或进一步二次编辑。</p>
      </div>
    </footer>
  </div>
</body>
</html>
"""


def main() -> None:
    ensure_dirs()
    clear_asset_dirs()
    crop_portrait("headshot")
    resume = get_resume_summary()
    projects = build_projects()
    asset_map = asset_map_from_projects(projects)
    html_content = build_html(resume, projects, asset_map)
    asset_dirs = distribute_assets(asset_map)
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    manifest = {
        "html": str(OUTPUT_HTML),
        "asset_dirs": [str(path) for path in asset_dirs],
        "project_count": len(projects),
        "resume_source_used": resume["resume_file_used"],
    }
    (ROOT / "outputs" / "baowenhai-portfolio-assets-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
