# ui/dxf_view.py
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem
from PyQt5.QtCore import Qt, QRectF, QLineF, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath
import ezdxf
import math

class CustomGraphicsView(QGraphicsView):
    """
    Klasa obsługująca wyświetlanie DXF i zapewniająca:
      1) (0,0) w "wizualnie najniższym" lewym rogu rysunku.
      2) Środek boundingRect w środku widoku.
      3) Obsługę panningu, zoomu i rysowania linii centralnych.
    """

    def __init__(self):
        super().__init__()
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

        self.setCursor(Qt.ArrowCursor)
        self.main_window = None

        # Przybliżony "środek rysunku" (np. boundingRect.center())
        self.cm_x = 0.0
        self.cm_y = 0.0

    def scene(self):
        """Dostęp do sceny z zewnątrz (np. SegmentManager)."""
        return self._scene

    def load_dxf(self, file_path):
        """
        Wczytuje plik DXF i:
          - czyści scenę,
          - ładuje obiekty,
          - ustawia (0,0) w wizualnym dolnym lewym rogu rysunku,
          - przesuwa widok tak, by środek boundingRect był w centrum ekranu.
        """
        print("[DEBUG] load_dxf:", file_path)
        doc = ezdxf.readfile(file_path)
        self._scene.clear()

        # --- Wczytanie elementów do sceny ---
        for entity in doc.modelspace():
            if entity.dxftype() == 'LINE':
                start, end = entity.dxf.start, entity.dxf.end
                if hasattr(entity.dxf, 'color') and entity.dxf.color == 2:
                    pen = QPen(QColor("yellow"))
                    line_item = QGraphicsLineItem(start.x, start.y, end.x, end.y)
                    line_item.setData(0, "bending")
                    line_item.setPen(pen)
                    self._scene.addItem(line_item)
                else:
                    self._scene.addLine(start.x, start.y, end.x, end.y)
            elif entity.dxftype() == 'CIRCLE':
                center = entity.dxf.center
                radius = entity.dxf.radius
                self._scene.addEllipse(center.x - radius, center.y - radius, 2*radius, 2*radius)
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = entity.dxf.start_angle
                end_angle = entity.dxf.end_angle
                rect = QRectF(center.x - radius, center.y - radius, 2*radius, 2*radius)
                path = QPainterPath()
                path.arcMoveTo(rect, start_angle)
                path.arcTo(rect, start_angle, end_angle - start_angle)
                self._scene.addPath(path)
            elif entity.dxftype() == 'POLYLINE':
                points = list(entity.points())
                for i in range(len(points) - 1):
                    self._scene.addLine(points[i][0], points[i][1],
                                        points[i+1][0], points[i+1][1])
            elif entity.dxftype() == 'LWPOLYLINE':
                points = list(entity.points())
                for i in range(len(points)):
                    start_point = points[i]
                    end_point = points[(i+1) % len(points)]
                    bulge = start_point[4] if len(start_point) > 4 else 0
                    if bulge == 0:
                        self._scene.addLine(start_point[0], start_point[1],
                                            end_point[0], end_point[1])
                    else:
                        self.draw_bulge_arc(start_point, end_point, bulge)
            else:
                print(f"[DEBUG] Nieobsługiwany typ: {entity.dxftype()}")

        # 1) Ustawiamy (0,0) w WIZUALNIE dolnym lewym rogu.
        self.adjust_scene_origin_bottom_left()

        # 2) Obliczamy środek boundingRect (przybliżony "środek ciężkości")
        br = self._scene.itemsBoundingRect()
        center = br.center()
        self.cm_x = center.x()
        self.cm_y = center.y()
        print(f"[DEBUG] boundingRect after shift: (left={br.left()}, top={br.top()}, bottom={br.bottom()}, right={br.right()})")
        print(f"[DEBUG] boundingRect center = ({self.cm_x}, {self.cm_y})")

        # 3) Reset transform (nie odwracamy osi - przyjmujemy, że PyQt rośnie w dół)
        self.resetTransform()

        # 4) Centrujemy w widoku -> środek boundingRect do środka ekranu.
        self.center_dxf_in_view_using_mass_center()

    def draw_bulge_arc(self, start_point, end_point, bulge):
        chord_length = math.sqrt((end_point[0] - start_point[0])**2 + (end_point[1] - start_point[1])**2)
        if chord_length == 0:
            return
        radius = abs(chord_length / (2*math.sin(2*math.atan(bulge))))
        center_x = (start_point[0] + end_point[0]) / 2
        center_y = (start_point[1] + end_point[1]) / 2

        start_angle = math.degrees(math.atan2(start_point[1] - center_y, start_point[0] - center_x))
        end_angle = math.degrees(math.atan2(end_point[1] - center_y, end_point[0] - center_x))
        rect = QRectF(center_x - radius, center_y - radius, 2*radius, 2*radius)

        path = QPainterPath()
        path.arcMoveTo(rect, start_angle)
        path.arcTo(rect, start_angle, end_angle - start_angle)
        self._scene.addPath(path)

    def adjust_scene_origin_bottom_left(self):
        """
        Przesuwa elementy sceny tak, by WIZUALNIE dolny lewy róg boundingRect
        trafił w punkt (0,0) sceny.

        UWAGA: zakładamy, że boundingRect.top() < boundingRect.bottom(), bo PyQt
        interpretuje top jako MIN y przy rosnącej w dół osi. Jeżeli Twój DXF
        ma odwrotną konwencję, trzeba dostosować.
        """
        bounding_rect = self._scene.itemsBoundingRect()

        top = bounding_rect.top()       # w PyQt: najmniejsza wartość Y
        bottom = bounding_rect.bottom() # największa wartość Y
        left = bounding_rect.left()
        right = bounding_rect.right()

        print(f"[DEBUG] original boundingRect: top={top}, bottom={bottom}, left={left}, right={right}")

        # Jeżeli Y rośnie w dół (pyqt standard), to top < bottom => top jest wizualnie górnym brzegiem
        # ALE Ty chcesz, by "dolny" brzeg (bottom) wylądował w 0,0?
        # To TUTAJ MUSISZ zdecydować, co jest "dolnym" brzegiem w Twojej konwencji.

        # ZAŁÓŻMY, że "dolny" wizualnie to bottom (większa wartość Y).
        # Wtedy dy = - bottom => przenosimy bottom do 0 (0,0 w scenie).
        # "Lewa" krawędź = left => dx = -left => przenosimy left do 0.
        # => (bottom, left) -> (0,0).

        dx = -left
        dy = -bottom

        for item in self._scene.items():
            item.moveBy(dx, dy)

        # Po przesunięciu robimy "margines"
        new_rect = self._scene.itemsBoundingRect()
        margin = 5000
        new_rect = new_rect.adjusted(-margin, -margin, margin, margin)
        self._scene.setSceneRect(new_rect)

    def center_dxf_in_view_using_mass_center(self):
        """
        Przesuwa widok (transformację QGraphicsView),
        aby (self.cm_x, self.cm_y) w scenie wylądowało w środku okna.
        """
        self.resetTransform()
        # JEŚLI w Twoim rysunku Y rośnie w górę, a chcesz "na ekranie" mieć normalny widok,
        # MOŻESZ odkomentować:
        # self.scale(1, -1)

        # Obliczamy offset
        view_center = self.mapToScene(self.viewport().rect().center())
        cm_point = QPointF(self.cm_x, self.cm_y)
        offset = cm_point - view_center

        print(f"[DEBUG] center_dxf_in_view_using_mass_center => offset=({offset.x()}, {offset.y()})")

        self.translate(offset.x(), offset.y())

    # ------------------------------------------------
    # Obsługa panningu, zoomu, klikania w bending line:
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
                pos = self.mapToScene(event.pos())
                tolerance = 20.0
                search_rect = QRectF(pos.x() - tolerance, pos.y() - tolerance, tolerance*2, tolerance*2)
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
                    clicked_point = QPointF((qline.x1()+qline.x2())/2, (qline.y1()+qline.y2())/2)
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

    def drawForeground(self, painter, rect):
        painter.resetTransform()
        pen = QPen(QColor("red"))
        pen.setWidth(1)
        painter.setPen(pen)
        view_rect = self.viewport().rect()
        center = view_rect.center()
        painter.drawLine(view_rect.left(), center.y(), view_rect.right(), center.y())
        painter.drawLine(center.x(), view_rect.top(), center.x(), view_rect.bottom())

    def _distance_to_point(self, line: QLineF, point: QPointF) -> float:
        A = line.p1()
        B = line.p2()
        AB = B - A
        AP = point - A
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
