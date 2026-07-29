from PIL import Image, ImageDraw, ImageFont

from or_solver.core.image_graph_recognizer import infer_edges_from_weight_positions, recognize_colored_nodes


def test_recognize_colored_nodes_from_simple_network_diagram():
    image = Image.new("RGB", (500, 220), "white")
    draw = ImageDraw.Draw(image)
    nodes = [
        ((30, 90), "red"),
        ((130, 65), "blue"),
        ((230, 45), "blue"),
        ((230, 125), "blue"),
        ((340, 65), "blue"),
        ((460, 90), "red"),
    ]
    colors = {"red": "#e94f64", "blue": "#bde8ff"}
    outlines = {"red": "#c62828", "blue": "#5b8def"}
    for (x, y), color in nodes:
        draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=colors[color], outline=outlines[color], width=3)
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    draw.text((78, 52), "3", font=font, fill="black")
    draw.text((180, 58), "6", font=font, fill="black")

    result = recognize_colored_nodes(image)

    assert result.source == "S"
    assert result.target == "T"
    assert result.nodes == ["S", "A", "B", "C", "D", "T"]
    assert "3" in result.weights
    assert "6" in result.weights
    assert result.edges == []
    assert any("未自动填写矩阵" in note for note in result.notes)
    assert infer_edges_from_weight_positions(result.node_positions, result.weight_positions)


def test_standard_textbook_shortest_path_template_fills_edges():
    image = Image.new("RGB", (700, 300), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    nodes = [
        ((60, 150), "red"),
        ((170, 90), "blue"),
        ((180, 155), "blue"),
        ((150, 230), "blue"),
        ((290, 110), "blue"),
        ((300, 170), "blue"),
        ((390, 70), "blue"),
        ((420, 150), "blue"),
        ((390, 230), "blue"),
        ((610, 150), "red"),
    ]
    colors = {"red": "#e94f64", "blue": "#bde8ff"}
    outlines = {"red": "#c62828", "blue": "#5b8def"}
    for (x, y), color in nodes:
        draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=colors[color], outline=outlines[color], width=3)
    for i, (x, y) in enumerate([
        (110, 80), (120, 145), (110, 205), (220, 80), (175, 120), (180, 190),
        (240, 160), (250, 220), (330, 55), (350, 115), (285, 145), (360, 155),
    ]):
        draw.text((x, y), str((i % 8) + 1), font=font, fill="black")

    result = recognize_colored_nodes(image)

    assert result.nodes == ["S", "A", "B", "C", "D", "E", "F", "G", "H", "T"]
    assert ("S", "A", 3) in result.edges
    assert ("H", "T", 8) in result.edges
    assert any("标准最短路题图模板" in note for note in result.notes)
