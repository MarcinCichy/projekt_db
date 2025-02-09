# ui/dxf_view.py
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PyQt5.QtCore import Qt, QRectF, QLineF, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath
import ezdxf
import math

class CustomGraphicsView(QGraphicsView):
    """Widok z obsługą wczytywania pliku DXF, panningu, zoomu oraz rysowania linii centralnych."""
    def __init__(self):
        super().__init__()
        # Tworzymy jedyną scenę w całym projekcie
        self._scene = QGraphicsScene()
        self.setScene(self._scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.setInteractive(True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self._mouse_pressed_position = None
        self._panStart = None
        self._isPanning = False
        self.padding = 500
        self.setCursor(Qt.ArrowCursor)
        self.main_window = None

    def scene(self):
        """Zwraca obiekt sceny, aby segment_manager iterował po tej samej scenie."""
        return self._scene

    def load_dxf(self, file_path):
        """Wczytuje plik DXF do sceny."""
        doc = ezdxf.readfile(file_path)
        self._scene.clear()

        for entity in doc.modelspace():
            if entity.dxftype() == 'LINE':
                start, end = entity.dxf.start, entity.dxf.end
                if hasattr(entity.dxf, 'color') and entity.dxf.color == 2:
                    # bending line
                    pen = QPen(QColor("yellow"))
                    line_item = QGraphicsLineItem(start.x, start.y, end.x, end.y)
                    line_item.setData(0, "bending")  # identyfikacja
                    line_item.setPen(pen)
                    self._scene.addItem(line_item)
                else:
                    self._scene.addLine(start.x, start.y, end.x, end.y)
            elif entity.dxftype() == 'CIRCLE':
                center = entity.dxf.center
                radius = entity.dxf.radius
                self._scene.addEllipse(center.x - radius, center.y - radius, 2 * radius, 2 * radius)
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = entity.dxf.start_angle
                end_angle = entity.dxf.end_angle
                rect = QRectF(center.x - radius, center.y - radius, 2 * radius, 2 * radius)
                path = QPainterPath()
                path.arcMoveTo(rect, start_angle)
                path.arcTo(rect, start_angle, (end_angle - start_angle))
                self._scene.addPath(path)
            elif entity.dxftype() == 'POLYLINE':
                points = list(entity.points())
                for i in range(len(points) - 1):
                    self._scene.addLine(points[i][0], points[i][1],
                                        points[i + 1][0], points[i + 1][1])
            elif entity.dxftype() == 'LWPOLYLINE':
                points = list(entity.points())
                for i in range(len(points)):
                    start_point = points[i]
                    end_point = points[(i + 1) % len(points)]
                    bulge = start_point[4] if len(start_point) > 4 else 0
                    if bulge == 0:
                        self._scene.addLine(start_point[0], start_point[1],
                                            end_point[0], end_point[1])
                    else:
                        self.draw_bulge_arc(start_point, end_point, bulge)
            else:
                print(f"Nieobsługiwany typ: {entity.dxftype()}")

        # Po wczytaniu – wyśrodkuj scenę w widoku
        self.adjust_scene_origin()
        self.resetTransform()
        self.scale(1, -1)
        self.center_dxf_in_view()

    def draw_bulge_arc(self, start_point, end_point, bulge):
        """Rysowanie łuku z uwzględnieniem 'bulge'."""
        chord_length = math.sqrt((end_point[0] - start_point[0])**2 + (end_point[1] - start_point[1])**2)
        if chord_length == 0:
            return
        radius = abs(chord_length / (2 * math.sin(2 * math.atan(bulge))))
        center_x = (start_point[0] + end_point[0]) / 2
        center_y = (start_point[1] + end_point[1]) / 2

        start_angle = math.degrees(math.atan2(start_point[1] - center_y, start_point[0] - center_x))
        end_angle = math.degrees(math.atan2(end_point[1] - center_y, end_point[0] - center_x))
        rect = QRectF(center_x - radius, center_y - radius, 2 * radius, 2 * radius)

        path = QPainterPath()
        path.arcMoveTo(rect, start_angle)
        arc_span = end_angle - start_angle
        path.arcTo(rect, start_angle, arc_span)
        self._scene.addPath(path)

    def adjust_scene_origin(self):
        """Przesuwa elementy, aby minimalne x,y były w (0,0)."""
        bounding_rect = self._scene.itemsBoundingRect()
        dx = -bounding_rect.left()
        dy = -bounding_rect.top()

        for item in self._scene.items():
            item.moveBy(dx, dy)

        new_rect = self._scene.itemsBoundingRect()
        margin = 5000
        new_rect = new_rect.adjusted(-margin, -margin, margin, margin)
        self._scene.setSceneRect(new_rect)

    def center_dxf_in_view(self):
        """Centruje rysunek w widoku (po transformacji)."""
        self.resetTransform()
        self.scale(1, -1)
        view_center = self.mapToScene(self.viewport().rect().center())
        scene_center = self._scene.sceneRect().center()
        offset = scene_center - view_center
        self.translate(offset.x(), offset.y())

    # Rysowanie linii centralnych w widoku
    def drawForeground(self, painter, rect):
        painter.resetTransform()
        pen = QPen(QColor("red"))
        pen.setWidth(1)
        painter.setPen(pen)
        view_rect = self.viewport().rect()
        center = view_rect.center()
        painter.drawLine(view_rect.left(), center.y(), view_rect.right(), center.y())
        painter.drawLine(center.x(), view_rect.top(), center.x(), view_rect.bottom())

    # Obsługa panningu
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_pressed_position = event.pos()
            self._panStart = event.pos()
            self._isPanning = True
            self.viewport().setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._isPanning:
            delta = event.pos() - self._panStart
            self._panStart = event.pos()
            self.translate(delta.x(), delta.y())
        if self.main_window:
            pos = self.mapToScene(event.pos())
            self.main_window.update_status_bar(pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.viewport().setCursor(Qt.ArrowCursor)
            if (event.pos() - self._mouse_pressed_position).manhattanLength() < 10:
                # Kliknięcie w linię gięcia
                pos = self.mapToScene(event.pos())
                tolerance = 20.0
                search_rect = QRectF(pos.x() - tolerance, pos.y() - tolerance, tolerance * 2, tolerance * 2)
                items = self._scene.items(search_rect, Qt.IntersectsItemShape)
                closest_item = None
                closest_dist = tolerance
                for it in items:
                    if isinstance(it, QGraphicsLineItem) and it.data(0) == "bending":
                        p1 = it.mapToScene(it.line().p1())
                        p2 = it.mapToScene(it.line().p2())
                        qline = QLineF(p1, p2)
                        dist = self._distance_to_point(qline, pos)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_item = it
                if closest_item and self.main_window:
                    p1 = closest_item.mapToScene(closest_item.line().p1())
                    p2 = closest_item.mapToScene(closest_item.line().p2())
                    qline = QLineF(p1, p2)
                    clicked_point = QPointF((qline.x1() + qline.x2())/2, (qline.y1() + qline.y2())/2)
                    self.main_window.handle_bending_line_click(closest_item, clicked_point)
            self._isPanning = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.1
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def _distance_to_point(self, line: QLineF, point: QPointF) -> float:
        A = line.p1()
        B = line.p2()
        AP = point - A
        AB = B - A
        ab2 = AB.x()**2 + AB.y()**2
        if ab2 == 0:
            return (AP.x()**2 + AP.y()**2)**0.5
        t = (AP.x()*AB.x() + AP.y()*AB.y()) / ab2
        if t < 0:
            closest = A
        elif t > 1:
            closest = B
        else:
            closest = A + AB * t
        return (point - closest).manhattanLength()


# jest ok