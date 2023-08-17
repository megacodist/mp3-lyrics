#
# 
#
"""
"""


import tkinter as tk

from megacodist.keyboard import Modifiers


class ABView(tk.Canvas):
    def __init__(
            self,
            master: tk.Misc | None = None,
            width: int = 150,
            height: int = 8,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        self['bd'] = 0
        self['width'] = width
        self['height'] = height
        self['background'] = '#fcf8de'

        # Initializing atrributes...
        self._a: float = 0.0
        """Specifies the A component of the A-B repeat object."""
        self._b: float = 0.0
        """Specifies the B component of the A-B repeat object."""
        self._length: float = 0.0
        """Specifies the maximum length of the A-B repeat object."""

        # Bindings...
        self.bind(
            '<Button-1>',
            self._OnMouseClicked)
    
    @property
    def a(self) -> float:
        """Gets or sets the A component of the A-B repeat object."""
        return self._a
    
    @a.setter
    def a(self, __a, /) -> None:
        if not isinstance(__a, (float, int,)):
            raise TypeError(
                "The A component of a A-B repeat object must be "
                + "a float or an integer")
        if not (0.0 <= __a <= self._length):
            raise ValueError(
                "Out of range value for the A "
                + "component of a A-B repeat object")
        self._a = __a
        if __a > self._b:
            self._b = self._length
        self._Redraw()
    
    @property
    def b(self) -> float:
        """Gets or sets the B component of the A-B repeat object."""
        return self._b
    
    @a.setter
    def b(self, __b, /) -> None:
        if not isinstance(__b, (float, int,)):
            raise TypeError(
                "The B component of a A-B repeat object must be "
                + "a float or an integer")
        if not (0.0 <= __b <= self._length):
            raise ValueError(
                "Out of range value for the B "
                + "component of a A-B repeat object")
        self._b = __b
        if __b < self._a:
            self._a = 0.0
        self._Redraw()
    
    @property
    def length(self) -> float:
        """Gets or sets the 'length' component of this A-B repeat object.
        By setting this property, 'a' and 'b' will be set to 0.0.
        """
        return self._length
    
    @length.setter
    def length(self, __leng, /) -> None:
        if not isinstance(__leng, float):
            raise TypeError(
                "The length component of the A-B "
                + "repeat object must be a float")
        if __leng < 0.0:
            raise ValueError(
                "The length component of the A-B repeat"
                + " object must be positive")
        self._length = __leng
        self._a = 0.0
        self._b = 0.0
        self._Redraw()
    
    def Reset(self) -> None:
        """Resets this A-B repeat object."""
        self._a = 0.0
        self._b = 0.0
        self._length = 0.0
    
    def IsSet(self) -> bool:
        """Specifies whether this A-B repeat object is set or not."""
        return self._length > 0.0 and ((self._b - self._a) > 0.0)
    
    def IsInside(self, __value: float, /) -> bool:
        """Specifies whether the A-B interval is set and the provided
        value is inside the interval.
        """
        return self.IsSet() and (self._a <= __value <= self._b)
    
    def _OnMouseClicked(self, event: tk.Event) -> None:
        cnvsWidth = self.winfo_width()
        # Detecting whether ALT is holding or not...
        if event.state & Modifiers.ALT == Modifiers.ALT:
            if self._length > 0.0:
                self.b = event.x / cnvsWidth * self._length
        # Detecting whether ALT is holding or not...
        elif event.state & Modifiers.CONTROL == Modifiers.CONTROL:
            if self._length > 0.0:
                self.a = event.x / cnvsWidth * self._length
    
    def _Redraw(self) -> None:
        self.delete('all')
        if self.IsSet():
            cnvsWidth = self.winfo_width()
            cnvsHeight = self.winfo_height()
            aX = round(self._a / self._length * cnvsWidth)
            bX = round(self._b / self._length * cnvsWidth)
            self.create_line(
                aX,
                0,
                bX,
                0,
                stipple='gray50',
                width=cnvsHeight)
