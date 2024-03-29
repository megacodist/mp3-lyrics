#
# 
#
"""
"""


import logging
import tkinter as tk
from typing import Callable, Iterable

import tksheet

from media.lrc import LyricsItem, Timestamp


class SelectionError(Exception):
    """Raised when a selection-based operation is triggered with no
    selection.
    """
    pass


class LyricsEditor(tksheet.Sheet):
    def __init__(
            self,
            parent: tk.Misc,
            *,
            lyrics_items_sep: str = '\n',
            timestamp_lyrics_delim: str = '\t',
            **kwargs
            ) -> None:
        """Initializes a new instance of `LyricsEditor` and sets the empty
        state as the origin for change comparison.
        """
        super().__init__(parent, **kwargs)
        # Creating attributes...
        self._lyricsItemsSep = lyrics_items_sep
        """Specifies the separator between lyrics items."""
        self._timestampLyricsDelim = timestamp_lyrics_delim
        """Specifies the delimiter between timestamps and lyrics."""
        self._hashCols: str
        """The hash of data in the sheet computed column by column."""
        self._hashRows: str
        """The hash of data in the sheet computed row by row."""
        self.SetChangeOrigin()
        # Configuring the sheet...
        self.headers([
            'Timestap',
            'Lyrics/text'])
        self.enable_bindings(
            'deselect',
            'drag_select',
            'single_select',
            'row_select',
            'column_select',
            'row_height_resize',
            'column_width_resize',
            'double_click_column_resize',
            'row_drag_and_drop',
            'arrowkeys',
            'edit_cell')
    
    def SetChangeOrigin(self) -> None:
        """Sets the current status of the editor as the origin for
        chnage comparisons.
        """
        data: list[LyricsItem] = self.get_sheet_data()
        self._hashCols = self._HashCols(data)
        self._hashRows = self._HashRows(data)
    
    def HasChanged(self) -> bool:
        """Determines whether the content of the sheet has changed
        since last origin of change.
        """
        data: list[LyricsItem] = self.get_sheet_data()
        hashCols = self._HashCols(data)
        hashRows = self._HashRows(data)
        return any([
            hashCols != self._hashCols,
            hashRows != self._hashRows])

    def _HashCols(self, data: list[LyricsItem]) -> str:
        """Computes the hash of the sheet by concatenating timestamps
        and lyrics respectively.
        """
        from hashlib import sha512
        hash_ = sha512(b'')
        for lyricsItem in data:
            hash_.update(str(lyricsItem[0]).encode())
        for lyricsItem in data:
            hash_.update(str(lyricsItem[1]).encode())
        return hash_.hexdigest()
    
    def _HashRows(self, data: list[LyricsItem]) -> str:
        """Computes the hash of the sheet by concatenating `LyricsItem`s.
        """
        from hashlib import sha512
        hash_ = sha512(b'')
        for lyricsItem in data:
            hash_.update(
                str(lyricsItem[0]).encode() + str(lyricsItem[1]).encode())
        return hash_.hexdigest()
    
    def GetAllLyricsItems(self) -> list[LyricsItem]:
        """Gets all the content of the editor as a list of `LyricsItem`
        objects."""
        return self.get_sheet_data()
    
    def ClearContent(self) -> None:
        """Clears the content of this lyrics editor and makes it empty."""
        self.set_sheet_data([], reset_col_positions=False)
    
    def Populate(self, __lis: Iterable[LyricsItem], /) -> None:
        """Populates the provided LRC object into this editor."""
        self.set_sheet_data(__lis, reset_col_positions=False, redraw=True)
    
    def InsertRowAbove(self) -> None:
        """Inserts a row above selected cells. If no cell is selected,
        it inserts a row at the start of the sheet.
        """
        # Getting the selection box...
        data: list[LyricsItem] = self.get_sheet_data()
        selectedBox: tuple[tuple[int, ...]] = self.get_all_selection_boxes()
        if selectedBox:
            # There are selected cells,
            # Inserting a row at the start of them...
            rowStart, colStart, rowEnd, colEnd = selectedBox[0]
            rowIdx = rowStart
        else:
            # No selected cells,
            # Inserting a row at the strat of the sheet...
            rowIdx = 0
        data.insert(
            rowIdx,
            LyricsItem(''))
        colIdx = 1
        self.set_sheet_data(data, reset_col_positions=False)
        if selectedBox:
            self.select_cell(rowIdx, colIdx)              

    def InsertRowBelow(self) -> None:
        """Inserts a row below selected cells. If no cell is selected,
        it inserts a row at the end of the sheet.
        """
        # Getting the selection box...
        data: list[LyricsItem] = self.get_sheet_data()
        selectedBox: tuple[tuple[int, ...]] = self.get_all_selection_boxes()
        if selectedBox:
            # There are selected cells,
            # Inserting a row at the end of them...
            rowStart, colStart, rowEnd, colEnd = selectedBox[0]
            rowIdx = rowEnd
        else:
            # No selected cells,
            # Inserting a row at the end of the sheet...
            rowIdx = len(data)
        data.insert(
            rowIdx,
            LyricsItem(''))
        colIdx = 1
        self.set_sheet_data(data, reset_col_positions=False)
        if selectedBox:
            self.select_cell(rowIdx, colIdx)

    def ClearCells(self) -> None:
        selectedCells = self.get_selected_cells()
        data = self.get_sheet_data()
        for cell in selectedCells:
            rowIdx, colIdx = cell
            if data[rowIdx][colIdx]:
                data[rowIdx][colIdx] = ''
        self.set_sheet_data(data, reset_col_positions=False)
    
    def RemoveRows(self) -> None:
        # Getting the selected box...
        selectedBox = self.get_all_selection_boxes()
        if not selectedBox:
            # No selected cells, returning...
            return
        rowStart, _, rowEnd, _ = selectedBox[0]
        data = self.get_sheet_data()
        data = [*data[0:rowStart], *data[rowEnd:]]
        self.set_sheet_data(data, reset_col_positions=False)
        #self.deselect()
        self.selection_clear()
    
    def Deselect(self) -> None:
        self.select_cell(0, 0)
    
    def SetTimestamp(self, pos: float) -> None:
        # Getting the selected box...
        selectedBox = self.get_all_selection_boxes()
        if not selectedBox:
            # No selected cells, returning...
            return
        rowStart, _, rowEnd, _ = selectedBox[0]
        if (rowEnd - rowStart) == 1:
            data = self.get_sheet_data()
            data[rowStart][0] = Timestamp.FromFloat(pos)
            self.set_sheet_data(data, reset_col_positions=False)
            if rowEnd < len(data):
                self.select_cell(rowEnd, 0)
    
    def _GetClipboardAsList(self) -> list[str]:
        clipboard = self.clipboard_get()
        return clipboard.strip().splitlines()
    
    def CopyLyricsOnly(self) -> None:
        """Copies the lyrics of the selected rows of the editor to the
        clipboard.
        """
        # Declaring variables -----------------------------
        data: list[LyricsItem]
        selectedBox: tuple[tuple[int, ...], ...]
        # Copying lyrics only -----------------------------
        data = self.get_sheet_data()
        if not data:
            # No data to copy, returning...
            return
        selectedBox = self.get_all_selection_boxes()
        if not selectedBox:
            # No selected cells, returning...
            return
        rowStart, colStart, rowEnd, colEnd = selectedBox[0]
        copy = self._lyricsItemsSep.join(
            li.text for li in data[rowStart:rowEnd])
        self.clipboard_clear()
        self.clipboard_append(copy)
    
    def CopyLyricsTimestamps(self) -> None:
        """Copies the selection into the clipboard. It might copy
        timestamps and/or lyrics.
        """
        # Declaring variables -----------------------------
        data: list[LyricsItem]
        selectedBox: tuple[tuple[int, ...], ...]
        CopyLyricsItem: Callable[[LyricsItem], str]
        # Copying lyrics only -----------------------------
        data = self.get_sheet_data()
        if not data:
            # No data to copy, returning...
            return
        selectedBox = self.get_all_selection_boxes()
        if not selectedBox:
            # No selected cells, returning...
            return
        rowStart, colStart, rowEnd, colEnd = selectedBox[0]
        colSpan = colEnd - colStart
        if colSpan == 2:
            CopyLyricsItem = lambda li: str(li.timestamp) + \
                self._timestampLyricsDelim + li.text
        elif colSpan == 1:
            if colStart == 0:
                CopyLyricsItem = lambda li: str(li.timestamp)
            elif colStart == 1:
                CopyLyricsItem = lambda li: li.text
            else:
                logging.error('E-2-3', stack_info=True)
                return
        else:
            logging.error('E-2-4', stack_info=True)
            return
        text = self._lyricsItemsSep.join(
            CopyLyricsItem(li) for li in data[rowStart:rowEnd])
        self.clipboard_clear()
        self.clipboard_append(text)
    
    def PasreOverrideLyrics(self) -> None:
        # Declaring variables -----------------------------
        data: list[LyricsItem]
        selectedBox: tuple[tuple[int, ...], ...]
        # Copying lyrics only -----------------------------
        data = self.get_sheet_data()
        selectedBox = self.get_all_selection_boxes()
        if not data:
            rowIdx = 0
        elif selectedBox:
            rowIdx, _, _, _ = selectedBox[0]
        else:
            # No selection in the populated sheet, returning...
            return
        
        try:
            clipLines = self._GetClipboardAsList()
            lineIdx = 0
            while True:
                data[rowIdx][1] = clipLines[lineIdx]
                lineIdx += 1
                rowIdx += 1
        except IndexError:
            # Checking whether clipboard exhausted...
            if lineIdx >= len(clipLines):
                # clipboard exhausted, we've done, returning...
                return
            # The sheet exhausted, appending the rest of clipboard...
            for idx in range(lineIdx, len(clipLines)):
                data.append(LyricsItem(clipLines[idx]))
        self.set_sheet_data(data, reset_col_positions=False)

    def PasteInsert(self) -> None:
        pass
