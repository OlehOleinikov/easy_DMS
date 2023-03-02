"""Модуль нанесення фігур та друку тексту на зображення"""

import cv2
from defines import TEXT_DEF_SIZE, DEF_COLOR, TEXT_DEF_THICK, LINE_DEF_THICK, OFFSET, C_C, DEF_RADIUS, PAGE_W, PAGE_H

DEF_FONT = cv2.FONT_HERSHEY_SIMPLEX


def d_text(img, x, y, text, font=DEF_FONT, size=TEXT_DEF_SIZE, color=DEF_COLOR, thick=TEXT_DEF_THICK):
    """Друк тексту (типові налаштування кольору, розміру та відступів)"""
    img = cv2.putText(img, text, (x+5+OFFSET, y-5-OFFSET), font, size, color, thick)
    return img


def d_rect(img, x, y, h, w, color=DEF_COLOR, desc=None, line=LINE_DEF_THICK):
    """Малювання прямокутника"""
    img = cv2.rectangle(img, (x, y), (x + w, y + h), color, line)
    if desc:
        img = d_text(img, x, y, desc, color=color)
    return img


def d_circ(img, x, y, radius=DEF_RADIUS, color=DEF_COLOR, desc=None):
    """Малювання кола (переважно для виділення опорного кута боксу знайденого слова)"""
    img = cv2.circle(img, (x, y), radius=radius, color=color, thickness=LINE_DEF_THICK)
    if desc:
        img = d_text(img, x, y, desc, color=color)
    return img


def line_h(img, y, color=C_C, thick=LINE_DEF_THICK):
    """Малювання горизонтальної лінії з додатковими офсетними лініями - відображення меж входження"""
    img = cv2.line(img, (0, y), (PAGE_W, y), color, thick)
    img = cv2.line(img, (0, y + OFFSET), (PAGE_W, y+OFFSET), color, 1)
    img = cv2.line(img, (0, y - OFFSET), (PAGE_W, y-OFFSET), color, 1)
    return img


def line_v(img, x, color=DEF_COLOR, thick=LINE_DEF_THICK):
    """Малювання вертикальної лінії з додатковими офсетними лініями - відображення меж входження"""
    img = cv2.line(img, (x, 0), (x, PAGE_H), color, thick)
    img = cv2.line(img, (x - OFFSET, 0), (x-OFFSET, PAGE_H), color, 1)
    img = cv2.line(img, (x + OFFSET, 0), (x+OFFSET, PAGE_H), color, 1)
    return img


def d_elem(img, x, y, h, w, color=DEF_COLOR, desc=None, line=LINE_DEF_THICK):
    """Виділення слова - у прямокутник з опорною точкою"""
    img = d_rect(img, x, y, h, w, color, desc, line)
    img = d_circ(img, x, y, color=color)
    return img
