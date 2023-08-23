#
# 
#
"""
"""


import tkinter as tk

import tksheet

from media.lrc import Lrc, LyricsItem, Timestamp


class LyricsEditor(tksheet.Sheet):
    def __init__(
            self,
            parent: tk.Misc,
            **kwargs
            ) -> None:
        super().__init__(parent, **kwargs)
        # Creating attributes...
        self._changed: bool = False
        """Specifies whether contents changed after 'Populate' methid."""
        self._hashCols: str
        """The hash of data in the sheet computed column by column."""
        self._hashRows: str
        """The hash of data in the sheet computed row by row."""
        self._lrc: Lrc
        """The LRC object which this editor is supposed to process it."""
        # Configuring the sheet...
        self.headers([
            'Timestap',
            'Lyrics/text'])
        self.enable_bindings(
            'drag_select',
            'single_select',
            'row_drag_and_drop',
            'row_select',
            'column_width_resize',
            'double_click_column_resize',
            'arrowkeys',
            'edit_cell')
    
    def SetChangeOrigin(self) -> None:
        """Sets the current status of the editor as the origin for
        chnage comparisons.
        """
        data = self.get_sheet_data()
        self._hashCols = self._HashCols(data)
        self._hashRows = self._HashRows(data)
    
    def HasChanged(self) -> bool:
        """Determines whether the content of the sheet has changed
        since last origin of change.
        """
        data = self.get_sheet_data()
        hashCols = self._HashCols(data)
        hashRows = self._HashRows(data)
        return all([
            hashCols == self._hashCols,
            hashRows == self._hashRows])

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
    
    def ApplyLyrics(self) -> None:
        """Applies the changes """
        if self._changed:
            data = self.get_sheet_data()
            self._lrc.lyrics = data
            self._changed = False
    
    def GetAllLyricsItems(self) -> list[LyricsItem]:
        """Gets all the content of the editor as a list of `LyricsItem`
        objects."""
        return self.get_sheet_data()
    
    def Populate(self, lrc: Lrc) -> None:
        """Populates the provided LRC object into this editor."""
        self._lrc = lrc
        if self._lrc:
            self.set_sheet_data(
                self._lrc.lyrics,
                reset_col_positions=False)
        else:
            self.set_sheet_data(
                [],
                reset_col_positions=False)
    
    def InsertRowAbove(self) -> None:
        if self._lrc:            
            # Getting the selection box...
            data = self.get_sheet_data()
            selectedBox = self.get_all_selection_boxes()
            if selectedBox:
                # There are selected cells,
                # Inserting a row at the start of them...
                rowStart, colStart, rowEnd, colEnd = selectedBox[0]
                data.insert(
                    rowStart,
                    LyricsItem(''))
                # Selecting the inserted row...
                if colEnd - colStart == 1:
                    rowIdx = rowEnd
                    colIdx = colStart
                else:
                    rowIdx = rowStart
                    colIdx = 1
            else:
                # No selected cells,
                # Inserting a row at the strat of the sheet...
                data.insert(
                    0,
                    LyricsItem(''))
                rowIdx = 0
                colIdx = 1

            self._changed = True
            self.set_sheet_data(data, reset_col_positions=False)
            self.select_cell(rowIdx, colIdx)              

    def InsertRowBelow(self) -> None:
        if self._lrc:
            # Getting the selection box...
            data = self.get_sheet_data()
            selectedBox = self.get_all_selection_boxes()
            if selectedBox:
                # There are selected cells,
                # Inserting a row at the end of them...
                rowStart, colStart, rowEnd, colEnd = selectedBox[0]
                data.insert(
                    rowEnd,
                    LyricsItem(''))
                # Selecting the inserted row...
                if colEnd - colStart == 1:
                    rowIdx = rowEnd
                    colIdx = colStart
                else:
                    rowIdx = rowEnd
                    colIdx = 1
            else:
                # No selected cells,
                # Inserting a row at the end of the sheet...
                rowIdx = len(data)
                data.insert(
                    rowIdx,
                    LyricsItem(''))
                colIdx = 1

            self._changed = True
            self.set_sheet_data(data, reset_col_positions=False)
            self.select_cell(rowIdx, colIdx)

    def ClearCells(self) -> None:
        selectedCells = self.get_selected_cells()
        data = self.get_sheet_data()
        for cell in selectedCells:
            rowIdx, colIdx = cell
            if data[rowIdx][colIdx]:
                self._changed = True
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
        self._changed = True
        self.set_sheet_data(data, reset_col_positions=False)
        self.deselect()
    
    def SetTimestamp(self, pos: float) -> None:
        if self._lrc:
            # Getting the selected box...
            selectedBox = self.get_all_selection_boxes()
            if not selectedBox:
                # No selected cells, returning...
                return
            rowStart, _, rowEnd, _ = selectedBox[0]
            if (rowEnd - rowStart) == 1:
                data = self.get_sheet_data()
                data[rowStart][0] = Timestamp.FromFloat(pos)
                self._changed = True
                self.set_sheet_data(data, reset_col_positions=False)
                if rowEnd < len(data):
                    self.select_cell(rowEnd, 0)
    
    def _GetClipboardAsList(self) -> list[str]:
        clipboard = self.clipboard_get()
        return clipboard.strip().splitlines()
    
    def OverrideFromClipboard(self) -> None:
        if self._lrc:
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

            if clipLines:
                self._changed = True

    def InsertFromClipboard(self) -> None:
        pass
